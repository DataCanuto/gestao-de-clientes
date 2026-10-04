"""Nome do cliente no contexto da EXTRAÇÃO.

- extrair_nome_do_arquivo: regra legada `processar_nome` (célula 6 do notebook).
  O notebook usava o nome do arquivo, renomeado à mão, como chave do cliente.
  Agora ele é o FALLBACK, e o nome lido do conteúdo tem prioridade.
- limpar_nome_extraido: arruma um nome lido de DENTRO do PDF.

A chave canônica usada para comparar nomes fica em app/domain/nomes.py.
"""

import re

from app.domain.nomes import normalizar_unicode

# Prefixos que identificam o tipo no nome do arquivo (em Title Case, como no notebook).
PREFIXOS_TIPO_NO_NOME = ("Planilha Comissão ", "Prestação De Contas ", "Nf ")


def extrair_nome_do_arquivo(nome_arquivo: str) -> str:
    """Migração de `processar_nome` (célula 6 do notebook).

    Exemplos:
        "Planilha Comissão Ana Souza (VT Helena).pdf" -> "Ana Souza"
        "NF Espólio de João Lima.pdf"                -> "João Lima - Espólio"

    Diferenças intencionais em relação ao notebook:
    1. aplica NFC antes do .title() (ver domain.nomes.normalizar_unicode);
    2. remove o prefixo só do início; o notebook usava str.replace, que removeria
       o mesmo texto em qualquer posição do nome.
    """
    nome = normalizar_unicode(nome_arquivo).title()

    for prefixo in PREFIXOS_TIPO_NO_NOME:
        prefixo = prefixo.title()
        if nome.startswith(prefixo):
            nome = nome[len(prefixo) :]

    nome = nome.replace(".Pdf", "")
    nome = re.sub(r"\s*\(.*?\)", "", nome).strip()  # remove anotações "(VT Helena)", "(2)"...

    if nome.lower().startswith(("espólio", "espolio")):
        nome = re.sub(r"^(Esp[óo]lio( De)?)\s*", "", nome, flags=re.IGNORECASE)
        nome = nome.strip() + " - Espólio"

    return nome


def limpar_nome_extraido(nome: str | None) -> str | None:
    """Normaliza espaços e remove pontuação solta nas pontas de um nome lido do PDF."""
    if not nome:
        return None
    nome = re.sub(r"\s+", " ", normalizar_unicode(nome)).strip(" ,.;:-")
    return nome or None
