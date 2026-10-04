"""Identificação do tipo: pelo nome do arquivo (legado) ou pelo conteúdo (novo)."""

import unicodedata

import pytest

from app.domain.enums import TipoDocumento
from app.extraction.detector import DocumentTypeDetector
from app.extraction.documento_pdf import DocumentoPdf
from tests.conftest import LeitorFalso, LeitorQueFalha, LeitorTabelasFalso

detector = DocumentTypeDetector()


@pytest.mark.parametrize(
    ("nome_arquivo", "tipo"),
    [
        ("NF Ana Souza.pdf", TipoDocumento.NOTA_FISCAL),
        ("nf ana souza.pdf", TipoDocumento.NOTA_FISCAL),
        ("Planilha Comissão Ana Souza (VT Helena).pdf", TipoDocumento.PLANILHA_COMISSAO),
        ("Prestação de Contas Ana Souza.pdf", TipoDocumento.PRESTACAO_CONTAS),
        (unicodedata.normalize("NFD", "Prestação de Contas Ana.pdf"), TipoDocumento.PRESTACAO_CONTAS),
        ("scan_0042.pdf", None),
        ("Nfe Ana.pdf", None),  # o prefixo exige "nf " com espaço
    ],
)
def test_detectar_pelo_nome(nome_arquivo, tipo):
    assert detector.detectar_pelo_nome(nome_arquivo) is tipo


def _documento(nome, texto="", texto_ocr=""):
    return DocumentoPdf(nome, b"x", LeitorFalso({b"x": texto}), LeitorFalso({b"x": texto_ocr}), LeitorTabelasFalso())


def test_pelo_nome_nao_le_o_conteudo():
    documento = DocumentoPdf("NF Ana.pdf", b"x", LeitorQueFalha(), LeitorQueFalha(), LeitorTabelasFalso())
    deteccao = detector.detectar(documento)
    assert deteccao.tipo is TipoDocumento.NOTA_FISCAL
    assert not deteccao.pelo_conteudo


@pytest.mark.parametrize(
    ("texto", "texto_ocr", "tipo"),
    [
        ("À ANA SOUZA\nReferente: Prestação de Contas\nProcesso: 1", "", TipoDocumento.PRESTACAO_CONTAS),
        ("Planilha Controle de Pagamentos _ Plano Verão", "", TipoDocumento.PLANILHA_COMISSAO),
        ("", "NOTA FISCAL DE SERVICOS ELETRONICA", TipoDocumento.NOTA_FISCAL),
    ],
)
def test_detectar_pelo_conteudo_quando_o_nome_foge_do_padrao(texto, texto_ocr, tipo):
    deteccao = detector.detectar(_documento("scan_0042.pdf", texto, texto_ocr))
    assert deteccao.tipo is tipo
    assert deteccao.pelo_conteudo


def test_ocr_so_roda_quando_nao_ha_camada_de_texto():
    ocr = LeitorFalso({b"x": "NOTA FISCAL"})
    documento = DocumentoPdf("scan.pdf", b"x", LeitorFalso({b"x": "um documento qualquer com texto"}), ocr, LeitorTabelasFalso())
    assert detector.detectar(documento) is None
    assert ocr.chamadas == 0


def test_desativar_deteccao_pelo_conteudo():
    documento = _documento("scan.pdf", "Referente: Prestação de Contas")
    assert DocumentTypeDetector(usar_conteudo=False).detectar(documento) is None
