"""Models (SQLAlchemy): as TABELAS do PostgreSQL, descritas em Python.

Por que "Model" no nome das classes (ClienteModel)? Para não confundir com as
entidades do domínio (FichaCliente, DocumentoArmazenado). O model sabe de
colunas, chaves e índices; a entidade do domínio sabe das regras. Os
repositórios convertem um no outro.

Todos os models são importados aqui para que Base.metadata conheça todas as
tabelas (o Alembic depende disso).
"""

from app.models.cliente import ClienteChaveModel, ClienteModel
from app.models.documento import AlteracaoDocumentoModel, DocumentoModel
from app.models.importacao import ImportacaoModel
from app.models.processamento import ProcessamentoItemModel, ProcessamentoModel

__all__ = [
    "AlteracaoDocumentoModel",
    "ClienteChaveModel",
    "ClienteModel",
    "DocumentoModel",
    "ImportacaoModel",
    "ProcessamentoItemModel",
    "ProcessamentoModel",
]
