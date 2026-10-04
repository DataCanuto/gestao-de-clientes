"""Pipeline completo: bytes -> ResultadoExtracao."""

import json
from datetime import date

import pytest

from app.domain.entities import DadosPlanilhaComissao, DadosPrestacaoContas
from app.domain.enums import OrigemNome, Situacao, StatusExtracao, TipoDocumento
from app.extraction import criar_pipeline
from app.extraction.readers import PdfTableReader, PdfTextReader
from tests.conftest import (
    LeitorFalso,
    LeitorQueFalha,
    LeitorTabelasFalso,
    criar_pdf_com_tabela,
    criar_pdf_com_texto,
    pdf_falso,
)

NF_ANA = pdf_falso("nf-ana")
PLANILHA_ANA = pdf_falso("planilha-ana")
PRESTACAO_ANA = pdf_falso("prestacao-ana")
DESCONHECIDO = pdf_falso("desconhecido")


@pytest.fixture
def pipeline(tmp_path):
    textos = LeitorFalso(
        {
            PRESTACAO_ANA: "À\n ANA SOUZA\nReferente: Prestação de Contas\nProcesso: 0001001-37.2014.8.05.0001",
            DESCONHECIDO: "um contrato qualquer, sem marcadores conhecidos",
        }
    )
    ocr = LeitorFalso({NF_ANA: "Data e Hora de Emissao: 08/03/2023\nCliente: ANA SOUZA Valor Acordo: R$ 1,00"})
    tabelas = LeitorTabelasFalso({PLANILHA_ANA: [[["Cliente", "Valor"], ["Ana Souza", "1.000,00"]]]})
    correcoes = tmp_path / "correcoes.json"
    correcoes.write_text(json.dumps({"NF Pedro Lima.pdf": {"data_emissao": "25/04/2024"}}), encoding="utf-8")
    return criar_pipeline(leitor_texto=textos, leitor_ocr=ocr, leitor_tabelas=tabelas, arquivo_correcoes=correcoes)


def test_nota_fiscal(pipeline):
    resultado = pipeline.processar("NF Ana Souza (Incnt.).pdf", NF_ANA)

    assert resultado.status is StatusExtracao.SUCESSO
    assert resultado.tipo is TipoDocumento.NOTA_FISCAL
    assert resultado.dados.data_emissao == date(2023, 3, 8)
    assert resultado.dados.situacao is Situacao.VALOR_INCONTROVERSO
    assert resultado.nome_pelo_conteudo == "ANA SOUZA"
    assert resultado.nome_pelo_arquivo == "Ana Souza"
    assert resultado.origem_nome is OrigemNome.CONTEUDO
    assert resultado.avisos == []


def test_planilha_nome_pela_tabela_e_situacao_pela_anotacao(pipeline):
    resultado = pipeline.processar("Planilha Comissão Ana Souza (Vl Inct. Helena).pdf", PLANILHA_ANA)
    assert resultado.nome_pelo_conteudo == "Ana Souza"
    assert resultado.dados == DadosPlanilhaComissao(
        corretor="HELENA", situacao=Situacao.VALOR_INCONTROVERSO, anotacao="Vl Inct. Helena"
    )


def test_planilha_com_sigla_desconhecida_fica_verificar(pipeline):
    resultado = pipeline.processar("Planilha Comissão Ana Souza (correção Rafael).pdf", PLANILHA_ANA)
    assert (resultado.dados.situacao, resultado.dados.corretor) == (Situacao.VERIFICAR, "RAFAEL")
    assert any("Sigla 'CORREÇÃO'" in aviso for aviso in resultado.avisos)
    assert resultado.campos_a_verificar == ["situacao"]


def test_planilha_sem_anotacao_fica_verificar_sem_corretor(pipeline):
    resultado = pipeline.processar("Planilha Comissão Ana Souza.pdf", PLANILHA_ANA)
    assert (resultado.dados.situacao, resultado.dados.corretor) == (Situacao.VERIFICAR, None)
    assert resultado.campos_a_verificar == ["situacao", "corretor"]


def test_prestacao(pipeline):
    resultado = pipeline.processar("Prestação de Contas Ana Souza (VT Juliana).pdf", PRESTACAO_ANA)
    assert resultado.dados == DadosPrestacaoContas("ANA SOUZA", "0001001-37.2014.8.05.0001", Situacao.VALOR_TOTAL)


def test_caminho_de_pasta_e_reduzido_ao_nome_do_arquivo(pipeline):
    resultado = pipeline.processar("lote/2026/NF Ana Souza.pdf", NF_ANA)
    assert resultado.nome_arquivo == "NF Ana Souza.pdf"


def test_correcao_manual_preenche_campo_nao_extraido(pipeline):
    resultado = pipeline.processar("NF Pedro Lima.pdf", pdf_falso("sem-ocr"))
    assert resultado.dados.data_emissao == date(2024, 4, 25)
    assert resultado.campos_corrigidos == ["data_emissao"]


def test_nome_divergente_gera_aviso(pipeline):
    resultado = pipeline.processar("NF Carlos Pereira.pdf", NF_ANA)
    assert any("difere do nome do arquivo" in aviso for aviso in resultado.avisos)


def test_tipo_detectado_pelo_conteudo_nao_usa_o_nome_do_arquivo(pipeline):
    resultado = pipeline.processar("scan_0042.pdf", PRESTACAO_ANA)
    assert resultado.tipo is TipoDocumento.PRESTACAO_CONTAS
    assert resultado.nome_pelo_arquivo is None
    assert resultado.nome_cliente == "ANA SOUZA"
    assert any("pelo conteúdo" in aviso for aviso in resultado.avisos)


def test_arquivo_que_nao_e_pdf(pipeline):
    resultado = pipeline.processar("NF Ana.pdf", b"PK\x03\x04 planilha excel")
    assert resultado.status is StatusExtracao.TIPO_DESCONHECIDO
    assert resultado.avisos == ["O arquivo não é um PDF."]


def test_tipo_desconhecido(pipeline):
    assert pipeline.processar("contrato.pdf", DESCONHECIDO).status is StatusExtracao.TIPO_DESCONHECIDO


def test_erro_em_um_arquivo_nao_derruba_os_demais():
    corrompido, bom = pdf_falso("corrompido"), pdf_falso("bom")
    leitor = LeitorQueFalha(conteudos_ruins={corrompido}, textos={bom: "À\nANA SOUZA\nProcesso: 123-45"})
    pipeline = criar_pipeline(
        leitor_texto=leitor, leitor_ocr=LeitorFalso(), leitor_tabelas=LeitorTabelasFalso(), arquivo_correcoes=None
    )

    com_erro = pipeline.processar("Prestação de Contas Ana.pdf", corrompido)
    seguinte = pipeline.processar("Prestação de Contas Ana (2).pdf", bom)

    assert com_erro.status is StatusExtracao.ERRO
    assert com_erro.erro == "RuntimeError: PDF corrompido"
    assert seguinte.status is StatusExtracao.SUCESSO


def test_pdf_real_com_camada_de_texto():
    """Integração com o PyPDF2 de verdade (sem OCR)."""
    conteudo = criar_pdf_com_texto(
        ["Salvador, 16 de fevereiro de 2023.", "À", "ANA SOUZA", "Referente: Prestação de Contas", "Processo: 0001001-37.2014.8.05.0001"]
    )
    assert "ANA SOUZA" in PdfTextReader().ler_texto(conteudo)

    pipeline = criar_pipeline(leitor_ocr=LeitorFalso(), arquivo_correcoes=None)
    resultado = pipeline.processar("documento_sem_padrao.pdf", conteudo)
    assert resultado.tipo is TipoDocumento.PRESTACAO_CONTAS
    assert resultado.dados == DadosPrestacaoContas("ANA SOUZA", "0001001-37.2014.8.05.0001")


def test_pdf_real_com_tabela():
    """Integração com o find_tables() do PyMuPDF: nome na célula abaixo de "Cliente"."""
    conteudo = criar_pdf_com_tabela([["Cliente", "Valor Atualizado R$"], ["ANA SOUZA", "298.924,91"]])
    assert PdfTableReader().ler_tabelas(conteudo)[0][1][0] == "ANA SOUZA"

    pipeline = criar_pipeline(leitor_ocr=LeitorFalso(), arquivo_correcoes=None)
    resultado = pipeline.processar("Planilha Comissão Ana (VT Helena).pdf", conteudo)
    assert resultado.nome_pelo_conteudo == "ANA SOUZA"
    assert resultado.dados.situacao is Situacao.VALOR_TOTAL
