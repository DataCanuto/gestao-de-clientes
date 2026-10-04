"""Extractors: uma estratégia de extração por tipo de documento (Strategy Pattern).

Para suportar um novo tipo (ex.: DOCX das planilhas de prestação de contas):
    1. crie uma classe que herda de DocumentExtractor;
    2. registre-a em app/extraction/factory.py.
Nenhum outro módulo precisa mudar.
"""

from app.extraction.extractors.base import DocumentExtractor, ExtracaoDocumento
from app.extraction.extractors.nota_fiscal_extractor import NotaFiscalExtractor
from app.extraction.extractors.planilha_extractor import PlanilhaComissaoExtractor
from app.extraction.extractors.prestacao_extractor import PrestacaoContasExtractor

__all__ = [
    "DocumentExtractor",
    "ExtracaoDocumento",
    "NotaFiscalExtractor",
    "PlanilhaComissaoExtractor",
    "PrestacaoContasExtractor",
]
