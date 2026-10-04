"""Registro de extractors: dado um TipoDocumento, devolve a estratégia certa.

Por que não um if/elif no pipeline? Com if/elif, adicionar um tipo exige mexer
no pipeline, e o pipeline passa a conhecer todos os extractors. Com o registro,
o pipeline só pergunta "quem trata este tipo?". Novos tipos são adicionados na
fábrica (factory.py) sem tocar no pipeline (princípio aberto/fechado).
"""

from collections.abc import Iterable

from app.domain.enums import TipoDocumento
from app.extraction.exceptions import ExtractorNaoRegistradoError
from app.extraction.extractors.base import DocumentExtractor


class ExtractorRegistry:
    def __init__(self, extractors: Iterable[DocumentExtractor] = ()) -> None:
        self._extractors: dict[TipoDocumento, DocumentExtractor] = {}
        for extractor in extractors:
            self.registrar(extractor)

    def registrar(self, extractor: DocumentExtractor) -> None:
        self._extractors[extractor.tipo] = extractor

    def obter(self, tipo: TipoDocumento) -> DocumentExtractor:
        try:
            return self._extractors[tipo]
        except KeyError:
            raise ExtractorNaoRegistradoError(f"Nenhum extractor registrado para {tipo}.") from None

    @property
    def tipos_suportados(self) -> list[TipoDocumento]:
        return list(self._extractors)
