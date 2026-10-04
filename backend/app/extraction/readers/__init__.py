"""Readers: os ÚNICOS módulos que conhecem as bibliotecas de PDF.

Se um dia o PyPDF2 for trocado pelo pypdf, ou o Tesseract por outro OCR, só
esta pasta muda. Os extractors dependem dos protocolos TextReader/TableReader,
não das bibliotecas.
"""

from app.extraction.readers.base import Tabela, TableReader, TextReader
from app.extraction.readers.cache import LeitorComCache
from app.extraction.readers.pdf_ocr_reader import PdfOcrReader
from app.extraction.readers.pdf_table_reader import PdfTableReader
from app.extraction.readers.pdf_text_reader import PdfTextReader

__all__ = ["LeitorComCache", "PdfOcrReader", "PdfTableReader", "PdfTextReader", "Tabela", "TableReader", "TextReader"]
