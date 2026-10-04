"""Nota Fiscal: PDF escaneado, lido por OCR.

Campos (notebook): data de emissão.
Nome do cliente (CHAVE): "Cliente: ..." ou o nome após o número do processo.
Situação: anotação no nome do arquivo, ex.: "(CANCELADA)" -> CANCELADO.
"""

from app.domain.entities import DadosNotaFiscal
from app.domain.enums import TipoDocumento
from app.extraction.documento_pdf import DocumentoPdf
from app.extraction.extractors.base import DocumentExtractor, ExtracaoDocumento
from app.extraction.parsers.anotacao import interpretar_anotacao
from app.extraction.parsers.data_emissao import extrair_data_emissao
from app.extraction.parsers.nome_cliente import limpar_nome_extraido
from app.extraction.parsers.nota_fiscal import extrair_nome_nota_fiscal
from app.extraction.siglas import TabelaSiglas


class NotaFiscalExtractor(DocumentExtractor):
    tipo = TipoDocumento.NOTA_FISCAL

    def __init__(self, siglas: TabelaSiglas) -> None:
        self._siglas = siglas

    def extrair(self, documento: DocumentoPdf) -> ExtracaoDocumento:
        texto = documento.texto_ocr
        data_emissao = extrair_data_emissao(texto)
        nome = limpar_nome_extraido(extrair_nome_nota_fiscal(texto))
        situacao = interpretar_anotacao(documento.nome_arquivo, self._siglas).situacao

        avisos = []
        if data_emissao is None:
            avisos.append("Data de emissão não encontrada no OCR.")
        if nome is None:
            avisos.append("Nome do cliente não encontrado no OCR.")

        return ExtracaoDocumento(DadosNotaFiscal(data_emissao=data_emissao, situacao=situacao), nome, avisos)
