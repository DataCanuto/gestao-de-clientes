"""Configuração do logging.

Cada módulo cria o seu logger com logging.getLogger(__name__); aqui só se define
o formato e o nível, uma vez, na inicialização da aplicação. O nome do módulo no
log mostra de onde a mensagem veio (ex.: app.services.processamento_service).

Produção: com ARQUIVO_LOG definido, o log também vai para um arquivo com
rotação (até 5 arquivos de 5 MB): quando algo der errado num lote de
madrugada, o registro continua lá depois que a janela do servidor for fechada.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMATO = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
TAMANHO_MAXIMO_LOG = 5 * 1024 * 1024
ARQUIVOS_DE_LOG_GUARDADOS = 5


def configurar_logging(nivel: str = "INFO", arquivo: Path | None = None) -> None:
    destinos: list[logging.Handler] = [logging.StreamHandler()]
    if arquivo is not None:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        destinos.append(
            RotatingFileHandler(arquivo, maxBytes=TAMANHO_MAXIMO_LOG, backupCount=ARQUIVOS_DE_LOG_GUARDADOS, encoding="utf-8")
        )
    logging.basicConfig(level=nivel.upper(), format=FORMATO, handlers=destinos, force=True)
