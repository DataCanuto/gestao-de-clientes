"""Revisão de um arquivo do lote antes de salvar (domain/revisao.py)."""

from datetime import date

import pytest

from app.domain.consolidacao import ConsolidadorFichas
from app.domain.entities import (
    DadosNotaFiscal,
    DadosPlanilhaComissao,
    DadosPrestacaoContas,
    ResultadoExtracao,
)
from app.domain.enums import Situacao, StatusExtracao, TipoDocumento
from app.domain.revisao import RevisaoDeItem, RevisaoInvalidaError, revisar
from tests.conftest import resultado

NF_SEM_DATA = resultado(
    "NF Ana Souza.pdf", TipoDocumento.NOTA_FISCAL, DadosNotaFiscal(None), nome_pelo_arquivo="Ana Souza", nome_pelo_conteudo="ANA SOUZA"
)


def test_campo_preenchido_a_mao_fica_marcado_como_corrigido():
    revisado = revisar(NF_SEM_DATA, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUZA", data_emissao=date(2023, 3, 8)))

    assert revisado.dados == DadosNotaFiscal(date(2023, 3, 8))
    assert revisado.campos_corrigidos == ["data_emissao"]
    assert revisado.campos_a_verificar == []


def test_nome_informado_vira_o_nome_do_cliente():
    ilegivel = resultado("NF 123.pdf", TipoDocumento.NOTA_FISCAL, DadosNotaFiscal(date(2023, 1, 1)))
    revisado = revisar(ilegivel, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "  Bruno   Lima ", data_emissao=date(2023, 1, 1)))

    assert revisado.nome_pelo_conteudo == "Bruno Lima"
    assert revisado.nome_cliente == "Bruno Lima"
    assert revisado.campos_corrigidos == ["nome_cliente"]


def test_sem_mudancas_nada_e_marcado():
    revisado = revisar(NF_SEM_DATA, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUZA"))
    assert revisado.campos_corrigidos == []


def test_campo_de_outro_tipo_e_recusado():
    with pytest.raises(RevisaoInvalidaError, match="corretor"):
        revisar(NF_SEM_DATA, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUZA", corretor="HELENA"))


def test_tipo_nao_reconhecido_recebe_o_tipo_da_pessoa():
    desconhecido = ResultadoExtracao("scan001.pdf", StatusExtracao.TIPO_DESCONHECIDO, avisos=["Tipo não identificado."])
    revisao = RevisaoDeItem(
        TipoDocumento.PRESTACAO_CONTAS, "Ana Souza", nome_encontrado="ANA SOUZA", numero_processo="0001-00.2020.8.05.0001"
    )
    revisado = revisar(desconhecido, revisao)

    assert (revisado.status, revisado.tipo) == (StatusExtracao.SUCESSO, TipoDocumento.PRESTACAO_CONTAS)
    assert revisado.dados == DadosPrestacaoContas("ANA SOUZA", "0001-00.2020.8.05.0001")
    assert set(revisado.campos_corrigidos) == {"tipo", "nome_cliente", "nome_encontrado", "numero_processo"}


def test_planilha_preserva_a_anotacao_e_padroniza_o_corretor():
    planilha = resultado(
        "Planilha Comissão Ana (VS).pdf",
        TipoDocumento.PLANILHA_COMISSAO,
        DadosPlanilhaComissao(None, Situacao.VERIFICAR, anotacao="VS"),
        nome_pelo_conteudo="ANA SOUZA",
    )
    revisado = revisar(
        planilha, RevisaoDeItem(TipoDocumento.PLANILHA_COMISSAO, "ANA SOUZA", situacao=Situacao.VALOR_TOTAL, corretor=" helena ")
    )

    assert revisado.dados == DadosPlanilhaComissao("HELENA", Situacao.VALOR_TOTAL, anotacao="VS")
    assert revisado.campos_corrigidos == ["corretor", "situacao"]


def test_correcoes_se_acumulam_entre_revisoes():
    primeira = revisar(NF_SEM_DATA, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUZA", data_emissao=date(2023, 3, 8)))
    segunda = revisar(
        primeira, RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUZA", data_emissao=date(2023, 3, 8), situacao=Situacao.CANCELADO)
    )
    assert segunda.campos_corrigidos == ["data_emissao", "situacao"]


def test_nome_digitado_numa_nf_nao_e_reconciliado_como_ocr():
    """'ANA SOUSA' digitado à mão é uma decisão da pessoa, e não um erro de leitura a corrigir."""
    prestacao = resultado(
        "Prestação de Contas Ana Souza.pdf",
        TipoDocumento.PRESTACAO_CONTAS,
        DadosPrestacaoContas("ANA SOUZA", "1"),
        nome_pelo_conteudo="ANA SOUZA",
    )
    nf = revisar(
        resultado("NF.pdf", TipoDocumento.NOTA_FISCAL, DadosNotaFiscal(date(2023, 1, 1))),
        RevisaoDeItem(TipoDocumento.NOTA_FISCAL, "ANA SOUSA", data_emissao=date(2023, 1, 1)),
    )

    consolidacao = ConsolidadorFichas().consolidar([prestacao, nf])

    assert {f.chave for f in consolidacao.fichas} == {"ANA SOUZA", "ANA SOUSA"}
    assert consolidacao.reconciliacoes_ocr == []
