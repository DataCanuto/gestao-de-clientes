"""ExtractionPipeline: orquestra a transformação de UM arquivo em ResultadoExtracao.

    bytes -> DocumentoPdf -> detectar tipo -> extractor -> correções -> verificações

O pipeline não sabe COMO extrair uma NF nem COMO ler um PDF: ele coordena
componentes recebidos no construtor (injeção de dependências). Assim cada peça
pode ser trocada ou simulada nos testes de forma isolada.
"""

import logging
import re

from app.domain.entities import ResultadoExtracao
from app.domain.enums import StatusExtracao
from app.domain.nomes import normalizar_unicode, similaridade_nomes
from app.extraction.correcoes_manuais import CorrecoesManuais
from app.extraction.detector import DocumentTypeDetector
from app.extraction.documento_pdf import DocumentoPdf
from app.extraction.parsers.nome_cliente import extrair_nome_do_arquivo
from app.extraction.readers.base import TableReader, TextReader
from app.extraction.registry import ExtractorRegistry

logger = logging.getLogger(__name__)

# Abaixo desta similaridade, o nome do conteúdo e o do arquivo são considerados
# divergentes e o resultado recebe um aviso (possível arquivo renomeado errado,
# ou documento de espólio endereçado ao representante).
LIMIAR_DIVERGENCIA_NOME = 0.85

# Todo PDF contém "%PDF" no início do arquivo (a norma tolera lixo antes, por isso
# olhamos o primeiro 1 KB). Verificar os BYTES, e não a extensão, pega arquivos
# renomeados como "planilha.pdf" que na verdade são .xlsx.
ASSINATURA_PDF = b"%PDF"
TAMANHO_CABECALHO_PDF = 1024


class ExtractionPipeline:
    def __init__(
        self,
        detector: DocumentTypeDetector,
        registry: ExtractorRegistry,
        correcoes: CorrecoesManuais,
        leitor_texto: TextReader,
        leitor_ocr: TextReader,
        leitor_tabelas: TableReader,
    ) -> None:
        self._detector = detector
        self._registry = registry
        self._correcoes = correcoes
        self._leitor_texto = leitor_texto
        self._leitor_ocr = leitor_ocr
        self._leitor_tabelas = leitor_tabelas

    def processar(self, nome_arquivo: str, conteudo: bytes) -> ResultadoExtracao:
        nome_arquivo = _somente_nome(nome_arquivo)
        if ASSINATURA_PDF not in conteudo[:TAMANHO_CABECALHO_PDF]:
            return ResultadoExtracao(
                nome_arquivo=nome_arquivo,
                status=StatusExtracao.TIPO_DESCONHECIDO,
                avisos=["O arquivo não é um PDF."],
            )
        documento = DocumentoPdf(
            nome_arquivo, conteudo, self._leitor_texto, self._leitor_ocr, self._leitor_tabelas
        )

        # Fronteira de erro POR ARQUIVO: bibliotecas de PDF lançam exceções de
        # vários tipos (arquivo corrompido, criptografado, OCR ausente...).
        # Capturamos tudo aqui para que um arquivo ruim vire um item com status
        # ERRO, e não interrompa o processamento do lote.
        try:
            deteccao = self._detector.detectar(documento)
            if deteccao is None:
                return ResultadoExtracao(
                    nome_arquivo=nome_arquivo,
                    status=StatusExtracao.TIPO_DESCONHECIDO,
                    avisos=["Tipo não identificado pelo nome do arquivo nem pelo conteúdo."],
                )
            extracao = self._registry.obter(deteccao.tipo).extrair(documento)
            dados, campos_corrigidos = self._correcoes.aplicar(nome_arquivo, extracao.dados)
        except Exception as erro:
            logger.exception("Falha ao processar %s", nome_arquivo)
            return ResultadoExtracao(
                nome_arquivo=nome_arquivo,
                status=StatusExtracao.ERRO,
                erro=f"{type(erro).__name__}: {erro}",
            )

        # O nome do arquivo só é confiável como fonte do nome do cliente quando
        # o arquivo segue a convenção de nomes (tipo detectado pelo prefixo).
        nome_pelo_arquivo = None if deteccao.pelo_conteudo else extrair_nome_do_arquivo(nome_arquivo)

        avisos = list(extracao.avisos)
        if deteccao.pelo_conteudo:
            avisos.append("Tipo identificado pelo conteúdo: o nome do arquivo não segue a convenção.")
        avisos.extend(_verificar_divergencia_de_nome(extracao.nome_pelo_conteudo, nome_pelo_arquivo))

        return ResultadoExtracao(
            nome_arquivo=nome_arquivo,
            status=StatusExtracao.SUCESSO,
            tipo=deteccao.tipo,
            nome_pelo_arquivo=nome_pelo_arquivo,
            nome_pelo_conteudo=extracao.nome_pelo_conteudo,
            dados=dados,
            avisos=avisos,
            campos_corrigidos=campos_corrigidos,
        )


def _somente_nome(caminho: str) -> str:
    """'pasta/sub/arquivo.pdf' ou 'C:\\pasta\\arquivo.pdf' -> 'arquivo.pdf' (em NFC).

    No upload de pasta, o navegador envia o caminho relativo com '/'.
    """
    return normalizar_unicode(re.split(r"[\\/]", caminho)[-1])


def _verificar_divergencia_de_nome(nome_conteudo: str | None, nome_arquivo: str | None) -> list[str]:
    if not nome_conteudo or not nome_arquivo:
        return []
    similaridade = similaridade_nomes(nome_conteudo, nome_arquivo)
    if similaridade >= LIMIAR_DIVERGENCIA_NOME:
        return []
    return [
        f"Nome no conteúdo ('{nome_conteudo}') difere do nome do arquivo "
        f"('{nome_arquivo}'): similaridade {similaridade:.2f}."
    ]
