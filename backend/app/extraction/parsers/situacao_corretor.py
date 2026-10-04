"""Situação e corretor a partir do NOME do arquivo da Planilha Comissão.

Migração de `extrair_situacao_corretor` (célula 17). Hoje é a regra RESERVA de
parsers/anotacao.py (usada quando nenhuma sigla conhecida aparece). A informação não está no
conteúdo do PDF: é uma anotação feita à mão no nome do arquivo, entre parênteses:

    "Planilha Comissão Ana Souza (VT Helena e Inês).pdf" -> ("VT", "HELENA E INÊS")
    "Planilha Comissão Ana Souza (2 Inct. Inês).pdf"    -> ("2 INCT.", "INÊS")

Regra preservada como no notebook, incluindo uma limitação conhecida: em
"(Vl Inct. Viviane)" o resultado é ("VL", "INCT. VIVIANE"), porque o padrão
assume que a situação é UMA palavra (ver docs/migration.md).

Diferença intencional: o notebook aplicava a função ao CAMINHO completo do
arquivo; aqui ela recebe só o nome, então parênteses em nomes de pastas não
interferem mais.
"""

import re

# Aplicados sobre o texto em MAIÚSCULAS, nesta ordem.
PADROES_SITUACAO_CORRETOR: tuple[str, ...] = (
    # 1. Dois ou mais espaços separam situação e corretor
    r"\(\s*(.+?)\s{2,}(.+?)\s*\)",
    # 2. Número + situação + ponto opcional + nome: "(2 INCT. INÊS)"
    r"\(\s*(\d+\s+[A-Z]+\.?)\s+([A-Z][^)]+?)\s*\)",
    # 3. Situação com ponto opcional + nome: "(INCTR. TELES)", "(VT HELENA)"
    r"\(\s*([A-Z]+\.?)\s+([A-Z][^)]+?)\s*\)",
    # 4. Palavra acentuada + nome: "(CORREÇÃO RAFAEL)"
    r"\(\s*([A-Z][A-ZÀ-Ú]+)\s+([A-Z][^)]+?)\s*\)",
)

# Validação contra falsos positivos (mantida do notebook).
TAMANHO_MAXIMO_SITUACAO = 30
TAMANHO_MINIMO_CORRETOR = 2


def extrair_situacao_corretor(nome_arquivo: str) -> tuple[str | None, str | None]:
    """Devolve (situação, corretor) ou (None, None) se nenhum padrão casar."""
    texto = nome_arquivo.upper()

    for padrao in PADROES_SITUACAO_CORRETOR:
        match = re.search(padrao, texto)
        if not match:
            continue
        situacao = match.group(1).strip()
        corretor = match.group(2).strip()
        if len(situacao) <= TAMANHO_MAXIMO_SITUACAO and len(corretor) >= TAMANHO_MINIMO_CORRETOR:
            return situacao, corretor

    return None, None
