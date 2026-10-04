"""Anotação entre parênteses no nome do arquivo: situação e corretor.

Os arquivos são anotados à mão pelo escritório:

    "Planilha Comissão Ana Souza (VT Helena e Inês).pdf"
    "Planilha Comissão Ana Souza (Vl Inct. Viviane).pdf"
    "NF Ana Souza (CANCELADA POR DUPLICIDADE).pdf"

Regra (levantada nos relatórios, ver docs/migration.md):
    1. separa o texto dos parênteses em palavras;
    2. as palavras que são siglas conhecidas (situacao_siglas.json) definem a
       situação. "V", "Vl" e "Valor" são só a abreviação de "valor" e não estão
       na tabela: em "Vl Inct.", quem define a situação é "Inct";
    3. o corretor é o que vem DEPOIS da última sigla.

Por que não usar só a regra do notebook (extrair_situacao_corretor)? Ela assume
que a situação é a PRIMEIRA palavra. Em "(Vl Inct. Viviane)" o notebook lia
situação "VL" e corretor "INCT. VIVIANE", enquanto o relatório do escritório
(Tabela Clientes) registra "Incontroverso" e "Viviane". A regra do notebook
continua sendo usada como reserva quando nenhuma sigla conhecida aparece
(ex.: "(correção Rafael)"), para não perder o corretor.
"""

import re
from dataclasses import dataclass

from app.domain.enums import Situacao
from app.extraction.siglas import TabelaSiglas

# Se aparecerem duas situações na mesma anotação, a mais específica vence.
# Ex.: uma NF "(Inct cancelada)" é, antes de tudo, uma nota cancelada.
PRIORIDADE_SITUACAO: tuple[Situacao, ...] = (
    Situacao.CANCELADO,
    Situacao.VALOR_INCONTROVERSO,
    Situacao.ACORDO,
    Situacao.VALOR_FINAL,
    Situacao.VALOR_TOTAL,
)

PADRAO_PARENTESES = re.compile(r"\(([^()]*)\)")
PADRAO_PALAVRA = re.compile(r"[^\W\d_]+|\d+")  # palavras (inclusive acentuadas) ou números


@dataclass(frozen=True, slots=True)
class Anotacao:
    texto: str | None  # conteúdo dos parênteses, ex.: "Vl Inct. Viviane"
    situacao: Situacao | None
    corretor: str | None


def interpretar_anotacao(nome_arquivo: str, siglas: TabelaSiglas) -> Anotacao:
    """Devolve a primeira anotação entre parênteses que contém uma sigla de situação."""
    grupos = [grupo.strip() for grupo in PADRAO_PARENTESES.findall(nome_arquivo) if grupo.strip()]

    for grupo in grupos:
        palavras = PADRAO_PALAVRA.findall(grupo)
        encontradas = [
            (posicao, situacao)
            for posicao, palavra in enumerate(palavras)
            if (situacao := siglas.situacao_da_palavra(palavra)) is not None
        ]
        if not encontradas:
            continue

        situacao = min((s for _, s in encontradas), key=PRIORIDADE_SITUACAO.index)
        ultima_sigla = max(posicao for posicao, _ in encontradas)
        corretor = " ".join(palavras[ultima_sigla + 1 :]).upper() or None
        return Anotacao(texto=grupo, situacao=situacao, corretor=corretor)

    return Anotacao(texto=grupos[0] if grupos else None, situacao=None, corretor=None)
