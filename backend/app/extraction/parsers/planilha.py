r"""Nome do cliente a partir do CONTEÚDO da Planilha Comissão.

Regra NOVA (não existia no notebook): a identidade do cliente vem de dentro do
documento, e não do nome do arquivo renomeado à mão.

1. Regra principal, pela TABELA: o nome é a célula logo abaixo do cabeçalho
   "Cliente" (primeira coluna da tabela de valores):

       | Cliente              | Valor Atualizado | ...
       | ANA SOUZA            | 298.924,91       | ...

2. Regra reserva, pelo TEXTO (quando a tabela não é reconhecida): a primeira
   linha que começa com letras e é seguida, NA MESMA LINHA, por um valor
   monetário no formato brasileiro (1.234,56).

Atenção ao separador `[ \t]+` (e não `\s+`) na regra reserva: `\s` inclui a
quebra de linha, e a primeira versão aceitava o título "Planilha Controle de
Pagamentos" seguido do "18,33%" da linha de baixo como se fosse "nome + valor".
O erro foi pego pelo scripts/verificar_paridade.py.
"""

import re

from app.extraction.readers.base import Tabela

CABECALHO_COLUNA_CLIENTE = "cliente"

PADRAO_LINHA_CLIENTE_PLANILHA = re.compile(
    r"^[ \t]*([A-Za-zÀ-ÿ][^\d\n$]{2,}?)[ \t]+\d{1,3}(?:\.\d{3})*,\d{2}",
    re.MULTILINE,
)


def extrair_nome_da_tabela(tabelas: list[Tabela]) -> str | None:
    """Procura a célula "Cliente" e devolve a primeira célula preenchida abaixo dela."""
    for tabela in tabelas:
        for indice_linha, linha in enumerate(tabela):
            for indice_coluna, celula in enumerate(linha):
                if _texto_da_celula(celula).lower() == CABECALHO_COLUNA_CLIENTE:
                    return _primeira_celula_abaixo(tabela, indice_linha, indice_coluna)
    return None


def extrair_nome_do_texto(texto: str) -> str | None:
    match = PADRAO_LINHA_CLIENTE_PLANILHA.search(texto)
    return match.group(1).strip() if match else None


def _primeira_celula_abaixo(tabela: Tabela, indice_linha: int, indice_coluna: int) -> str | None:
    for linha in tabela[indice_linha + 1 :]:
        if indice_coluna < len(linha) and _texto_da_celula(linha[indice_coluna]):
            return _somente_o_nome(_texto_da_celula(linha[indice_coluna])) or None
    return None


def _somente_o_nome(texto: str) -> str:
    """Quando a planilha não tem linhas verticais, o find_tables junta a linha
    inteira numa célula: "ANA SOUZA 28.149,22 18/04/24 ...". Nome não tem
    dígitos, então cortamos no primeiro número."""
    return re.split(r"\s*\d", texto, maxsplit=1)[0].strip()


def _texto_da_celula(celula: str | None) -> str:
    """Células com quebra de linha ("ESPÓLIO DE ANA\nSOUZA") viram uma linha só."""
    return re.sub(r"\s+", " ", celula or "").strip()
