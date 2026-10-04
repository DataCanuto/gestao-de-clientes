"""Mesclagem de PDFs: um arquivo por cliente (Prestação + Planilha + NF).

No notebook (célula 42), com PyPDF2.PdfMerger. Aqui, com PyMuPDF, que o
projeto já usa para o OCR e as tabelas: `insert_pdf` copia as páginas de um
documento para outro, sem converter para imagem (a qualidade é a mesma dos
originais, e as NFs escaneadas não aumentam de tamanho).

Por que não o PyPDF2? Ele está descontinuado (ver extraction/readers/
pdf_text_reader.py); o código novo não deve depender dele.
"""

from collections.abc import Iterable
from pathlib import Path

import pymupdf


def mesclar_pdfs(arquivos: Iterable[Path]) -> bytes:
    """Junta os PDFs na ordem recebida e devolve o conteúdo do PDF mesclado."""
    destino = pymupdf.open()
    try:
        for caminho in arquivos:
            if not Path(caminho).is_file():  # o PyMuPDF lança uma exceção própria; esta é a do Python
                raise FileNotFoundError(caminho)
            with pymupdf.open(caminho) as origem:
                destino.insert_pdf(origem)
        # garbage=3 remove objetos duplicados (fontes repetidas); deflate comprime.
        return destino.tobytes(garbage=3, deflate=True)
    finally:
        destino.close()
