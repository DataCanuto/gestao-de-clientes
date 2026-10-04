"""Regra legada `processar_nome`: o nome do cliente a partir do nome do arquivo."""

import unicodedata

import pytest

from app.extraction.parsers.nome_cliente import extrair_nome_do_arquivo, limpar_nome_extraido


@pytest.mark.parametrize(
    ("nome_arquivo", "esperado"),
    [
        ("Planilha Comissão Ana Souza (VT Helena).pdf", "Ana Souza"),
        ("Prestação de Contas JOÃO DA SILVA.pdf", "João Da Silva"),
        ("NF Pedro Lima (2).pdf", "Pedro Lima"),
        ("NF Espólio de João Lima.pdf", "João Lima - Espólio"),
        ("NF Espolio Maria Lima rep. Ana Lima (Final).pdf", "Maria Lima Rep. Ana Lima - Espólio"),
    ],
)
def test_extrair_nome_do_arquivo(nome_arquivo, esperado):
    assert extrair_nome_do_arquivo(nome_arquivo) == esperado


def test_nome_em_nfd_gera_o_mesmo_resultado_que_em_nfc():
    # Sem normalizar, "Célia" em NFD virava "CéLia" no .title() (bug do notebook).
    nfc = "NF Maria Célia Souza.pdf"
    nfd = unicodedata.normalize("NFD", nfc)
    assert extrair_nome_do_arquivo(nfd) == extrair_nome_do_arquivo(nfc) == "Maria Célia Souza"


def test_limpar_nome_extraido():
    assert limpar_nome_extraido("  ANA   SOUZA , ") == "ANA SOUZA"
    assert limpar_nome_extraido("") is None
    assert limpar_nome_extraido(None) is None
