"""Nome e número do processo a partir do texto da Prestação de Contas.

Migração de `extrair_dados_prestacao` (célula 26). O texto do documento é assim:

    Salvador, 16 de fevereiro de 2023.
    À
      ANA SOUZA               <- nome do cliente
    Referente: Prestação de Contas
    Processo: 0001001-37.2014.8.05.0001

Diferença intencional: o notebook devolvia textos-marcadores ("Nome não
encontrado", "Número não encontrado") misturados aos dados. Aqui devolvemos None,
e quem chama decide como exibir a ausência. No banco, isso vira NULL.

Limitação herdada (mantida por paridade): em alguns PDFs o PyPDF2 junta as linhas
e o nome sai como "ANA SOUZA Referente: Prestação de Contas". O campo
`nome_encontrado` guarda o valor bruto, como o notebook. Para IDENTIFICAR o
cliente usamos limpar_nome_prestacao, que corta a partir de "Referente".
"""

import re

PADRAO_NOME_PRESTACAO = re.compile(r"À\s+([^\n]+)")
PADRAO_NUMERO_PROCESSO = re.compile(r"(?:Processo|N° Processo)[:\s]*([\d\.\-/]+)", re.IGNORECASE)
PADRAO_TEXTO_APOS_NOME = re.compile(r"\s+Referente\b.*$", re.IGNORECASE)


def extrair_nome_prestacao(texto: str) -> str | None:
    match = PADRAO_NOME_PRESTACAO.search(texto)
    return match.group(1).strip() if match else None


def limpar_nome_prestacao(nome: str | None) -> str | None:
    """Remove o texto que o PyPDF2 às vezes cola após o nome ("Referente: ...")."""
    if not nome:
        return None
    return PADRAO_TEXTO_APOS_NOME.sub("", nome).strip() or None


def extrair_numero_processo(texto: str) -> str | None:
    match = PADRAO_NUMERO_PROCESSO.search(texto)
    return match.group(1).strip() if match else None
