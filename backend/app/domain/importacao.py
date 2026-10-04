"""Importação: levar o resultado de um processamento (lote) para o banco.

Três etapas, cada uma com a sua estrutura:

1. PLANO DO LOTE (montar_plano): o que o lote contém, organizado por cliente,
   com o hash e a posição de cada arquivo. Vem só do lote.
2. COMPARAÇÃO (domain/comparacao.py): o plano confrontado com o banco:
   NOVO, IGUAL, ALTERADO, CONFLITO.
3. PLANO DECIDIDO (decidir): comparação + escolhas do usuário (o que importar,
   a que cliente vincular, quais correções manuais sobrescrever). É ele que o
   repositório aplica, numa única transação.

As três etapas são funções puras: dá para testar toda a regra sem banco.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.domain.entities import Consolidacao, ResultadoExtracao
from app.domain.enums import StatusComparacao, StatusItem
from app.domain.processamento import ItemProcessamento, Processamento

if TYPE_CHECKING:
    from app.domain.comparacao import Comparacao

# --------------------------------------------------------------------------- 1. plano do lote


@dataclass(frozen=True, slots=True)
class DocumentoAImportar:
    posicao_item: int  # item do processamento de onde o documento veio
    hash_sha256: str
    tamanho_bytes: int
    resultado: ResultadoExtracao


@dataclass(frozen=True, slots=True)
class ClienteAImportar:
    chave: str
    nome: str
    espolio: bool
    documentos: list[DocumentoAImportar] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ItemForaDaImportacao:
    """Arquivo do lote que não pode ser importado (e por quê)."""

    posicao_item: int
    nome_arquivo: str
    status: StatusItem
    motivo: str | None


@dataclass(frozen=True, slots=True)
class PlanoDoLote:
    processamento_id: int
    clientes: list[ClienteAImportar]
    sem_cliente: list[DocumentoAImportar]
    fora_da_importacao: list[ItemForaDaImportacao]


def montar_plano(processamento: Processamento, consolidacao: Consolidacao) -> PlanoDoLote:
    """Organiza o lote por cliente, ligando cada documento ao item (hash, tamanho) de onde veio.

    A consolidação agrupa os MESMOS objetos ResultadoExtracao que estão nos itens
    do lote; por isso dá para achar o item de cada documento pela identidade do
    objeto (id()).
    """
    item_do_resultado: dict[int, ItemProcessamento] = {id(i.resultado): i for i in processamento.itens if i.resultado}

    def a_importar(resultado: ResultadoExtracao) -> DocumentoAImportar:
        item = item_do_resultado[id(resultado)]
        return DocumentoAImportar(item.id, item.hash_sha256, item.tamanho_bytes, resultado)

    return PlanoDoLote(
        processamento_id=processamento.id,
        clientes=[
            ClienteAImportar(f.chave, f.nome, f.espolio, [a_importar(r) for r in f.documentos])
            for f in consolidacao.fichas
        ],
        sem_cliente=[a_importar(r) for r in consolidacao.documentos_sem_cliente],
        fora_da_importacao=[
            ItemForaDaImportacao(i.id, i.nome_arquivo, i.status, i.erro or _motivo(i))
            for i in processamento.itens
            if i.status is not StatusItem.SUCESSO
        ],
    )


def _motivo(item: ItemProcessamento) -> str | None:
    if item.status is StatusItem.DUPLICADO:
        return f"Mesmo conteúdo de '{item.duplicado_de}'."
    if item.resultado and item.resultado.avisos:
        return item.resultado.avisos[0]
    return None


# --------------------------------------------------------------------------- 3. plano decidido


@dataclass(frozen=True, slots=True)
class AtualizacaoDeDocumento:
    """Nova versão de um documento que já está no banco."""

    documento_id: int
    documento: DocumentoAImportar
    campos: dict[str, Any]  # só os campos que vão mudar
    campos_sobrescritos: list[str]  # correções manuais que o usuário mandou substituir


@dataclass(slots=True)
class ClienteDecidido:
    chave: str
    nome: str
    espolio: bool
    cliente_id: int | None  # cliente existente (encontrado ou vinculado); None = criar
    vinculado_manualmente: bool = False  # a chave do lote vira apelido do cliente escolhido
    novos: list[DocumentoAImportar] = field(default_factory=list)
    atualizacoes: list[AtualizacaoDeDocumento] = field(default_factory=list)
    iguais: list[tuple[int, int]] = field(default_factory=list)  # (posição no lote, documento_id)

    @property
    def tem_o_que_gravar(self) -> bool:
        return bool(self.novos or self.atualizacoes)


@dataclass(slots=True)
class PlanoDecidido:
    processamento_id: int
    clientes: list[ClienteDecidido] = field(default_factory=list)
    sem_cliente: list[DocumentoAImportar] = field(default_factory=list)
    sem_cliente_iguais: list[tuple[int, int]] = field(default_factory=list)
    ignorados: int = 0  # documentos que o usuário deixou de fora


def decidir(
    plano: PlanoDoLote,
    comparacao: "Comparacao",
    selecionados: set[int],
    vincular: dict[str, int],
    sobrescrever: set[int],
) -> PlanoDecidido:
    """Aplica as escolhas do usuário sobre a comparação.

    - documentos IGUAIS: nada a gravar; o item do lote só é ligado ao documento existente;
    - não selecionados: ignorados;
    - NOVO: entra como documento novo;
    - ALTERADO/CONFLITO: atualiza o documento existente, SEM tocar nas correções
      manuais, a não ser que a posição esteja em `sobrescrever`.
    """
    comparado = {d.posicao_item: d for d in comparacao.todos_os_documentos()}
    decidido = PlanoDecidido(plano.processamento_id)

    for cliente, cliente_comparado in zip(plano.clientes, comparacao.clientes, strict=True):
        destino = ClienteDecidido(
            chave=cliente.chave,
            nome=cliente.nome,
            espolio=cliente.espolio,
            cliente_id=vincular.get(cliente.chave, cliente_comparado.cliente_id),
            vinculado_manualmente=cliente.chave in vincular,
        )
        for documento in cliente.documentos:
            _decidir_documento(documento, comparado[documento.posicao_item], selecionados, sobrescrever, destino, decidido)
        decidido.clientes.append(destino)

    for documento in plano.sem_cliente:
        situacao = comparado[documento.posicao_item]
        if situacao.status is StatusComparacao.IGUAL:
            decidido.sem_cliente_iguais.append((documento.posicao_item, situacao.documento_id))
        elif documento.posicao_item in selecionados:
            decidido.sem_cliente.append(documento)
        else:
            decidido.ignorados += 1
    return decidido


def _decidir_documento(documento, situacao, selecionados, sobrescrever, destino: ClienteDecidido, decidido: PlanoDecidido):
    if situacao.status is StatusComparacao.IGUAL:
        destino.iguais.append((documento.posicao_item, situacao.documento_id))
    elif documento.posicao_item not in selecionados:
        decidido.ignorados += 1
    elif situacao.status is StatusComparacao.NOVO:
        destino.novos.append(documento)
    else:  # ALTERADO ou CONFLITO: nova versão de um documento existente
        pode_sobrescrever = documento.posicao_item in sobrescrever
        aplicaveis = [d for d in situacao.diferencas if pode_sobrescrever or not d.editado_manualmente]
        destino.atualizacoes.append(
            AtualizacaoDeDocumento(
                documento_id=situacao.documento_id,
                documento=documento,
                campos={d.campo: d.valor_novo for d in aplicaveis},
                campos_sobrescritos=[d.campo for d in aplicaveis if d.editado_manualmente],
            )
        )


# --------------------------------------------------------------------------- resultado


@dataclass(frozen=True, slots=True)
class Importacao:
    id: int
    processamento_id: int
    criado_em: datetime
    clientes_criados: int
    documentos_criados: int
    documentos_atualizados: int  # novas versões aplicadas a documentos existentes
    documentos_ja_existentes: int  # mesmo hash já estava no banco: nada muda
    documentos_ignorados: int  # não selecionados pelo usuário
    documentos_sem_cliente: int
