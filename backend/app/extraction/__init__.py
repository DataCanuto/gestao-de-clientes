"""Camada de extração: transforma um PDF em dados estruturados.

Fluxo (ver docs/architecture.md):

    bytes do PDF
      -> DocumentoPdf            (guarda os bytes e lê o texto sob demanda)
      -> DocumentTypeDetector    (NF? Planilha? Prestação?)
      -> ExtractorRegistry       (escolhe a estratégia certa para o tipo)
      -> DocumentExtractor       (aplica as regras do notebook)
      -> CorrecoesManuais        (preenche campos vazios com correções conhecidas)
      -> ResultadoExtracao       (objeto Python com os dados)

Esta camada não conhece FastAPI nem banco de dados: recebe bytes e devolve
objetos do domínio. É por isso que ela pode ser testada e reutilizada por um
script de linha de comando (scripts/verificar_paridade.py) sem subir o servidor.
"""

from app.extraction.factory import criar_pipeline
from app.extraction.pipeline import ExtractionPipeline

__all__ = ["ExtractionPipeline", "criar_pipeline"]
