"""Comparação: o que o lote traria de diferente para o banco?

    PLANO DO LOTE ──┐
                    ├──► comparar() ──► NOVO / IGUAL / ALTERADO / CONFLITO / ERRO
    ESTADO DO BANCO ┘                    (por cliente e por documento, com diferenças)

Função PURA: recebe uma "foto" do banco (EstadoDoBanco), montada pelo
ComparacaoService, e não acessa o banco. Toda a regra é testável sem PostgreSQL.

Regras para cada DOCUMENTO do lote:
1. o hash já existe no banco                          -> IGUAL (o mesmo arquivo)
2. o cliente existe e já tem um documento do mesmo tipo e com o mesmo nome de
   arquivo (conteúdo diferente)                       -> nova VERSÃO:
       - alguma diferença cai num campo corrigido à mão -> CONFLITO
       - senão                                         -> ALTERADO (com o diff)
3. senão                                              -> NOVO

Regra de segurança: um valor que a extração NÃO encontrou (None) nunca conta
como diferença. Se o OCR falhou desta vez, o valor que está no banco fica.

Regras para cada CLIENTE do lote:
- todos os documentos são IGUAIS (já estão no banco, talvez em outro cliente)
  -> IGUAL: nada a importar, nada a decidir;
- a chave não existe no banco (nem como apelido):
      - há clientes com nome parecido -> CONFLITO (vincular ao existente ou criar?)
      - senão                          -> NOVO
- a chave existe: CONFLITO se algum documento está em conflito; IGUAL se todos
  são iguais; senão ALTERADO.
"""

from dataclasses import dataclass, field, fields
from difflib import SequenceMatcher
from typing import Any

from app.domain.entities import DocumentoArmazenado, FichaCliente, ResultadoExtracao
from app.domain.enums import StatusComparacao, TipoDocumento
from app.domain.importacao import DocumentoAImportar, ItemForaDaImportacao, PlanoDoLote
from app.domain.nomes import normalizar_unicode

# A partir desta similaridade entre chaves, um cliente novo do lote é apontado
# como possível correspondência de um cliente que já está no banco.
LIMIAR_CLIENTE_PARECIDO = 0.85
MAXIMO_SUGESTOES = 3


@dataclass(frozen=True, slots=True)
class DiferencaDeCampo:
    campo: str
    valor_atual: Any
    valor_novo: Any
    editado_manualmente: bool  # o valor atual foi corrigido à mão (e seria sobrescrito)


@dataclass(slots=True)
class ComparacaoDocumento:
    posicao_item: int
    nome_arquivo: str
    tipo: TipoDocumento
    status: StatusComparacao
    documento_id: int | None = None  # documento do banco (IGUAL, ALTERADO, CONFLITO)
    cliente_id_no_banco: int | None = None
    diferencas: list[DiferencaDeCampo] = field(default_factory=list)
    observacao: str | None = None


@dataclass(frozen=True, slots=True)
class SugestaoDeCliente:
    cliente_id: int
    nome: str
    similaridade: float


@dataclass(slots=True)
class ComparacaoCliente:
    chave: str
    nome: str
    status: StatusComparacao
    cliente_id: int | None  # cliente do banco com esta chave (None = não existe)
    sugestoes: list[SugestaoDeCliente] = field(default_factory=list)
    documentos: list[ComparacaoDocumento] = field(default_factory=list)

    @property
    def precisa_decisao(self) -> bool:
        """Cliente novo parecido com um existente, e com algo a importar: vincular ou criar?
        Só o usuário sabe."""
        tem_o_que_importar = any(d.status is not StatusComparacao.IGUAL for d in self.documentos)
        return self.cliente_id is None and bool(self.sugestoes) and tem_o_que_importar


@dataclass(slots=True)
class Comparacao:
    processamento_id: int
    clientes: list[ComparacaoCliente]
    documentos_sem_cliente: list[ComparacaoDocumento]
    fora_da_importacao: list[ItemForaDaImportacao]

    def todos_os_documentos(self) -> list[ComparacaoDocumento]:
        return [d for c in self.clientes for d in c.documentos] + self.documentos_sem_cliente

    def selecao_padrao(self) -> set[int]:
        """O que vem marcado na tela: NOVO e ALTERADO, exceto os de clientes que precisam de decisão.
        CONFLITO nunca vem marcado: exige uma escolha consciente."""
        importaveis = {StatusComparacao.NOVO, StatusComparacao.ALTERADO}
        selecao = {
            d.posicao_item
            for c in self.clientes
            if not c.precisa_decisao
            for d in c.documentos
            if d.status in importaveis
        }
        return selecao | {d.posicao_item for d in self.documentos_sem_cliente if d.status in importaveis}

    @property
    def resumo(self) -> dict[str, dict[StatusComparacao, int]]:
        def contar(status_list) -> dict[StatusComparacao, int]:
            return {s: sum(1 for x in status_list if x is s) for s in StatusComparacao if s is not StatusComparacao.ERRO}

        documentos = contar([d.status for d in self.todos_os_documentos()])
        documentos[StatusComparacao.ERRO] = len(self.fora_da_importacao)
        return {"clientes": contar([c.status for c in self.clientes]), "documentos": documentos}


class EstadoDoBanco:
    """Foto do banco com o que a comparação precisa, indexada para consulta rápida."""

    def __init__(
        self,
        clientes: list[FichaCliente],
        cliente_por_chave: dict[str, int],
        documentos_sem_cliente: list[DocumentoArmazenado],
    ) -> None:
        self._clientes = {c.id: c for c in clientes}
        self._cliente_por_chave = cliente_por_chave
        self._por_hash: dict[str, DocumentoArmazenado] = {
            d.hash_sha256: d for c in clientes for d in c.documentos
        } | {d.hash_sha256: d for d in documentos_sem_cliente}

    def cliente_da_chave(self, chave: str) -> int | None:
        return self._cliente_por_chave.get(chave)

    def documento_com_hash(self, hash_sha256: str) -> DocumentoArmazenado | None:
        return self._por_hash.get(hash_sha256)

    def versao_anterior(self, cliente_id: int, tipo: TipoDocumento, nome_arquivo: str) -> DocumentoArmazenado | None:
        """Documento do cliente com o mesmo tipo e o mesmo nome de arquivo."""
        alvo = _nome_comparavel(nome_arquivo)
        return next(
            (
                d
                for d in self._clientes[cliente_id].documentos_do_tipo(tipo)
                if _nome_comparavel(d.nome_arquivo) == alvo
            ),
            None,
        )

    def clientes_parecidos(self, chave: str) -> list[SugestaoDeCliente]:
        """Clientes cuja chave (ou algum apelido) é parecida com `chave`, do mais ao menos parecido."""
        melhor_por_cliente: dict[int, float] = {}
        for outra_chave, cliente_id in self._cliente_por_chave.items():
            comparador = SequenceMatcher(None, chave, outra_chave)
            if comparador.quick_ratio() < LIMIAR_CLIENTE_PARECIDO:
                continue
            similaridade = comparador.ratio()
            if similaridade >= LIMIAR_CLIENTE_PARECIDO:
                melhor_por_cliente[cliente_id] = max(similaridade, melhor_por_cliente.get(cliente_id, 0))
        sugestoes = [SugestaoDeCliente(i, self._clientes[i].nome, s) for i, s in melhor_por_cliente.items()]
        return sorted(sugestoes, key=lambda s: -s.similaridade)[:MAXIMO_SUGESTOES]


def comparar(plano: PlanoDoLote, estado: EstadoDoBanco, vincular: dict[str, int] | None = None) -> Comparacao:
    """Compara o lote com o banco. `vincular` (chave do lote -> cliente) aplica as
    vinculações escolhidas pelo usuário antes de comparar os documentos."""
    vincular = vincular or {}
    clientes = []
    for cliente in plano.clientes:
        cliente_id = vincular.get(cliente.chave) or estado.cliente_da_chave(cliente.chave)
        documentos = [_comparar_documento(d, cliente_id, estado) for d in cliente.documentos]
        sugestoes = [] if cliente_id else estado.clientes_parecidos(cliente.chave)
        clientes.append(
            ComparacaoCliente(
                chave=cliente.chave,
                nome=cliente.nome,
                status=_status_do_cliente(cliente_id, sugestoes, documentos),
                cliente_id=cliente_id,
                sugestoes=sugestoes,
                documentos=documentos,
            )
        )
    return Comparacao(
        processamento_id=plano.processamento_id,
        clientes=clientes,
        documentos_sem_cliente=[_comparar_documento(d, None, estado) for d in plano.sem_cliente],
        fora_da_importacao=plano.fora_da_importacao,
    )


def diferencas_de_campos(atual: DocumentoArmazenado, novo: ResultadoExtracao) -> list[DiferencaDeCampo]:
    """Campos extraídos que mudaram. Valor novo ausente (None) não conta: não apaga o atual."""
    if atual.dados is None or novo.dados is None or type(atual.dados) is not type(novo.dados):
        return []
    diferencas = []
    for campo in fields(novo.dados):
        valor_atual, valor_novo = getattr(atual.dados, campo.name), getattr(novo.dados, campo.name)
        if valor_novo is not None and valor_novo != valor_atual:
            diferencas.append(
                DiferencaDeCampo(campo.name, valor_atual, valor_novo, campo.name in atual.campos_editados)
            )
    return diferencas


def _comparar_documento(documento: DocumentoAImportar, cliente_id: int | None, estado: EstadoDoBanco) -> ComparacaoDocumento:
    resultado = documento.resultado
    base = {"posicao_item": documento.posicao_item, "nome_arquivo": resultado.nome_arquivo, "tipo": resultado.tipo}

    existente = estado.documento_com_hash(documento.hash_sha256)
    if existente:
        outro_cliente = existente.cliente_id != cliente_id
        return ComparacaoDocumento(
            **base,
            status=StatusComparacao.IGUAL,
            documento_id=existente.id,
            cliente_id_no_banco=existente.cliente_id,
            observacao="O mesmo arquivo já está no banco, em outro cliente." if outro_cliente and cliente_id else None,
        )

    anterior = estado.versao_anterior(cliente_id, resultado.tipo, resultado.nome_arquivo) if cliente_id else None
    if anterior:
        diferencas = diferencas_de_campos(anterior, resultado)
        conflito = any(d.editado_manualmente for d in diferencas)
        return ComparacaoDocumento(
            **base,
            status=StatusComparacao.CONFLITO if conflito else StatusComparacao.ALTERADO,
            documento_id=anterior.id,
            cliente_id_no_banco=anterior.cliente_id,
            diferencas=diferencas,
            observacao="Nova versão do arquivo (mesmo nome, conteúdo diferente)."
            + ("" if diferencas else " Os dados extraídos não mudaram."),
        )

    return ComparacaoDocumento(**base, status=StatusComparacao.NOVO)


def _status_do_cliente(
    cliente_id: int | None, sugestoes: list[SugestaoDeCliente], documentos: list[ComparacaoDocumento]
) -> StatusComparacao:
    # Todos os arquivos já estão no banco (talvez em outro cliente): nada a importar,
    # mesmo que o lote tenha agrupado esses arquivos sob uma chave desconhecida.
    if all(d.status is StatusComparacao.IGUAL for d in documentos):
        return StatusComparacao.IGUAL
    if cliente_id is None:
        return StatusComparacao.CONFLITO if sugestoes else StatusComparacao.NOVO
    if any(d.status is StatusComparacao.CONFLITO for d in documentos):
        return StatusComparacao.CONFLITO
    return StatusComparacao.ALTERADO


def _nome_comparavel(nome_arquivo: str) -> str:
    return normalizar_unicode(nome_arquivo).casefold().strip()
