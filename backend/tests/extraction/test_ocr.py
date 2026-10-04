"""Integração com o Tesseract real. Lento: pule com `pytest -m "not ocr"`."""

from datetime import date

import pytest

from app.domain.enums import TipoDocumento
from app.extraction import criar_pipeline
from app.extraction.readers import PdfOcrReader, PdfTextReader
from tests.conftest import criar_pdf_escaneado

pytestmark = pytest.mark.ocr

LINHAS_NF = [
    "PREFEITURA MUNICIPAL",
    "Data e Hora de Emissao: 08/03/2023 16:49:34",
    "NOTA FISCAL DE SERVICOS ELETRONICA",
    "Cliente: ANA SOUZA Valor Acordo: R$ 1.000,00",
]


def test_pdf_escaneado_nao_tem_camada_de_texto():
    assert PdfTextReader().ler_texto(criar_pdf_escaneado(LINHAS_NF)).strip() == ""


def test_ocr_le_a_nota_fiscal(tesseract_cmd):
    texto = PdfOcrReader(tesseract_cmd).ler_texto(criar_pdf_escaneado(LINHAS_NF))
    assert "08/03/2023" in texto


def test_pipeline_com_ocr_real(tesseract_cmd):
    pipeline = criar_pipeline(tesseract_cmd=tesseract_cmd, arquivo_correcoes=None)
    resultado = pipeline.processar("digitalizacao.pdf", criar_pdf_escaneado(LINHAS_NF))

    assert resultado.tipo is TipoDocumento.NOTA_FISCAL  # detectado pelo conteúdo (OCR)
    assert resultado.dados.data_emissao == date(2023, 3, 8)
    assert resultado.nome_pelo_conteudo == "ANA SOUZA"
