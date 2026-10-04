"""Leitura de TABELAS do PDF (Planilha Comissão).

Por que ler a tabela, e não o texto corrido? Na Planilha, o nome do cliente é a
célula logo abaixo do cabeçalho "Cliente". No texto corrido, as células viram
linhas soltas e um nome longo, quebrado em duas linhas dentro da célula, chega
cortado. O `find_tables()` do PyMuPDF usa as linhas desenhadas da tabela para
reconstruir as células, e a célula volta inteira.

Nos arquivos reais, essa leitura encontrou o nome em 149 de 151 planilhas. As
restantes usam a regra de texto como reserva (ver parsers/planilha.py).
"""

import pymupdf

from app.extraction.readers.base import Tabela

# O PyMuPDF sugere, no terminal, instalar um pacote opcional de layout na
# primeira chamada de find_tables(). Não usamos esse pacote; desligamos a sugestão.
pymupdf.no_recommend_layout()


class PdfTableReader:
    def ler_tabelas(self, conteudo: bytes) -> list[Tabela]:
        tabelas: list[Tabela] = []
        with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
            for pagina in documento:
                tabelas.extend(tabela.extract() for tabela in pagina.find_tables().tables)
        return tabelas
