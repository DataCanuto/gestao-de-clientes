"""Configuração do Alembic (migrations do banco).

O que é uma migration? Um script versionado que leva o banco de uma versão do
esquema para a seguinte (criar tabela, adicionar coluna...). O Alembic guarda,
na tabela `alembic_version`, qual foi a última aplicada. Assim, qualquer banco
(o seu, o de testes, o de produção) chega exatamente à mesma estrutura com:

    alembic upgrade head

Este arquivo diz ao Alembic:
- ONDE está o banco: a URL vem de app/core/config.py (.env), e nunca do
  alembic.ini, para a senha não ir para o Git. Nos testes, a URL é passada em
  `config.attributes["url"]`;
- O QUE o banco deveria ter: Base.metadata (os models). O
  `alembic revision --autogenerate` compara isso com o banco real e escreve o
  script das diferenças.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import obter_settings
from app.core.database import Base
import app.models  # noqa: F401  (registra todas as tabelas em Base.metadata)

config = context.config

if config.config_file_name is not None and not config.attributes.get("sem_logging"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url_do_banco() -> str:
    return config.attributes.get("url") or obter_settings().url_banco


def run_migrations_offline() -> None:
    """Modo offline: gera o SQL sem se conectar (alembic upgrade head --sql)."""
    context.configure(
        url=_url_do_banco(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url_do_banco(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # compare_type: detecta também mudança de TIPO de coluna (ex.: String(60) -> String(80)).
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
