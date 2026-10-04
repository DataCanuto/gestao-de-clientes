"""Fábrica do pipeline: o único lugar que sabe montar todas as peças.

Este é o "composition root" da extração. Os outros módulos recebem suas
dependências prontas e não precisam saber de onde vêm os arquivos JSON nem qual
é o caminho do Tesseract. Na Fase 2, o FastAPI chamará criar_pipeline() com
valores vindos das variáveis de ambiente (app/core/config.py).
"""

from pathlib import Path

from app.extraction.correcoes_manuais import CorrecoesManuais
from app.extraction.detector import DocumentTypeDetector
from app.extraction.extractors import (
    NotaFiscalExtractor,
    PlanilhaComissaoExtractor,
    PrestacaoContasExtractor,
)
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.readers import PdfOcrReader, PdfTableReader, PdfTextReader, TableReader, TextReader
from app.extraction.readers.pdf_ocr_reader import IDIOMA_OCR_PADRAO, ZOOM_OCR_PADRAO
from app.extraction.registry import ExtractorRegistry
from app.extraction.siglas import TabelaSiglas

DIRETORIO_DADOS = Path(__file__).parent / "data"
ARQUIVO_SIGLAS_PADRAO = DIRETORIO_DADOS / "situacao_siglas.json"
ARQUIVO_CORRECOES_PADRAO = DIRETORIO_DADOS / "correcoes_manuais.json"


def criar_pipeline(
    *,
    tesseract_cmd: str | None = None,
    idioma_ocr: str = IDIOMA_OCR_PADRAO,
    zoom_ocr: float = ZOOM_OCR_PADRAO,
    arquivo_siglas: Path = ARQUIVO_SIGLAS_PADRAO,
    arquivo_correcoes: Path | None = ARQUIVO_CORRECOES_PADRAO,
    leitor_texto: TextReader | None = None,
    leitor_ocr: TextReader | None = None,
    leitor_tabelas: TableReader | None = None,
) -> ExtractionPipeline:
    """Monta o pipeline padrão. Os leitores podem ser substituídos (testes, --sem-ocr)."""
    siglas = TabelaSiglas.carregar(arquivo_siglas)
    registry = ExtractorRegistry(
        [
            NotaFiscalExtractor(siglas),
            PlanilhaComissaoExtractor(siglas),
            PrestacaoContasExtractor(siglas),
        ]
    )
    return ExtractionPipeline(
        detector=DocumentTypeDetector(),
        registry=registry,
        correcoes=CorrecoesManuais.carregar(arquivo_correcoes),
        leitor_texto=leitor_texto or PdfTextReader(),
        leitor_ocr=leitor_ocr or PdfOcrReader(tesseract_cmd, idioma_ocr, zoom_ocr),
        leitor_tabelas=leitor_tabelas or PdfTableReader(),
    )
