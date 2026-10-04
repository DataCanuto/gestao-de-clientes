"""Exceções da camada de extração.

Exceções próprias deixam claro, para quem chama, O QUE deu errado sem depender
de mensagens de texto. O pipeline captura ExtracaoError por arquivo, de modo que
um PDF problemático vira um item com status ERRO, sem derrubar o lote inteiro.
"""


class ExtracaoError(Exception):
    """Base para erros de extração."""


class OcrIndisponivelError(ExtracaoError):
    """O executável do Tesseract não foi encontrado (configure TESSERACT_CMD)."""


class ExtractorNaoRegistradoError(ExtracaoError):
    """Não existe extractor registrado para o tipo de documento detectado."""
