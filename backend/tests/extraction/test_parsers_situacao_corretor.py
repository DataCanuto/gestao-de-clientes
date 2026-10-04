"""Regra ORIGINAL do notebook (célula 17), hoje usada como reserva da anotação.

Só entra em ação quando nenhuma sigla conhecida aparece, ex.: "(correção Rafael)".
"""

import pytest

from app.extraction.parsers.situacao_corretor import extrair_situacao_corretor


@pytest.mark.parametrize(
    ("nome_arquivo", "esperado"),
    [
        ("Planilha Comissão Ana Souza (VT Helena e Inês).pdf", ("VT", "HELENA E INÊS")),  # padrão 3
        ("Planilha Comissão Ana Souza (VT  Marcelo).pdf", ("VT", "MARCELO")),  # padrão 1
        ("Planilha Comissão Ana Souza (2 Inct. Inês).pdf", ("2 INCT.", "INÊS")),  # padrão 2
        ("Planilha Comissão Ana Souza (correção Rafael).pdf", ("CORREÇÃO", "RAFAEL")),  # padrão 4
        ("Planilha Comissão Ana Souza (VS Inês).pdf", ("VS", "INÊS")),
    ],
)
def test_padroes_do_notebook(nome_arquivo, esperado):
    assert extrair_situacao_corretor(nome_arquivo) == esperado


def test_limitacao_que_motivou_a_nova_regra():
    # O notebook assume que a situação é a 1ª palavra. Ver test_parsers_anotacao.py.
    assert extrair_situacao_corretor("Planilha Comissão Ana (Vl Inct. Viviane).pdf") == ("VL", "INCT. VIVIANE")


@pytest.mark.parametrize("nome_arquivo", ["Planilha Comissão Ana Souza.pdf", "Planilha Comissão Ana Souza (1).pdf"])
def test_sem_anotacao(nome_arquivo):
    assert extrair_situacao_corretor(nome_arquivo) == (None, None)
