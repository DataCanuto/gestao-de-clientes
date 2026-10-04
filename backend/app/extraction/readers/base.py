"""Contratos comuns dos readers.

Por que Protocol e não uma classe base (ABC)? Protocol é "tipagem estrutural":
qualquer objeto com o método certo serve, sem precisar herdar de nada. Nos
testes isso permite passar um leitor falso de 3 linhas no lugar do OCR real,
que é lento e exige o Tesseract instalado.
"""

from typing import Protocol

# Uma tabela é uma lista de linhas; cada linha, uma lista de células (texto ou vazia).
Tabela = list[list[str | None]]


class TextReader(Protocol):
    def ler_texto(self, conteudo: bytes) -> str:
        """Recebe os bytes de um PDF e devolve o texto de todas as páginas."""
        ...


class TableReader(Protocol):
    def ler_tabelas(self, conteudo: bytes) -> list[Tabela]:
        """Recebe os bytes de um PDF e devolve as tabelas encontradas (células com texto)."""
        ...
