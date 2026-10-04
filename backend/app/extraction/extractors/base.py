"""Contrato comum de todos os extractors.

Por que uma classe abstrata (ABC) aqui, se os readers usam Protocol? Porque
extractors formam uma FAMÍLIA dentro do projeto: todos declaram o atributo
`tipo` e são registrados no ExtractorRegistry. A herança explícita documenta
essa família, e o Python impede instanciar um extractor que esqueceu de
implementar `extrair`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.domain.entities import DadosExtraidos
from app.domain.enums import TipoDocumento
from app.extraction.documento_pdf import DocumentoPdf


@dataclass(slots=True)
class ExtracaoDocumento:
    """O que um extractor devolve: dados do tipo + nome lido do conteúdo + avisos."""

    dados: DadosExtraidos
    nome_pelo_conteudo: str | None
    avisos: list[str] = field(default_factory=list)


class DocumentExtractor(ABC):
    tipo: ClassVar[TipoDocumento]

    @abstractmethod
    def extrair(self, documento: DocumentoPdf) -> ExtracaoDocumento:
        """Aplica as regras do tipo e devolve os dados estruturados."""
