"""Prepara o banco de produção: cria o database (se não existir) e aplica as migrations.

Uso (a partir de APP/backend):

    .venv/Scripts/python -m scripts.preparar_banco

É chamado pelo instalar.ps1 e, a cada início, pelo iniciar.ps1: depois de
atualizar o código, o banco é levado à versão nova sozinho. Rodar de novo não
faz nada (o Alembic sabe em que versão o banco está).

Por que um script Python, e não psql no PowerShell? Ele usa a MESMA
configuração da aplicação (.env, senha com caracteres especiais, libpq no
Windows) e a mesma lógica dos testes (tests/banco/conftest.py).
"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from alembic import command
from alembic.config import Config
from app.core.config import DIRETORIO_BACKEND, obter_settings
import app.core.database  # noqa: F401  (ao ser importado, ajusta o PATH da libpq no Windows)


def criar_database_se_nao_existir(url_texto: str) -> bool:
    url = make_url(url_texto)
    engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")  # CREATE DATABASE fora de transação
    try:
        with engine.connect() as conexao:
            existe = conexao.scalar(text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": url.database})
            if not existe:
                conexao.execute(text(f'CREATE DATABASE "{url.database}"'))
            return not existe
    finally:
        engine.dispose()


def main() -> int:
    settings = obter_settings()
    url = settings.url_banco
    destino = make_url(url).render_as_string(hide_password=True)
    try:
        criado = criar_database_se_nao_existir(url)
    except OperationalError as erro:
        print(f"ERRO: não foi possível conectar ao PostgreSQL ({destino}).\n{erro.orig}", file=sys.stderr)
        print("Confira se o serviço do PostgreSQL está rodando e o usuário/senha no APP/backend/.env.", file=sys.stderr)
        return 1
    print(f"Banco {destino}: {'criado' if criado else 'já existia'}.")

    configuracao = Config(str(DIRETORIO_BACKEND / "alembic.ini"))
    configuracao.attributes["sem_logging"] = True
    command.upgrade(configuracao, "head")
    print("Estrutura do banco atualizada (alembic upgrade head).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
