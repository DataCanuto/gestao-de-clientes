"""Acesso às tabelas `cliente` e `cliente_chave`.

O repositório só lê e grava: não decide nada. Validações ("o cliente existe?",
"a chave já é usada?") ficam no ClienteService, que chama os métodos de
consulta antes dos de gravação.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import FabricaDeSessoes
from app.domain.entities import FichaCliente
from app.domain.enums import OrigemAlteracao
from app.models import AlteracaoDocumentoModel, ClienteChaveModel, ClienteModel, DocumentoModel
from app.repositories.conversao import cliente_para_ficha


class ClienteRepository:
    def __init__(self, sessoes: FabricaDeSessoes) -> None:
        self._sessoes = sessoes

    def listar(self, trecho_da_chave: str | None = None) -> list[FichaCliente]:
        with self._sessoes() as sessao:
            consulta = select(ClienteModel).options(selectinload(ClienteModel.documentos)).order_by(ClienteModel.nome)
            if trecho_da_chave:
                consulta = consulta.where(ClienteModel.chave.contains(trecho_da_chave))
            return [cliente_para_ficha(model) for model in sessao.scalars(consulta)]

    def obter(self, cliente_id: int) -> FichaCliente | None:
        with self._sessoes() as sessao:
            model = sessao.get(ClienteModel, cliente_id, options=[selectinload(ClienteModel.documentos)])
            return cliente_para_ficha(model) if model else None

    def mapa_de_chaves(self) -> dict[str, int]:
        """Todas as chaves (principais e apelidos) -> id do cliente. Usado pela comparação."""
        with self._sessoes() as sessao:
            linhas = sessao.execute(select(ClienteChaveModel.chave, ClienteChaveModel.cliente_id))
            return {chave: cliente_id for chave, cliente_id in linhas}  # cada Row se desempacota como tupla

    def id_pela_chave(self, chave: str) -> int | None:
        """Qual cliente usa esta chave (principal ou apelido)?"""
        with self._sessoes() as sessao:
            return sessao.scalar(select(ClienteChaveModel.cliente_id).where(ClienteChaveModel.chave == chave))

    def criar(self, nome: str, chave: str, espolio: bool) -> FichaCliente:
        with self._sessoes.begin() as sessao:
            model = ClienteModel(nome=nome, chave=chave, espolio=espolio, chaves=[ClienteChaveModel(chave=chave)])
            sessao.add(model)
            sessao.flush()
            return cliente_para_ficha(model)

    def atualizar(self, cliente_id: int, nome: str, chave: str, espolio: bool) -> FichaCliente:
        """Renomear muda a chave principal; a chave antiga continua como apelido."""
        with self._sessoes.begin() as sessao:
            model = sessao.get(ClienteModel, cliente_id, options=[selectinload(ClienteModel.documentos)])
            model.nome, model.espolio = nome, espolio
            if chave != model.chave:
                model.chave = chave
                if sessao.get(ClienteChaveModel, chave) is None:
                    sessao.add(ClienteChaveModel(chave=chave, cliente_id=cliente_id))
            sessao.flush()
            return cliente_para_ficha(model)

    def excluir(self, cliente_id: int) -> None:
        with self._sessoes.begin() as sessao:
            sessao.delete(sessao.get(ClienteModel, cliente_id))

    def unir(self, destino_id: int, origem_id: int) -> FichaCliente:
        """Move documentos e chaves de `origem` para `destino` e remove `origem`, numa só transação.

        As chaves da origem viram apelidos do destino: a próxima importação de um
        documento com o nome antigo já vai para o cliente certo.
        """
        with self._sessoes.begin() as sessao:
            destino = sessao.get(ClienteModel, destino_id)
            origem = sessao.get(ClienteModel, origem_id, options=[selectinload(ClienteModel.documentos)])

            for documento in origem.documentos:
                documento.cliente_id = destino_id
                documento.alteracoes.append(
                    AlteracaoDocumentoModel(
                        campo="cliente",
                        valor_anterior=origem.nome,
                        valor_novo=destino.nome,
                        origem=OrigemAlteracao.UNIAO_DE_CLIENTES,
                    )
                )
            sessao.execute(
                update(ClienteChaveModel).where(ClienteChaveModel.cliente_id == origem_id).values(cliente_id=destino_id)
            )
            destino.espolio = destino.espolio or origem.espolio
            sessao.flush()
            sessao.expire(origem)  # os documentos e chaves já não pertencem mais à origem
            sessao.delete(origem)
            sessao.flush()

            recarregado = sessao.get(
                ClienteModel, destino_id, options=[selectinload(ClienteModel.documentos)], populate_existing=True
            )
            return cliente_para_ficha(recarregado)

    def contar_documentos(self, cliente_id: int) -> int:
        with self._sessoes() as sessao:
            return len(sessao.scalars(select(DocumentoModel.id).where(DocumentoModel.cliente_id == cliente_id)).all())
