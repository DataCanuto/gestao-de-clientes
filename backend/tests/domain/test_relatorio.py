"""Números do dashboard (migração das células 35 e 37 do notebook)."""

from datetime import date

from app.domain.entities import DadosNotaFiscal, DadosPlanilhaComissao, DadosPrestacaoContas, FichaCliente
from app.domain.enums import Situacao, TipoDocumento
from app.domain.relatorio import clientes_com_documentos_faltantes, gerar_resumo
from tests.conftest import resultado

NF = TipoDocumento.NOTA_FISCAL
PL = TipoDocumento.PLANILHA_COMISSAO
PR = TipoDocumento.PRESTACAO_CONTAS


def _nf(arquivo, data=date(2024, 1, 1)):
    return resultado(arquivo, NF, DadosNotaFiscal(data), nome_pelo_conteudo="X")


def _planilha(arquivo, situacao):
    return resultado(arquivo, PL, DadosPlanilhaComissao("HELENA", situacao), nome_pelo_conteudo="X")


def _prestacao(arquivo):
    return resultado(arquivo, PR, DadosPrestacaoContas("X", "123"), nome_pelo_conteudo="X")


FICHAS = [
    FichaCliente(
        nome="Ana",
        chave="ANA",
        documentos=[
            _nf("NF Ana.pdf"),
            _nf("NF Ana (2).pdf", data=None),  # a verificar
            _planilha("Planilha Ana.pdf", Situacao.VALOR_TOTAL),
            _prestacao("Prestação Ana.pdf"),
        ],
    ),
    FichaCliente(nome="Bruno", chave="BRUNO", documentos=[_nf("NF Bruno.pdf")]),
    FichaCliente(
        nome="Carla",
        chave="CARLA",
        documentos=[_nf("NF Carla.pdf"), _planilha("Planilha Carla.pdf", Situacao.VERIFICAR)],  # a verificar
    ),
]


def test_resumo():
    resumo = gerar_resumo(FICHAS)
    assert resumo.total_clientes == 3
    assert resumo.total_documentos == {NF: 4, PL: 2, PR: 1}
    assert resumo.clientes_sem_documento == {NF: 0, PL: 1, PR: 2}
    assert resumo.clientes_com_varios_documentos == {NF: 1, PL: 0, PR: 0}
    assert resumo.clientes_com_documentos_faltantes == 2
    assert resumo.documentos_a_verificar == 2
    assert resumo.planilhas_por_situacao == {Situacao.VALOR_TOTAL: 1, Situacao.VERIFICAR: 1}


def test_relatorio_de_faltantes_ordena_por_quantidade_de_faltantes():
    assert [f.nome for f in clientes_com_documentos_faltantes(FICHAS)] == ["Bruno", "Carla"]


def test_resumo_vazio():
    assert gerar_resumo([]).total_clientes == 0
