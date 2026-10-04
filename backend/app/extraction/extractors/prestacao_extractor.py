"""Prestação de Contas: PDF com camada de texto.

Campos (notebook): nome encontrado e número do processo.
Nome do cliente (CHAVE): `nome_encontrado` limpo. Atenção: em alguns espólios a
Prestação é endereçada ao REPRESENTANTE; nesses casos a chave difere da dos
outros documentos e a consolidação aponta uma "possível duplicidade".
Situação: anotação no nome do arquivo, ex.: "(VT Juliana)".
"""

from app.domain.entities import DadosPrestacaoContas
from app.domain.enums import TipoDocumento
from app.extraction.documento_pdf import DocumentoPdf
from app.extraction.extractors.base import DocumentExtractor, ExtracaoDocumento
from app.extraction.parsers.anotacao import interpretar_anotacao
from app.extraction.parsers.nome_cliente import limpar_nome_extraido
from app.extraction.parsers.prestacao import (
    extrair_nome_prestacao,
    extrair_numero_processo,
    limpar_nome_prestacao,
)
from app.extraction.siglas import TabelaSiglas


class PrestacaoContasExtractor(DocumentExtractor):
    tipo = TipoDocumento.PRESTACAO_CONTAS

    def __init__(self, siglas: TabelaSiglas) -> None:
        self._siglas = siglas

    def extrair(self, documento: DocumentoPdf) -> ExtracaoDocumento:
        texto = documento.texto  # lido uma única vez (o notebook lia duas)
        nome = extrair_nome_prestacao(texto)
        numero_processo = extrair_numero_processo(texto)

        avisos = []
        if nome is None:
            avisos.append("Nome não encontrado (padrão 'À <nome>').")
        if numero_processo is None:
            avisos.append("Número do processo não encontrado.")

        dados = DadosPrestacaoContas(
            nome_encontrado=nome,
            numero_processo=numero_processo,
            situacao=interpretar_anotacao(documento.nome_arquivo, self._siglas).situacao,
        )
        return ExtracaoDocumento(dados, limpar_nome_extraido(limpar_nome_prestacao(nome)), avisos)
