"""DocumentoPdf: um PDF em memória, com leitura sob demanda.

Problema que resolve: o detector de tipo e o extractor podem precisar do mesmo
texto. Sem cache, o PDF seria lido duas vezes. O notebook lia cada Prestação
duas vezes, e no caso do OCR (~1 s por NF) isso dobraria o tempo.

Com @cached_property, cada representação (texto, OCR, tabelas) só é lida no
primeiro acesso e depois fica guardada no objeto. Quem não precisa de OCR nunca
paga por ele.
"""

from functools import cached_property

from app.extraction.readers.base import Tabela, TableReader, TextReader


class DocumentoPdf:
    def __init__(
        self,
        nome_arquivo: str,
        conteudo: bytes,
        leitor_texto: TextReader,
        leitor_ocr: TextReader,
        leitor_tabelas: TableReader,
    ) -> None:
        self.nome_arquivo = nome_arquivo
        self.conteudo = conteudo
        self._leitor_texto = leitor_texto
        self._leitor_ocr = leitor_ocr
        self._leitor_tabelas = leitor_tabelas

    @cached_property
    def texto(self) -> str:
        """Camada de texto do PDF (rápido; vazio em PDFs escaneados)."""
        return self._leitor_texto.ler_texto(self.conteudo)

    @cached_property
    def texto_ocr(self) -> str:
        """Texto obtido por OCR (lento; necessário para a Nota Fiscal)."""
        return self._leitor_ocr.ler_texto(self.conteudo)

    @cached_property
    def tabelas(self) -> list[Tabela]:
        """Tabelas desenhadas no PDF (usadas na Planilha Comissão)."""
        return self._leitor_tabelas.ler_tabelas(self.conteudo)
