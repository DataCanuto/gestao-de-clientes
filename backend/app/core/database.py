"""Conexão com o PostgreSQL via SQLAlchemy 2.

Três peças:
- Engine: sabe COMO se conectar (URL, pool de conexões). Uma por aplicação.
- sessionmaker: fábrica de Sessions. Uma Session é uma "conversa" com o banco,
  que termina em commit (grava) ou rollback (descarta).
- Base: classe-mãe dos models (app/models). O `metadata` dela conhece todas as
  tabelas e é o que o Alembic compara com o banco para gerar as migrations.

Convenção de nomes: sem ela, o PostgreSQL inventa nomes para chaves e índices
("documento_cliente_id_fkey"...), e o Alembic não consegue gerar migrations
estáveis para alterá-los depois. Com ela, todo nome é previsível.
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import obter_settings
from app.core.libpq import disponibilizar_libpq

# Antes de qualquer conexão (servidor, Alembic, testes, scripts): no Windows com
# Smart App Control, o driver precisa da libpq do PostgreSQL instalado. Todos
# esses caminhos importam este módulo, por isso a chamada fica aqui.
disponibilizar_libpq(obter_settings().postgres_bin_dir)

CONVENCAO_DE_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",  # todas as colunas da restrição
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


FabricaDeSessoes = sessionmaker[Session]


def criar_fabrica_de_sessoes(url_banco: str) -> FabricaDeSessoes:
    # pool_pre_ping: testa a conexão antes de usar (o PostgreSQL pode ter
    # derrubado conexões ociosas, por exemplo depois de reiniciar).
    engine = create_engine(url_banco, pool_pre_ping=True)
    # expire_on_commit=False: os objetos continuam legíveis depois do commit
    # (os repositórios convertem para o domínio ainda dentro da sessão).
    return sessionmaker(engine, expire_on_commit=False)
