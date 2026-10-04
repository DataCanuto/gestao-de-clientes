"""Nome do cliente a partir do OCR da Nota Fiscal.

Regra NOVA (não existia no notebook, que só extraía a data). O nome fica no
campo "Discriminação dos serviços", que aparece em DOIS layouts nos arquivos:

    Layout atual:   "Cliente: ANA SOUZA Valor Acordo: R$ 10.000,00"
    Layout antigo:  "Serviços de cálculos referente Processo n° 0001002-17.2014... DE: ANA SOUZA, no Valor"
                    "... Processo n° 0001005-71.2014... espólio de: ANA SOUZA, no"
                    "... REFERENTE AO LEVANTAMENTO DE VALORES DO ANA SOUZA, PROCESSO N° ..."

Os padrões são tentados em ordem. O OCR introduz ruído ("espélio", "n®",
"Servigos"), por isso os padrões aceitam variações nesses trechos, e o nome
capturado passa por uma limpeza (ver _limpar). Pequenos erros de letra que
sobram ("MARTA" por "MARIA") são reconciliados na consolidação, com o nome
lido da camada de texto da Planilha ou da Prestação.
"""

import re

MINIMO_LETRAS_NOME = 5
MINIMO_PALAVRAS_NOME = 2

# --- Layout atual: rótulo "Cliente:" -----------------------------------------
PADRAO_CLIENTE_NF = re.compile(r"\bCliente[ \t]*:?[ \t]*([^\n]+)", re.IGNORECASE)

# Onde o nome termina. Tudo a partir do primeiro destes trechos é descartado:
PADRAO_FIM_DO_NOME = re.compile(
    r"\s+(?:Valor|Acordo|R\$|R§)"  # próximo rótulo: "Valor Acordo: R$ ..."
    r"|,"  # "ANA SOUZA, representado por..."
    r"|\("  # anotação: "(Rep. Por ...)", "(FALECIDO)"
    r"|\s+V[1lI]\.\s"  # "Vl. Final", "V1. TOTAL" (situação colada ao nome)
    r"|(?-i:\s+no\s)",  # "no Valor" em minúsculas (sem pegar "NO" dentro de nomes)
    re.IGNORECASE,
)
PADRAO_LIXO_OCR_FINAL = re.compile(r"\s+[a-z]{1,2}$")  # ex.: um "no" solto no fim
# Rótulos que o OCR às vezes captura no lugar do nome.
PADRAO_NAO_E_NOME = re.compile(r"^(?:VALOR|DADOS\s+BANC)", re.IGNORECASE)

# --- Layout antigo: nome depois do número do processo --------------------------
# O nome é capturado só em MAIÚSCULAS: assim a captura para sozinha antes de
# "no valor", "no Valor Total" etc.
_NOME_EM_MAIUSCULAS = r"(?P<nome>[A-ZÀ-Ý][A-ZÀ-Ý .'\-]+)"
PADRAO_NOME_APOS_PROCESSO = re.compile(
    r"(?i:processo)\s+n\S{0,3}\s*\d[\d.\- ]{8,}\d\s*[.,]?\s*"  # "Processo n° 0001002-17.2014.8.05.0001,"
    r"(?P<espolio>(?i:esp\S{1,2}lio)\s+)?"  # "espólio " (OCR: espélio, espdlio)
    r"(?i:de:?\s+)?" + _NOME_EM_MAIUSCULAS
)
PADRAO_NOME_APOS_LEVANTAMENTO = re.compile(r"(?i:levantamento de valores d[oa])\s+" + _NOME_EM_MAIUSCULAS)


def extrair_nome_nota_fiscal(texto: str) -> str | None:
    return _pelo_rotulo_cliente(texto) or _pelo_texto_apos_processo(texto)


def _pelo_rotulo_cliente(texto: str) -> str | None:
    for match in PADRAO_CLIENTE_NF.finditer(texto):
        candidato = _limpar(match.group(1))
        if _parece_nome(candidato):
            return candidato
    return None


def _pelo_texto_apos_processo(texto: str) -> str | None:
    for padrao in (PADRAO_NOME_APOS_PROCESSO, PADRAO_NOME_APOS_LEVANTAMENTO):
        match = padrao.search(texto)
        if not match:
            continue
        nome = _limpar(match.group("nome"))
        if not _parece_nome(nome):
            continue
        return f"ESPÓLIO DE {nome}" if match.groupdict().get("espolio") else nome
    return None


def _limpar(candidato: str) -> str:
    candidato = PADRAO_FIM_DO_NOME.split(candidato, maxsplit=1)[0]
    return PADRAO_LIXO_OCR_FINAL.sub("", candidato).strip(" .:;-'")


def _parece_nome(texto: str) -> bool:
    return (
        sum(caractere.isalpha() for caractere in texto) >= MINIMO_LETRAS_NOME
        and len(texto.split()) >= MINIMO_PALAVRAS_NOME
        and not PADRAO_NAO_E_NOME.match(texto)
    )
