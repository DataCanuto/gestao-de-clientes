"""Leitura por OCR de PDFs escaneados (Nota Fiscal).

Migração de `extrair_texto_pdf_ocr` (célula 8). A NF é uma imagem dentro do
PDF, sem camada de texto, então cada página é:
    1. renderizada como imagem (PyMuPDF), com zoom 2x para melhorar o OCR;
    2. convertida para imagem PIL;
    3. lida pelo Tesseract.

Correções em relação ao notebook:
- Se o Tesseract falhasse numa página, a variável `texto_pagina` ficava
  indefinida (NameError) ou repetia o texto da página anterior. Agora a página
  com falha é registrada no log e contribui com texto vazio.
- Se o Tesseract não estiver instalado, o notebook engolia o erro e seguia sem
  datas. Agora é lançado OcrIndisponivelError, e o arquivo aparece com status
  ERRO e uma mensagem clara.
- O comentário do notebook dizia "tenta em português", mas o código usava 'eng'
  (só esse idioma está instalado). O idioma agora é configurável; o padrão
  continua 'eng' para preservar o comportamento.
"""

import logging

import pymupdf  # o notebook usava o nome antigo do pacote: `import fitz`
import pytesseract
from PIL import Image

from app.extraction.exceptions import OcrIndisponivelError

logger = logging.getLogger(__name__)

IDIOMA_OCR_PADRAO = "eng"
ZOOM_OCR_PADRAO = 2.0


def versao_do_tesseract() -> str | None:
    """Versão do Tesseract configurado, ou None se ele não estiver acessível (usado no /saude)."""
    try:
        return str(pytesseract.get_tesseract_version())
    except (pytesseract.TesseractNotFoundError, OSError):
        return None


class PdfOcrReader:
    def __init__(
        self,
        tesseract_cmd: str | None = None,
        idioma: str = IDIOMA_OCR_PADRAO,
        zoom: float = ZOOM_OCR_PADRAO,
    ) -> None:
        if tesseract_cmd:
            # Configuração global do pytesseract: é assim que a biblioteca funciona.
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._idioma = idioma
        self._zoom = zoom

    def ler_texto(self, conteudo: bytes) -> str:
        textos: list[str] = []
        with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
            for numero, pagina in enumerate(documento, start=1):
                textos.append(self._ocr_da_pagina(self._renderizar(pagina), numero))
        return "".join(textos)

    def _renderizar(self, pagina: pymupdf.Page) -> Image.Image:
        pixmap = pagina.get_pixmap(matrix=pymupdf.Matrix(self._zoom, self._zoom))
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    def _ocr_da_pagina(self, imagem: Image.Image, numero_pagina: int) -> str:
        try:
            return pytesseract.image_to_string(imagem, lang=self._idioma)
        except pytesseract.TesseractNotFoundError as erro:
            raise OcrIndisponivelError(
                "Tesseract não encontrado. Instale-o ou configure TESSERACT_CMD."
            ) from erro
        except pytesseract.TesseractError as erro:
            logger.warning("OCR falhou na página %s: %s", numero_pagina, erro)
            return ""
