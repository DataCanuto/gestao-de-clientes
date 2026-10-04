"""Leitor com cache: guarda o texto já lido, indexado pelo hash do conteúdo.

Padrão Decorator: LeitorComCache "envolve" outro leitor e tem a mesma interface
(ler_texto). Quem usa não percebe a diferença, só que a segunda leitura do mesmo
PDF é instantânea.

Por que cachear o TEXTO do OCR, e não o resultado da extração inteiro? Porque
parte do resultado vem do NOME do arquivo (situação, corretor). O mesmo PDF
enviado com outro nome precisa ter esses campos recalculados; só o OCR, que é a
parte cara (~1 s por página), pode ser reaproveitado.

O cache é qualquer MutableMapping: um dict em memória (padrão) ou um objeto que
persista em arquivo (ver scripts/verificar_paridade.py).
"""

import hashlib
from collections.abc import MutableMapping

from app.extraction.readers.base import TextReader


class LeitorComCache:
    def __init__(self, leitor: TextReader, cache: MutableMapping[str, str] | None = None) -> None:
        self._leitor = leitor
        self._cache: MutableMapping[str, str] = {} if cache is None else cache

    def ler_texto(self, conteudo: bytes) -> str:
        chave = hashlib.sha256(conteudo).hexdigest()
        if chave not in self._cache:
            self._cache[chave] = self._leitor.ler_texto(conteudo)
        return self._cache[chave]
