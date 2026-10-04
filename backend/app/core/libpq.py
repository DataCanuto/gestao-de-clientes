"""Windows: garantir que o driver do PostgreSQL encontre a libpq.

Problema (encontrado em produção, 2026-09-30): com o **Smart App Control** do
Windows 11 ligado, DLLs sem "reputação" conhecida pela Microsoft são
bloqueadas ("Uma política de Controle de Aplicativo bloqueou este arquivo").
Isso atingiu a libpq que vem DENTRO do pacote `psycopg[binary]`.

O psycopg 3 tenta três implementações, nesta ordem: "c", "binary" e "python".
A "python" usa a libpq instalada no sistema (via ctypes), procurando-a nas
pastas do PATH. O instalador oficial do PostgreSQL para Windows já traz uma
libpq em `C:/Program Files/PostgreSQL/<versão>/bin`, e essa não é bloqueada.

Solução: antes do primeiro uso do driver, colocar essa pasta no PATH do
processo. Se a implementação "binary" funcionar (Linux, Docker, Windows sem o
bloqueio), nada muda: ela tem prioridade e não depende do PATH.

Alternativa descartada: desligar o Smart App Control. É uma decisão de
segurança da máquina e, uma vez desligado, o Windows só permite religá-lo
reinstalando o sistema.
"""

import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PASTA_PADRAO_POSTGRESQL = Path(r"C:\Program Files\PostgreSQL")


def localizar_pasta_da_libpq(configurada: Path | None = None) -> Path | None:
    """Pasta com a libpq.dll: a configurada (POSTGRES_BIN_DIR) ou a da maior versão instalada."""
    if configurada is not None:
        return configurada if (configurada / "libpq.dll").exists() else None
    if not PASTA_PADRAO_POSTGRESQL.exists():
        return None
    candidatas = [p for p in PASTA_PADRAO_POSTGRESQL.glob("*/bin") if (p / "libpq.dll").exists()]
    # "18" > "9.6": ordena pelo número da versão, e não pelo texto.
    return max(candidatas, key=lambda p: _versao(p.parent.name), default=None)


def disponibilizar_libpq(configurada: Path | None = None) -> Path | None:
    """No Windows, acrescenta a pasta da libpq ao PATH do processo (uma única vez)."""
    if sys.platform != "win32":
        return None
    pasta = localizar_pasta_da_libpq(configurada)
    if pasta is None:
        return None
    caminho_atual = os.environ.get("PATH", "")
    if str(pasta).lower() not in caminho_atual.lower():
        os.environ["PATH"] = f"{pasta}{os.pathsep}{caminho_atual}"
        logger.debug("libpq do PostgreSQL disponibilizada a partir de %s", pasta)
    return pasta


def _versao(texto: str) -> tuple[int, ...]:
    return tuple(int(numero) for numero in re.findall(r"\d+", texto)) or (0,)
