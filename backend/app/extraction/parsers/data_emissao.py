"""Data de emissão da Nota Fiscal a partir do texto do OCR.

Migração de `extrair_data_texto` e `normalizar_data_malformada` (célula 8).
Os padrões e a ordem de tentativa foram preservados, porque são eles que definem
quais datas o notebook encontrava.

Diferença intencional: o notebook devolvia a string "dd/mm/aaaa"; aqui devolvemos
um `datetime.date`. Com isso, uma data impossível como 31/02 é descartada e passa
para o próximo padrão, em vez de ser aceita como texto.
"""

import re
from datetime import date, datetime

# Faixa de anos aceita. Filtra "datas" que são lixo de OCR (ex.: 81/05/1999).
# Mantida do notebook; precisa ser revista se surgirem notas fora da faixa.
ANO_MINIMO_VALIDO = 2020
ANO_MAXIMO_VALIDO = 2030

# Do mais específico ao mais genérico: a ordem importa.
PADROES_DATA_EMISSAO: tuple[str, ...] = (
    # 1. "Data e Hora de Emissão: 08/03/2023" (formato correto)
    r"Data e Hora de Emiss[ãa]o.*?:?\s*\"?(\d{2}/\d{2}/\d{4})",
    # 2. Mesmo rótulo com erros de OCR: dígitos extras ou barras faltando
    r"Data e Hora de Emiss.{1,3}o.*?:?\s*[\n\\]*\s*\"?(\d{2,4}[/]?\d{2,4}[/]?\d{4})",
    # 3. Sequência de 8 a 10 dígitos logo após "Data" ou "Emiss"
    r"(?:Data|Emiss).{0,30}?[\n\\:]*\s*\"?(\d{8,10})",
    # 4. Qualquer data dd/mm/aaaa no texto
    r"(\d{2}/\d{2}/\d{4})",
    # 5. Último recurso: 8 dígitos seguidos
    r"(\d{2}\d{2}\d{4})",
)

_FORMATO_DATA = re.compile(r"\d{2}/\d{2}/\d{4}")


def normalizar_data_malformada(texto_data: str) -> str | None:
    """Tenta reconstruir "dd/mm/aaaa" a partir de dígitos bagunçados pelo OCR.

    Exemplo: "14112/2023" -> "14/11/2023" (8 dígitos: ddmmaaaa).
    Com mais de 8 dígitos, usa os 4 últimos como ano e os anteriores como dia/mês.
    """
    apenas_digitos = re.sub(r"\D", "", texto_data.strip())

    if len(apenas_digitos) == 8:
        return f"{apenas_digitos[0:2]}/{apenas_digitos[2:4]}/{apenas_digitos[4:8]}"

    if len(apenas_digitos) > 8:
        ano = apenas_digitos[-4:]
        resto = apenas_digitos[:-4]
        if len(resto) >= 4:
            return f"{resto[-4:-2]}/{resto[-2:]}/{ano}"

    return None


def extrair_data_emissao(texto: str) -> date | None:
    """Percorre os padrões em ordem e devolve a primeira data válida."""
    for padrao in PADROES_DATA_EMISSAO:
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if not match:
            continue

        data_bruta = match.group(1)
        if "/" not in data_bruta or len(data_bruta) != 10:
            data_bruta = normalizar_data_malformada(data_bruta) or data_bruta

        data = _validar_data(data_bruta)
        if data is not None:
            return data

    return None


def converter_data_br(texto: str) -> date:
    """Converte "dd/mm/aaaa" em date. Usado pelas correções manuais."""
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date()


def _validar_data(data_bruta: str) -> date | None:
    if not _FORMATO_DATA.match(data_bruta):
        return None
    try:
        dia, mes, ano = map(int, data_bruta.split("/"))
    except ValueError:
        return None

    if not (ANO_MINIMO_VALIDO <= ano <= ANO_MAXIMO_VALIDO and 1 <= mes <= 12 and 1 <= dia <= 31):
        return None
    try:
        return date(ano, mes, dia)
    except ValueError:  # ex.: 31/02
        return None
