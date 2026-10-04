"""Planilha Comissão.

Nome do cliente (CHAVE): célula abaixo de "Cliente" na tabela do PDF, com a
    linha de texto como reserva.
Situação e corretor (notebook): anotação entre parênteses no nome do arquivo,
    interpretada pela tabela de siglas; a regra original do notebook é a reserva.
    Situação não identificada = VERIFICAR (corrigida manualmente no frontend).
"""

from app.domain.entities import DadosPlanilhaComissao
from app.domain.enums import Situacao, TipoDocumento
from app.extraction.documento_pdf import DocumentoPdf
from app.extraction.extractors.base import DocumentExtractor, ExtracaoDocumento
from app.extraction.parsers.anotacao import interpretar_anotacao
from app.extraction.parsers.nome_cliente import limpar_nome_extraido
from app.extraction.parsers.planilha import extrair_nome_da_tabela, extrair_nome_do_texto
from app.extraction.parsers.situacao_corretor import extrair_situacao_corretor
from app.extraction.siglas import TabelaSiglas

SITUACOES_CONHECIDAS = ", ".join(s.value for s in Situacao if s is not Situacao.VERIFICAR)


class PlanilhaComissaoExtractor(DocumentExtractor):
    tipo = TipoDocumento.PLANILHA_COMISSAO

    def __init__(self, siglas: TabelaSiglas) -> None:
        self._siglas = siglas

    def extrair(self, documento: DocumentoPdf) -> ExtracaoDocumento:
        avisos: list[str] = []

        nome = extrair_nome_da_tabela(documento.tabelas)
        if nome is None:
            nome = extrair_nome_do_texto(documento.texto)
            if nome:
                avisos.append("Tabela não reconhecida: nome lido pela linha de texto.")
        if nome is None:
            avisos.append("Nome do cliente não encontrado no conteúdo da planilha.")

        anotacao = interpretar_anotacao(documento.nome_arquivo, self._siglas)
        situacao, corretor = anotacao.situacao, anotacao.corretor
        if situacao is None:
            # Caso desconhecido: fica VERIFICAR, para o usuário corrigir no frontend.
            # O corretor ainda é buscado pela regra original do notebook.
            situacao = Situacao.VERIFICAR
            sigla, corretor = extrair_situacao_corretor(documento.nome_arquivo)
            if sigla:
                avisos.append(f"Sigla '{sigla}' sem situação correspondente ({SITUACOES_CONHECIDAS}).")
            else:
                avisos.append("Situação/corretor não encontrados no nome do arquivo.")
        if corretor is None:
            avisos.append("Corretor não identificado.")

        dados = DadosPlanilhaComissao(corretor=corretor, situacao=situacao, anotacao=anotacao.texto)
        return ExtracaoDocumento(dados, limpar_nome_extraido(nome), avisos)
