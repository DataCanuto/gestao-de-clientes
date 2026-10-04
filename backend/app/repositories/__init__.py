"""Repositories: TODO o acesso a dados passa por aqui (nenhum SQL fora desta pasta).

Routers e services não sabem se os dados estão na memória ou no PostgreSQL:
conversam com os repositórios, que devolvem sempre objetos do DOMÍNIO
(nunca models do SQLAlchemy). Ver conversao.py.

- ProcessamentoRepository (contrato) + EmMemoria (testes) + Sql (produção)
- ClienteRepository, DocumentoRepository, ImportacaoRepository (PostgreSQL)
"""

from app.repositories.cliente_repository import ClienteRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.importacao_repository import ImportacaoRepository
from app.repositories.processamento_repository import (
    ProcessamentoRepository,
    ProcessamentoRepositoryEmMemoria,
)
from app.repositories.processamento_repository_sql import ProcessamentoRepositorySql

__all__ = [
    "ClienteRepository",
    "DocumentoRepository",
    "ImportacaoRepository",
    "ProcessamentoRepository",
    "ProcessamentoRepositoryEmMemoria",
    "ProcessamentoRepositorySql",
]
