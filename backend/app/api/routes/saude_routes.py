"""GET /api/v1/saude: a API está no ar? O OCR está disponível?

Usado pelo frontend (e, no futuro, pelo Docker/serviço de nuvem) para saber se
o backend está pronto antes de enviar arquivos.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.dependencies import PipelineDep
from app.extraction.readers.pdf_ocr_reader import versao_do_tesseract

router = APIRouter(tags=["saúde"])


class SaudeSchema(BaseModel):
    status: str
    ocr_disponivel: bool
    versao_tesseract: str | None


@router.get("/saude", response_model=SaudeSchema, summary="Verifica se a API e o OCR estão prontos")
def verificar_saude(_: PipelineDep) -> SaudeSchema:
    # A dependência do pipeline garante que o caminho do Tesseract já foi configurado.
    versao = versao_do_tesseract()
    return SaudeSchema(status="ok", ocr_disponivel=versao is not None, versao_tesseract=versao)
