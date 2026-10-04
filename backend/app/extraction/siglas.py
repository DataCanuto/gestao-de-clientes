"""Tabela de siglas: palavra do nome do arquivo -> Situacao.

A tabela fica em data/situacao_siglas.json, e não no código, porque é um DADO
do negócio: quem conhece as siglas do escritório pode editá-la sem programar.
Ao carregar, cada valor é convertido para o enum Situacao; um valor inválido
no JSON gera erro na inicialização, e não um dado errado silencioso depois.
"""

import json
from pathlib import Path

from app.domain.enums import Situacao
from app.domain.nomes import remover_acentos


class TabelaSiglas:
    def __init__(self, siglas: dict[str, str]) -> None:
        self._siglas = {self.normalizar(palavra): Situacao(situacao) for palavra, situacao in siglas.items()}

    @classmethod
    def carregar(cls, caminho: Path) -> "TabelaSiglas":
        return cls(json.loads(caminho.read_text(encoding="utf-8"))["siglas"])

    @staticmethod
    def normalizar(palavra: str) -> str:
        return remover_acentos(palavra).upper().strip(" .")

    def situacao_da_palavra(self, palavra: str) -> Situacao | None:
        return self._siglas.get(self.normalizar(palavra))
