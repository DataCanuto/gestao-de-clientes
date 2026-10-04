"""Acesso às tabelas `documento` e `alteracao_documento`.

Toda alteração de campo grava uma linha no histórico (alteracao_documento) na
MESMA transação que altera o documento: ou as duas coisas acontecem, ou
nenhuma. É isso que garante que o histórico nunca fica incompleto.
"""

from typing import Any

from sqlalchemy import select

from app.core.database import FabricaDeSessoes
from app.domain.entities import CAMPO_CLIENTE, Alteracao, DocumentoArmazenado
from app.domain.enums import OrigemAlteracao, TipoDocumento
from app.models import AlteracaoDocumentoModel, ClienteModel, DocumentoModel
from app.repositories.conversao import documento_para_dominio, valor_como_texto

SEM_CLIENTE = "(sem cliente)"


class DocumentoRepository:
    def __init__(self, sessoes: FabricaDeSessoes) -> None:
        self._sessoes = sessoes

    def listar(
        self,
        tipo: TipoDocumento | None = None,
        cliente_id: int | None = None,
        sem_cliente: bool = False,
    ) -> list[DocumentoArmazenado]:
        with self._sessoes() as sessao:
            consulta = select(DocumentoModel).order_by(DocumentoModel.nome_arquivo)
            if tipo:
                consulta = consulta.where(DocumentoModel.tipo == tipo)
            if cliente_id is not None:
                consulta = consulta.where(DocumentoModel.cliente_id == cliente_id)
            if sem_cliente:
                consulta = consulta.where(DocumentoModel.cliente_id.is_(None))
            return [documento_para_dominio(model) for model in sessao.scalars(consulta)]

    def obter(self, documento_id: int) -> DocumentoArmazenado | None:
        with self._sessoes() as sessao:
            model = sessao.get(DocumentoModel, documento_id)
            return documento_para_dominio(model) if model else None

    def historico(self, documento_id: int) -> list[Alteracao]:
        with self._sessoes() as sessao:
            consulta = (
                select(AlteracaoDocumentoModel)
                .where(AlteracaoDocumentoModel.documento_id == documento_id)
                .order_by(AlteracaoDocumentoModel.id)
            )
            return [
                Alteracao(m.campo, m.valor_anterior, m.valor_novo, m.origem, m.criado_em)
                for m in sessao.scalars(consulta)
            ]

    def atualizar(self, documento_id: int, novos_valores: dict[str, Any], origem: OrigemAlteracao) -> DocumentoArmazenado:
        """Aplica os valores que mudaram e registra cada mudança no histórico.

        `cliente_id` é tratado à parte: mover o documento é um REMANEJAMENTO, e o
        histórico guarda o nome dos clientes (mais legível que os ids).
        """
        with self._sessoes.begin() as sessao:
            model = sessao.get(DocumentoModel, documento_id)
            editados = set(model.campos_editados)

            for campo, novo in novos_valores.items():
                anterior = getattr(model, campo)
                if anterior == novo:
                    continue
                setattr(model, campo, novo)
                if campo == "cliente_id":
                    model.alteracoes.append(
                        AlteracaoDocumentoModel(
                            campo="cliente",
                            valor_anterior=_nome_do_cliente(sessao, anterior),
                            valor_novo=_nome_do_cliente(sessao, novo),
                            origem=OrigemAlteracao.REMANEJAMENTO,
                        )
                    )
                    continue
                model.alteracoes.append(
                    AlteracaoDocumentoModel(
                        campo=campo,
                        valor_anterior=_texto(anterior),
                        valor_novo=_texto(novo),
                        origem=origem,
                    )
                )
                if origem is OrigemAlteracao.EDICAO_MANUAL:
                    editados.add(campo)

            # Quem salvou a edição viu o cliente do documento e o manteve (ou trocou):
            # o cliente está confirmado, e o nome deixa de ser pendência (ver DocumentoArmazenado).
            if origem is OrigemAlteracao.EDICAO_MANUAL and "cliente_id" in novos_valores:
                if novos_valores["cliente_id"] is None:
                    editados.discard(CAMPO_CLIENTE)
                else:
                    editados.add(CAMPO_CLIENTE)

            # JSONB não avisa o SQLAlchemy quando a lista muda "por dentro":
            # atribuir uma lista NOVA é o que marca a coluna para o UPDATE.
            model.campos_editados = sorted(editados)
            sessao.flush()
            return documento_para_dominio(model)

    def excluir(self, documento_id: int) -> None:
        with self._sessoes.begin() as sessao:
            sessao.delete(sessao.get(DocumentoModel, documento_id))


def _texto(valor: Any) -> str | None:
    convertido = valor_como_texto(valor)
    return None if convertido is None else str(convertido)


def _nome_do_cliente(sessao, cliente_id: int | None) -> str:
    if cliente_id is None:
        return SEM_CLIENTE
    return sessao.scalar(select(ClienteModel.nome).where(ClienteModel.id == cliente_id)) or SEM_CLIENTE
