"""Ferramentas compartilhadas pelos testes.

Todos os dados aqui são SINTÉTICOS: os PDFs reais contêm informações de clientes
e não entram no repositório. O comportamento com os arquivos reais é verificado
por scripts/verificar_paridade.py.
"""

import os
import shutil
from pathlib import Path

import pymupdf
import pytest

from app.domain.entities import DadosExtraidos, ResultadoExtracao
from app.domain.enums import StatusExtracao, TipoDocumento

CABECALHO_PDF_FALSO = b"%PDF-1.4 falso\n"


class LeitorFalso:
    """Dublê de TextReader: devolve o texto cadastrado para cada conteúdo.

    Permite testar extractors e pipeline sem PDFs reais e sem o Tesseract.
    """

    def __init__(self, textos: dict[bytes, str] | None = None) -> None:
        self.textos = textos or {}
        self.chamadas = 0

    def ler_texto(self, conteudo: bytes) -> str:
        self.chamadas += 1
        return self.textos.get(conteudo, "")


class LeitorQueFalha:
    """Lança exceção para os conteúdos informados (ou para todos, se nenhum for informado)."""

    def __init__(self, conteudos_ruins: set[bytes] | None = None, textos: dict[bytes, str] | None = None) -> None:
        self._conteudos_ruins = conteudos_ruins
        self._textos = textos or {}

    def ler_texto(self, conteudo: bytes) -> str:
        if self._conteudos_ruins is None or conteudo in self._conteudos_ruins:
            raise RuntimeError("PDF corrompido")
        return self._textos.get(conteudo, "")


class LeitorTabelasFalso:
    """Dublê de TableReader: devolve as tabelas cadastradas para cada conteúdo."""

    def __init__(self, tabelas: dict[bytes, list] | None = None) -> None:
        self.tabelas = tabelas or {}

    def ler_tabelas(self, conteudo: bytes) -> list:
        return self.tabelas.get(conteudo, [])


def pdf_falso(identificador: str) -> bytes:
    """Bytes que passam na checagem de assinatura %PDF e servem de chave para o LeitorFalso."""
    return CABECALHO_PDF_FALSO + identificador.encode()


def criar_pdf_com_texto(linhas: list[str]) -> bytes:
    """Gera um PDF real, com camada de texto, usando PyMuPDF."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    for posicao, linha in enumerate(linhas):
        pagina.insert_text((72, 72 + 16 * posicao), linha, fontname="helv", fontsize=11)
    conteudo = documento.tobytes()
    documento.close()
    return conteudo


def criar_pdf_com_tabela(celulas: list[list[str]]) -> bytes:
    """Gera um PDF com uma tabela desenhada (linhas e colunas), como a Planilha Comissão."""
    documento = pymupdf.open()
    pagina = documento.new_page()
    largura, altura, x0, y0 = 160, 24, 50, 80
    for i, linha in enumerate(celulas):
        for j, texto in enumerate(linha):
            retangulo = pymupdf.Rect(x0 + j * largura, y0 + i * altura, x0 + (j + 1) * largura, y0 + (i + 1) * altura)
            pagina.draw_rect(retangulo, color=(0, 0, 0), width=0.8)
            pagina.insert_text((retangulo.x0 + 4, retangulo.y1 - 7), texto, fontname="helv", fontsize=10)
    conteudo = documento.tobytes()
    documento.close()
    return conteudo


def criar_pdf_escaneado(linhas: list[str]) -> bytes:
    """Gera um PDF SEM camada de texto (só imagem), como as Notas Fiscais."""
    origem = pymupdf.open(stream=criar_pdf_com_texto(linhas), filetype="pdf")
    imagem = origem[0].get_pixmap(dpi=200)
    destino = pymupdf.open()
    pagina = destino.new_page(width=origem[0].rect.width, height=origem[0].rect.height)
    pagina.insert_image(pagina.rect, pixmap=imagem)
    conteudo = destino.tobytes()
    origem.close()
    destino.close()
    return conteudo


def resultado(
    nome_arquivo: str,
    tipo: TipoDocumento,
    dados: DadosExtraidos,
    nome_pelo_arquivo: str | None = None,
    nome_pelo_conteudo: str | None = None,
) -> ResultadoExtracao:
    """Atalho para montar um ResultadoExtracao de sucesso nos testes de consolidação."""
    return ResultadoExtracao(
        nome_arquivo=nome_arquivo,
        status=StatusExtracao.SUCESSO,
        tipo=tipo,
        nome_pelo_arquivo=nome_pelo_arquivo,
        nome_pelo_conteudo=nome_pelo_conteudo,
        dados=dados,
    )


def localizar_tesseract() -> str | None:
    candidatos = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ]
    return next((c for c in candidatos if c and Path(c).exists()), None)


@pytest.fixture
def tesseract_cmd() -> str:
    caminho = localizar_tesseract()
    if caminho is None:
        pytest.skip("Tesseract não instalado")
    return caminho
