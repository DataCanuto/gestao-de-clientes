"""Anotação entre parênteses: situação (enum) e corretor.

As expectativas vêm do cruzamento com o relatório Tabela Clientes
(ver docs/migration.md, seção "Situação").
"""

import pytest

from app.domain.enums import Situacao
from app.extraction.factory import ARQUIVO_SIGLAS_PADRAO
from app.extraction.parsers.anotacao import interpretar_anotacao
from app.extraction.siglas import TabelaSiglas

siglas = TabelaSiglas.carregar(ARQUIVO_SIGLAS_PADRAO)


@pytest.mark.parametrize(
    ("nome_arquivo", "situacao", "corretor"),
    [
        ("Planilha Comissão Ana Souza (VT Helena e Inês).pdf", Situacao.VALOR_TOTAL, "HELENA E INÊS"),
        ("Planilha Comissão Ana Souza (VT  Marcelo).pdf", Situacao.VALOR_TOTAL, "MARCELO"),
        ("Planilha Comissão Ana Souza (vf Rafael).pdf", Situacao.VALOR_FINAL, "RAFAEL"),
        ("Planilha Comissão Ana Souza (2 Inct. Inês).pdf", Situacao.VALOR_INCONTROVERSO, "INÊS"),
        ("Planilha Comissão Ana Souza (Acd Marcelo).pdf", Situacao.ACORDO, "MARCELO"),
        ("Planilha Comissão Ana Souza (Ac Beto).pdf", Situacao.ACORDO, "BETO"),
        # "V", "Vl" e "VI" abreviam "Valor": quem define a situação é a palavra seguinte.
        ("Planilha Comissão Ana Souza (Vl Inct. Viviane).pdf", Situacao.VALOR_INCONTROVERSO, "VIVIANE"),
        ("Planilha Comissão Ana Souza (V Inct Marcelo).pdf", Situacao.VALOR_INCONTROVERSO, "MARCELO"),
        ("Planilha Comissão Ana Souza (Vl Ictr Viviane).pdf", Situacao.VALOR_INCONTROVERSO, "VIVIANE"),
        ("Planilha Comissão Ana Souza (VI Juliana).pdf", Situacao.VALOR_INCONTROVERSO, "JULIANA"),
        ("Planilha Comissão Ana Souza (1 e 2 inctr Inês Helena).pdf", Situacao.VALOR_INCONTROVERSO, "INÊS HELENA"),
        ("Planilha Comissão Ana Souza (Inct.Helena.Inês).pdf", Situacao.VALOR_INCONTROVERSO, "HELENA INÊS"),
        ("Planilha Comissão Ana (Vl Inct. Marcelo)(2).pdf", Situacao.VALOR_INCONTROVERSO, "MARCELO"),
    ],
)
def test_planilha(nome_arquivo, situacao, corretor):
    anotacao = interpretar_anotacao(nome_arquivo, siglas)
    assert (anotacao.situacao, anotacao.corretor) == (situacao, corretor)


@pytest.mark.parametrize(
    ("nome_arquivo", "situacao"),
    [
        ("NF Ana Souza (CANCELADA POR DUPLICIDADE).pdf", Situacao.CANCELADO),
        ("NF Ana Souza (2 cancelada).pdf", Situacao.CANCELADO),
        ("NF Ana Souza (Vl Total).pdf", Situacao.VALOR_TOTAL),
        ("NF Ana Souza (V. Final).pdf", Situacao.VALOR_FINAL),
        ("NF Ana Souza (Incnt.).pdf", Situacao.VALOR_INCONTROVERSO),
        ("Prestação de Contas Ana Souza (acordo).pdf", Situacao.ACORDO),
        ("NF Ana Souza (2).pdf", None),
        ("NF Ana Souza (Rendimentos).pdf", None),
        ("NF Ana Souza.pdf", None),
    ],
)
def test_nf_e_prestacao(nome_arquivo, situacao):
    assert interpretar_anotacao(nome_arquivo, siglas).situacao is situacao


def test_sigla_fora_do_enum_nao_gera_situacao_mas_guarda_o_texto():
    anotacao = interpretar_anotacao("Planilha Comissão Ana Souza (VS Inês).pdf", siglas)
    assert anotacao.situacao is None
    assert anotacao.texto == "VS Inês"


def test_tabela_de_siglas_rejeita_situacao_invalida():
    with pytest.raises(ValueError):
        TabelaSiglas({"XX": "SITUACAO_INEXISTENTE"})
