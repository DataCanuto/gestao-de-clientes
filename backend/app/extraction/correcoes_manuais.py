"""Correções manuais: valores informados por uma pessoa quando a extração falha.

No notebook eram dicionários fixos no código (células 14 e 23):

    datas_manuais = {"NF Fulano.pdf": "12/01/2023", ...}
    corretor_nao_encontrado = {"Planilha Comissão Fulano.pdf": "Juliana", ...}

Problemas: exigiam editar código para corrigir um dado, e as chaves ficaram
desatualizadas (algumas não correspondem mais a nenhum arquivo).

Agora vivem em um JSON (data/correcoes_manuais.json), no formato:

    {"<nome exato do arquivo>": {"<campo>": "<valor>"}}

Regra preservada do notebook: a correção SÓ preenche um campo que a extração
deixou vazio; nunca sobrescreve um valor extraído.

O arquivo real contém nomes de clientes e está no .gitignore. O repositório traz
apenas correcoes_manuais.example.json. Na Fase 3, correções passam a ser feitas
na tela de revisão e ficam versionadas no banco; este arquivo cobre o legado.
"""

import json
import logging
from dataclasses import fields, replace
from pathlib import Path
from typing import Any

from app.domain.entities import DadosExtraidos
from app.domain.nomes import normalizar_unicode
from app.extraction.parsers.data_emissao import converter_data_br

logger = logging.getLogger(__name__)


class CorrecoesManuais:
    def __init__(self, correcoes: dict[str, dict[str, str]] | None = None) -> None:
        self._correcoes = {
            normalizar_unicode(nome_arquivo): campos
            for nome_arquivo, campos in (correcoes or {}).items()
            if not nome_arquivo.startswith("_")
        }

    @classmethod
    def carregar(cls, caminho: Path | None) -> "CorrecoesManuais":
        if caminho is None or not caminho.exists():
            logger.info("Arquivo de correções manuais não encontrado (%s); seguindo sem correções.", caminho)
            return cls()
        return cls(json.loads(caminho.read_text(encoding="utf-8")))

    def __len__(self) -> int:
        return len(self._correcoes)

    def aplicar(self, nome_arquivo: str, dados: DadosExtraidos) -> tuple[DadosExtraidos, list[str]]:
        """Devolve (dados corrigidos, nomes dos campos que foram corrigidos)."""
        correcoes = self._correcoes.get(normalizar_unicode(nome_arquivo))
        if not correcoes:
            return dados, []

        campos_existentes = {campo.name for campo in fields(dados)}
        novos_valores: dict[str, Any] = {}
        for campo, valor in correcoes.items():
            if campo not in campos_existentes:
                logger.warning("Correção ignorada: '%s' não é campo de %s.", campo, type(dados).__name__)
                continue
            if getattr(dados, campo) is None:
                novos_valores[campo] = _converter(campo, valor)

        if not novos_valores:
            return dados, []
        return replace(dados, **novos_valores), sorted(novos_valores)


def _converter(campo: str, valor: str) -> Any:
    return converter_data_br(valor) if campo.startswith("data_") else valor
