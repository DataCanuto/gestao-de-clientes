"""Importação de um lote para o banco: aplica o PLANO DECIDIDO numa única transação.

Se qualquer passo falhar (ex.: queda de conexão no meio), NADA fica gravado:
não existe importação pela metade, com cliente criado e documentos faltando.

O repositório não decide nada: quem decidiu o que importar, o que atualizar e
o que preservar foram a comparação (domain/comparacao.py) e o usuário
(domain/importacao.decidir). Aqui só se grava:
- cliente: usa o existente (encontrado ou vinculado) ou cria um novo; uma
  vinculação manual grava a chave do lote como APELIDO do cliente escolhido;
- documento novo: INSERT + histórico (IMPORTACAO);
- nova versão: UPDATE só dos campos decididos + histórico campo a campo
  (inclusive a troca de arquivo: o hash antigo fica registrado);
- documento igual: nada muda, só o item do lote é ligado a ele.
"""

from dataclasses import dataclass

from sqlalchemy import select, update

from app.core.database import FabricaDeSessoes
from app.domain.enums import OrigemAlteracao
from app.domain.importacao import AtualizacaoDeDocumento, ClienteDecidido, DocumentoAImportar, Importacao, PlanoDecidido
from app.models import (
    AlteracaoDocumentoModel,
    ClienteChaveModel,
    ClienteModel,
    DocumentoModel,
    ImportacaoModel,
    ProcessamentoItemModel,
)
from app.domain.rotulos import rotulo_campos
from app.repositories.conversao import campos_editados_por_pessoa, novo_documento, valor_como_texto


@dataclass
class _Contadores:
    clientes_criados: int = 0
    documentos_criados: int = 0
    documentos_atualizados: int = 0
    documentos_ja_existentes: int = 0
    documentos_ignorados: int = 0
    documentos_sem_cliente: int = 0


class ImportacaoRepository:
    def __init__(self, sessoes: FabricaDeSessoes) -> None:
        self._sessoes = sessoes

    def importar(self, plano: PlanoDecidido) -> Importacao:
        contadores = _Contadores(documentos_ignorados=plano.ignorados)
        with self._sessoes.begin() as sessao:
            for cliente in plano.clientes:
                cliente_id = self._resolver_cliente(sessao, cliente, contadores)
                for documento in cliente.novos:
                    self._inserir(sessao, plano.processamento_id, documento, cliente_id)
                    contadores.documentos_criados += 1
                for atualizacao in cliente.atualizacoes:
                    self._atualizar(sessao, plano.processamento_id, atualizacao)
                    contadores.documentos_atualizados += 1
                for posicao, documento_id in cliente.iguais:
                    self._ligar_item(sessao, plano.processamento_id, posicao, documento_id)
                    contadores.documentos_ja_existentes += 1

            for documento in plano.sem_cliente:
                self._inserir(sessao, plano.processamento_id, documento, None)
                contadores.documentos_criados += 1
                contadores.documentos_sem_cliente += 1
            for posicao, documento_id in plano.sem_cliente_iguais:
                self._ligar_item(sessao, plano.processamento_id, posicao, documento_id)
                contadores.documentos_ja_existentes += 1

            model = ImportacaoModel(processamento_id=plano.processamento_id, **vars(contadores))
            sessao.add(model)
            sessao.flush()
            return _para_dominio(model)

    def listar(self) -> list[Importacao]:
        with self._sessoes() as sessao:
            consulta = select(ImportacaoModel).order_by(ImportacaoModel.id.desc())
            return [_para_dominio(model) for model in sessao.scalars(consulta)]

    # ------------------------------------------------------------------ clientes

    @staticmethod
    def _resolver_cliente(sessao, cliente: ClienteDecidido, contadores: _Contadores) -> int | None:
        """Id do cliente de destino. Só cria cliente novo se houver algo a gravar para ele."""
        cliente_id = cliente.cliente_id or sessao.scalar(
            select(ClienteChaveModel.cliente_id).where(ClienteChaveModel.chave == cliente.chave)
        )
        if cliente_id is None:
            if not cliente.tem_o_que_gravar:
                return None
            novo = ClienteModel(
                nome=cliente.nome,
                chave=cliente.chave,
                espolio=cliente.espolio,
                chaves=[ClienteChaveModel(chave=cliente.chave)],
            )
            sessao.add(novo)
            sessao.flush()
            contadores.clientes_criados += 1
            return novo.id

        if cliente.vinculado_manualmente and sessao.get(ClienteChaveModel, cliente.chave) is None:
            # O usuário disse que esta grafia é deste cliente: vira apelido.
            sessao.add(ClienteChaveModel(chave=cliente.chave, cliente_id=cliente_id))
        if cliente.espolio and cliente.tem_o_que_gravar:
            sessao.execute(update(ClienteModel).where(ClienteModel.id == cliente_id).values(espolio=True))
        return cliente_id

    # ------------------------------------------------------------------ documentos

    def _inserir(self, sessao, processamento_id: int, documento: DocumentoAImportar, cliente_id: int | None) -> None:
        model = novo_documento(documento, cliente_id)
        revisados = documento.resultado.campos_corrigidos
        model.alteracoes = [
            AlteracaoDocumentoModel(
                campo="documento",
                valor_novo=f"Importado do processamento {processamento_id}"
                + (f" (revisado à mão: {rotulo_campos(revisados)})" if revisados else ""),
                origem=OrigemAlteracao.IMPORTACAO,
            )
        ]
        sessao.add(model)
        sessao.flush()
        self._ligar_item(sessao, processamento_id, documento.posicao_item, model.id)

    def _atualizar(self, sessao, processamento_id: int, atualizacao: AtualizacaoDeDocumento) -> None:
        """Nova versão: troca o arquivo e aplica só os campos decididos."""
        model = sessao.get(DocumentoModel, atualizacao.documento_id)
        novo = atualizacao.documento
        historico = [
            AlteracaoDocumentoModel(
                campo="arquivo",
                valor_anterior=f"{model.nome_arquivo} (sha256 {model.hash_sha256[:12]}…)",
                valor_novo=f"{novo.resultado.nome_arquivo} (sha256 {novo.hash_sha256[:12]}…)",
                origem=OrigemAlteracao.IMPORTACAO,
            )
        ]
        model.hash_sha256 = novo.hash_sha256
        model.nome_arquivo = novo.resultado.nome_arquivo
        model.tamanho_bytes = novo.tamanho_bytes
        model.nome_pelo_conteudo = novo.resultado.nome_pelo_conteudo or model.nome_pelo_conteudo
        model.avisos = list(novo.resultado.avisos)

        for campo, valor in atualizacao.campos.items():
            historico.append(
                AlteracaoDocumentoModel(
                    campo=campo,
                    valor_anterior=_texto(getattr(model, campo)),
                    valor_novo=_texto(valor),
                    origem=OrigemAlteracao.IMPORTACAO,
                )
            )
            setattr(model, campo, valor)
        editados = set(model.campos_editados)
        if atualizacao.campos_sobrescritos:
            # A correção manual foi substituída por decisão do usuário: deixa de ser "editada"...
            editados -= set(atualizacao.campos_sobrescritos)
        # ...a não ser que o valor novo também tenha sido informado por uma pessoa (revisão no lote).
        editados |= {c for c in campos_editados_por_pessoa(novo.resultado) if c in atualizacao.campos}
        model.campos_editados = sorted(editados)

        model.alteracoes.extend(historico)
        sessao.flush()
        self._ligar_item(sessao, processamento_id, novo.posicao_item, model.id)

    @staticmethod
    def _ligar_item(sessao, processamento_id: int, posicao: int, documento_id: int) -> None:
        sessao.execute(
            update(ProcessamentoItemModel)
            .where(ProcessamentoItemModel.processamento_id == processamento_id, ProcessamentoItemModel.posicao == posicao)
            .values(documento_id=documento_id)
        )


def _texto(valor) -> str | None:
    convertido = valor_como_texto(valor)
    return None if convertido is None else str(convertido)


def _para_dominio(model: ImportacaoModel) -> Importacao:
    return Importacao(
        id=model.id,
        processamento_id=model.processamento_id,
        criado_em=model.criado_em,
        clientes_criados=model.clientes_criados,
        documentos_criados=model.documentos_criados,
        documentos_atualizados=model.documentos_atualizados,
        documentos_ja_existentes=model.documentos_ja_existentes,
        documentos_ignorados=model.documentos_ignorados,
        documentos_sem_cliente=model.documentos_sem_cliente,
    )
