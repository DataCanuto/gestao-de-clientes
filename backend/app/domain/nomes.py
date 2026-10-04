"""Identidade do cliente pelo nome: normalização, chave canônica e similaridade.

Por que no DOMÍNIO e não na extração? Estas regras respondem "duas grafias são
a mesma pessoa?". Quem pergunta isso é a consolidação, a comparação com o banco
(Fase 4) e a busca de clientes, não apenas a leitura de PDFs. Morando aqui, a
dependência tem um sentido só: extraction -> domain.
"""

import re
import unicodedata
from difflib import SequenceMatcher

# "Rep", "Rep.", "representado por", "representada por": tudo a partir daí é o
# REPRESENTANTE do espólio, não o cliente. Sai da chave (mas continua no nome exibido).
PADRAO_REPRESENTANTE = re.compile(r"\s+(?:REP|REPRESENTAD[OA])\b.*$")

# Prefixo de espólio e variações encontradas nos documentos reais: "ESPÓLIO DE",
# "ESP." (abreviação), "ESPELIO" (erro de OCR) e "EPOLIO" (erro de digitação).
PADRAO_ESPOLIO_INICIO = re.compile(r"^(?:ES?P[OE]LIO|ESP\.)(?:\s+D[EOA])?\s+")
PADRAO_ESPOLIO_FIM = re.compile(r"\s*-?\s*ESP[OE]LIO$")  # "Ana Souza - Espólio" (nomes de arquivo)
SEPARADOR_REPRESENTANTE = " - "


def normalizar_unicode(texto: str) -> str:
    """Converte para a forma NFC (acento "colado" na letra).

    Alguns arquivos do projeto têm nomes em NFD (letra + acento separado, comum
    em arquivos vindos do macOS). Sem isso, "Célia" em NFD vira "CéLia" no
    .title() e nunca casa com o mesmo nome em NFC.
    """
    return unicodedata.normalize("NFC", texto)


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _maiusculas_sem_acento(nome: str) -> str:
    texto = remover_acentos(normalizar_unicode(nome)).upper()
    return re.sub(r"\s+", " ", texto).strip()


def eh_espolio(nome: str | None) -> bool:
    """O nome indica um espólio? ("Espólio de Ana", "Ana - Espólio", "Esp. Ana"...)."""
    if not nome:
        return False
    texto = _maiusculas_sem_acento(nome)
    return bool(PADRAO_ESPOLIO_INICIO.match(texto) or PADRAO_ESPOLIO_FIM.search(texto))


def gerar_chave_cliente(nome: str | None) -> str:
    """Forma canônica de um nome, usada para AGRUPAR e COMPARAR (não para exibir).

    Todos estes viram "JOAO DA SILVA":
        "João da Silva", "JOAO DA SILVA", "Joao  da Silva."

    E todos estes viram "OTAVIO RAMOS":
        "Otavio Ramos"                                (antes do falecimento)
        "Otavio Ramos Rep Beatriz Ramos - Espólio"    (nome de arquivo)
        "ESPOLIO DE OTAVIO RAMOS"                     (texto da Prestação)
        "ESPÓLIO DE OTAVIO RAMOS - BEATRIZ RAMOS"     (célula da Planilha)
        "Espélio OTAVIO RAMOS, representado por..."   (OCR da NF)

    O espólio NÃO faz parte da chave: "Espólio de X" é o mesmo cliente X depois do
    falecimento (o processo continua o mesmo). A informação não se perde: a ficha
    guarda o indicador `espolio` e o nome exibido mantém a grafia original.
    """
    if not nome:
        return ""

    texto = _maiusculas_sem_acento(nome)
    if PADRAO_ESPOLIO_INICIO.match(texto):
        texto = PADRAO_ESPOLIO_INICIO.sub("", texto)
        # Na tabela da Planilha: "ESPÓLIO DE ANTONIO LIMA - MARIA LIMA", em que
        # o trecho após " - " é o representante.
        texto = texto.split(SEPARADOR_REPRESENTANTE, 1)[0]
    texto = PADRAO_ESPOLIO_FIM.sub("", texto)

    texto = re.sub(r"[^\w\s]", " ", texto)  # pontuação vira espaço
    texto = re.sub(r"\s+", " ", texto).strip()
    return PADRAO_REPRESENTANTE.sub("", texto).strip()


def similaridade_nomes(nome_a: str | None, nome_b: str | None) -> float:
    """Similaridade entre 0 e 1 das CHAVES de dois nomes (difflib, biblioteca padrão).

    Usada para avisar quando o nome do conteúdo diverge do nome do arquivo e para
    apontar "possível mesma pessoa".
    """
    return similaridade_chaves(gerar_chave_cliente(nome_a), gerar_chave_cliente(nome_b))


def similaridade_chaves(chave_a: str, chave_b: str) -> float:
    if not chave_a or not chave_b:
        return 0.0
    return SequenceMatcher(None, chave_a, chave_b).ratio()
