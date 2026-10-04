"""Banco de TESTES: PostgreSQL real, separado do banco de trabalho.

Por que PostgreSQL de verdade, e não SQLite em memória? Os models usam
recursos do PostgreSQL (JSONB, IDENTITY, CHECK). Testar em outro banco
esconderia justamente os erros que importam.

Como funciona:
- o banco "<POSTGRES_DB>-teste" (ex.: gestao-db-teste) é criado se não existir;
- o esquema é criado RODANDO AS MIGRATIONS do Alembic: os testes também
  garantem que as migrations levam a um banco que funciona com o código;
- antes e depois de cada teste, TRUNCATE em todas as tabelas: cada teste começa
  do zero e não deixa dados para trás.

Se o PostgreSQL não estiver acessível, estes testes são pulados (skip).
Para rodar só eles: pytest -m banco
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from alembic import command
from alembic.config import Config
from app.core.config import DIRETORIO_BACKEND, Settings
from app.core.database import Base, criar_fabrica_de_sessoes


@pytest.fixture(scope="session")
def url_banco_teste() -> str:
    url = make_url(Settings().url_banco)
    url_teste = url.set(database=f"{url.database}-teste")
    try:
        _criar_banco_se_nao_existir(url, url_teste.database)
    except OperationalError as erro:
        pytest.skip(f"PostgreSQL indisponível: {erro.orig}")

    url_texto = url_teste.render_as_string(hide_password=False)
    configuracao = Config(str(DIRETORIO_BACKEND / "alembic.ini"))
    configuracao.attributes["url"] = url_texto
    configuracao.attributes["sem_logging"] = True
    command.upgrade(configuracao, "head")
    return url_texto


def _criar_banco_se_nao_existir(url_principal, nome_banco_teste: str) -> None:
    # CREATE DATABASE não roda dentro de transação: AUTOCOMMIT.
    engine = create_engine(url_principal.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conexao:
        existe = conexao.scalar(text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": nome_banco_teste})
        if not existe:
            conexao.execute(text(f'CREATE DATABASE "{nome_banco_teste}"'))
    engine.dispose()


@pytest.fixture
def sessoes(url_banco_teste):
    fabrica = criar_fabrica_de_sessoes(url_banco_teste)
    _esvaziar(fabrica)  # antes: o teste começa do zero
    yield fabrica
    _esvaziar(fabrica)  # depois: nada de teste fica no banco (ex.: se o servidor for apontado para ele)
    fabrica.kw["bind"].dispose()


def _esvaziar(fabrica) -> None:
    tabelas = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with fabrica.begin() as sessao:
        sessao.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))
