"""Chave canônica do cliente: é ela que decide se duas grafias são a mesma pessoa."""

import pytest

from app.domain.nomes import eh_espolio, gerar_chave_cliente, similaridade_nomes


@pytest.mark.parametrize("grafia", ["João da Silva", "JOAO DA SILVA", "Joao  da Silva.", " joão DA silva "])
def test_grafias_do_mesmo_nome_geram_a_mesma_chave(grafia):
    assert gerar_chave_cliente(grafia) == "JOAO DA SILVA"


@pytest.mark.parametrize(
    "grafia",
    [
        "Otavio Ramos",  # antes do falecimento
        "Otavio Ramos Rep Beatriz Ramos - Espólio",  # nome de arquivo (regra legada)
        "ESPOLIO DE OTAVIO RAMOS",  # texto da Prestação
        "ESPÓLIO DE OTAVIO RAMOS - BEATRIZ RAMOS",  # célula da Planilha (representante após " - ")
        "ESPÓLIO OTAVIO RAMOS rep. Por BEATRIZ RAMOS",  # OCR da NF
        "Espélio OTAVIO RAMOS representado por sua inventariante BEATRIZ",  # erro de OCR
        "EPOLIO DE OTAVIO RAMOS",  # erro de digitação no documento
        "Esp. OTAVIO RAMOS",  # abreviação
    ],
)
def test_espolio_e_o_mesmo_cliente_e_o_representante_sai_da_chave(grafia):
    assert gerar_chave_cliente(grafia) == "OTAVIO RAMOS"


def test_representante_so_e_cortado_como_palavra_inteira():
    assert gerar_chave_cliente("Ana Reposo") == "ANA REPOSO"


@pytest.mark.parametrize("vazio", [None, "", "   "])
def test_nome_vazio_gera_chave_vazia(vazio):
    assert gerar_chave_cliente(vazio) == ""


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("Espólio de Ana Souza", True),
        ("Ana Souza - Espólio", True),
        ("Esp. ANA SOUZA", True),
        ("Ana Souza", False),
        ("Esperança Souza", False),  # começa com "Esp", mas não é espólio
        (None, False),
    ],
)
def test_eh_espolio(nome, esperado):
    assert eh_espolio(nome) is esperado


def test_similaridade():
    assert similaridade_nomes("João da Silva", "JOAO DA SILVA") == 1.0
    assert similaridade_nomes("Ana Souza", "Pedro Lima") < 0.5
    assert similaridade_nomes(None, "Ana") == 0.0
