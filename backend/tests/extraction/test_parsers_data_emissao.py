"""Data de emissão da NF (texto vindo do OCR, frequentemente com ruído)."""

from datetime import date

import pytest

from app.extraction.parsers.data_emissao import (
    converter_data_br,
    extrair_data_emissao,
    normalizar_data_malformada,
)


def test_formato_correto_apos_o_rotulo():
    texto = "SECRETARIA DA FAZENDA Data e Hora de Emissao:\n08/03/2023 16:49:34"
    assert extrair_data_emissao(texto) == date(2023, 3, 8)


def test_data_sem_barras_e_reconstruida():
    assert extrair_data_emissao("Data e Hora de Emissao: 14112023") == date(2023, 11, 14)


def test_data_em_qualquer_lugar_quando_o_rotulo_nao_e_lido():
    assert extrair_data_emissao("COMPETENCIA 12/05/2024 (mes/ano)") == date(2024, 5, 12)


@pytest.mark.parametrize(
    "texto",
    [
        "Data e Hora de Emissao: 08/03/2019",  # ano fora da faixa válida
        "Data e Hora de Emissao: 31/02/2024",  # data impossível
        "nenhuma data aqui",
    ],
)
def test_sem_data_valida(texto):
    assert extrair_data_emissao(texto) is None


def test_normalizar_data_malformada():
    assert normalizar_data_malformada("14112023") == "14/11/2023"
    assert normalizar_data_malformada("123") is None


def test_converter_data_br():
    assert converter_data_br("25/04/2024") == date(2024, 4, 25)
