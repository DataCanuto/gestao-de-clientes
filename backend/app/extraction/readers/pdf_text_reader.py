"""Leitura da camada de texto do PDF (Prestação de Contas e Planilha).

Por que PyPDF2 e não PyMuPDF, que já é usado no OCR? As regex da Prestação
foram escritas no notebook sobre a saída do PyPDF2 (quebras de linha e espaços
específicos). Cada biblioteca monta o texto de um jeito, e trocar de biblioteca
poderia quebrar regras que hoje funcionam. O PyPDF2 foi descontinuado em favor
do `pypdf`, dos mesmos mantenedores; a migração está no roadmap e deve ser
validada com scripts/verificar_paridade.py.
"""

import io
import logging

from PyPDF2 import PdfReader

# O PyPDF2 emite avisos como "Multiple definitions in dictionary" para PDFs
# gerados por alguns programas. São inofensivos; silenciamos para não poluir o log.
logging.getLogger("PyPDF2").setLevel(logging.ERROR)


class PdfTextReader:
    def ler_texto(self, conteudo: bytes) -> str:
        leitor = PdfReader(io.BytesIO(conteudo))
        return "".join(pagina.extract_text() or "" for pagina in leitor.pages)
