"""ProcessamentoService: extrai os dados de um lote e monta a tabela geral.

Fluxo de `processar` (roda em segundo plano, depois da resposta do upload):

    para cada item PENDENTE:
        hash já visto neste lote?  -> DUPLICADO (mesmo arquivo com outro nome)
        senão                      -> ExtractionPipeline.processar(nome, bytes)
        grava o item (o frontend acompanha o progresso item a item)
    marca o lote como CONCLUIDO

A tabela geral do lote não é gravada: é calculada a cada consulta a partir
dos resultados dos itens (função pura e rápida). Guardar só os fatos evita
cópias derivadas que poderiam ficar desatualizadas.

As consultas (tabela geral, resumo, faltantes) só usam o domínio já pronto
(domain/consolidacao.py, domain/relatorio.py): o service apenas localiza o lote
e verifica se ele já terminou.
"""

import logging
from dataclasses import replace
from pathlib import Path

from app.core.armazenamento import ArmazenamentoDeArquivos
from app.domain.consolidacao import ConsolidadorFichas
from app.domain.entities import Consolidacao, FichaCliente
from app.domain.enums import StatusItem, StatusProcessamento
from app.domain.processamento import STATUS_DO_ITEM, ItemProcessamento, Processamento
from app.domain.relatorio import ResumoGeral, clientes_com_documentos_faltantes, gerar_resumo
from app.domain.revisao import RevisaoDeItem, RevisaoInvalidaError, revisar
from app.extraction.pipeline import ASSINATURA_PDF, TAMANHO_CABECALHO_PDF, ExtractionPipeline
from app.repositories import ProcessamentoRepository
from app.services.exceptions import (
    ItemJaImportadoError,
    ItemNaoEncontradoError,
    OperacaoInvalidaError,
    ProcessamentoNaoConcluidoError,
    ProcessamentoNaoEncontradoError,
)

# Itens que uma pessoa pode revisar: lidos (talvez com erros de leitura) ou de tipo não reconhecido.
STATUS_REVISAVEIS = frozenset({StatusItem.SUCESSO, StatusItem.TIPO_DESCONHECIDO})

logger = logging.getLogger(__name__)


class ProcessamentoService:
    def __init__(
        self,
        repositorio: ProcessamentoRepository,
        armazenamento: ArmazenamentoDeArquivos,
        pipeline: ExtractionPipeline,
        consolidador: ConsolidadorFichas | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._armazenamento = armazenamento
        self._pipeline = pipeline
        self._consolidador = consolidador or ConsolidadorFichas()

    # ------------------------------------------------------------------ comando

    def processar(self, processamento_id: int) -> None:
        """Processa o lote inteiro. Nunca lança exceção: um erro inesperado marca o lote como FALHOU."""
        try:
            self._repositorio.iniciar(processamento_id)
            processamento = self.obter(processamento_id)
            logger.info("Processamento %s: %s arquivos", processamento_id, processamento.total_arquivos)

            # Num lote RETOMADO, os arquivos já lidos também contam: uma cópia de
            # um deles, lida agora, continua sendo DUPLICADO.
            primeiro_arquivo_por_hash: dict[str, str] = {}
            for item in processamento.itens:
                if item.concluido and item.hash_sha256 and item.status is not StatusItem.DUPLICADO:
                    primeiro_arquivo_por_hash.setdefault(item.hash_sha256, item.nome_arquivo)
            for item in processamento.itens:
                if not item.concluido:  # itens recusados no upload já nascem com status ERRO
                    self._repositorio.atualizar_item(processamento_id, self._processar_item(item, primeiro_arquivo_por_hash))

            self._repositorio.concluir(processamento_id)
            logger.info("Processamento %s concluído", processamento_id)
        except Exception as erro:  # fronteira da tarefa em segundo plano: ninguém mais capturaria
            logger.exception("Processamento %s falhou", processamento_id)
            self._repositorio.falhar(processamento_id, f"{type(erro).__name__}: {erro}")

    def _processar_item(self, item: ItemProcessamento, primeiro_arquivo_por_hash: dict[str, str]) -> ItemProcessamento:
        if item.hash_sha256 in primeiro_arquivo_por_hash:
            return replace(item, status=StatusItem.DUPLICADO, duplicado_de=primeiro_arquivo_por_hash[item.hash_sha256])
        primeiro_arquivo_por_hash[item.hash_sha256] = item.nome_arquivo

        resultado = self._pipeline.processar(item.nome_arquivo, self._armazenamento.ler(item.hash_sha256))
        return replace(item, status=STATUS_DO_ITEM[resultado.status], resultado=resultado, erro=resultado.erro)

    def obter_item(self, processamento_id: int, posicao: int) -> ItemProcessamento:
        item = next((i for i in self.obter(processamento_id).itens if i.id == posicao), None)
        if item is None:
            raise ItemNaoEncontradoError(processamento_id, posicao)
        return item

    def caminho_do_arquivo(self, processamento_id: int, posicao: int) -> Path:
        """O PDF de um arquivo do lote, para conferir na tela de revisão (antes de salvar)."""
        item = self.obter_item(processamento_id, posicao)
        if item.hash_sha256 is None or not self._armazenamento.existe(item.hash_sha256):
            raise ItemNaoEncontradoError(processamento_id, posicao)
        return self._armazenamento.caminho(item.hash_sha256)

    def revisar_item(self, processamento_id: int, posicao: int, revisao: RevisaoDeItem) -> ItemProcessamento:
        """Corrige o que a extração leu de UM arquivo, antes de salvar no sistema (ver domain/revisao.py).

        A comparação e a importação recalculam tudo a partir dos itens: a
        correção vale imediatamente para a tabela do lote e para o que será salvo.
        """
        self.obter_concluido(processamento_id)
        item = self.obter_item(processamento_id, posicao)
        if item.documento_id is not None:
            raise ItemJaImportadoError(posicao, item.documento_id)
        if item.status not in STATUS_REVISAVEIS or item.resultado is None:
            raise OperacaoInvalidaError(f"O arquivo {posicao} não pode ser revisado (status: {item.status.value}).")
        if ASSINATURA_PDF not in self._armazenamento.ler(item.hash_sha256)[:TAMANHO_CABECALHO_PDF]:
            raise OperacaoInvalidaError(f"O arquivo {posicao} não é um PDF: não pode entrar no sistema.")
        try:
            corrigido = revisar(item.resultado, revisao)
        except RevisaoInvalidaError as erro:
            raise OperacaoInvalidaError(str(erro)) from erro

        revisado = replace(item, status=StatusItem.SUCESSO, resultado=corrigido, erro=None)
        self._repositorio.atualizar_item(processamento_id, revisado)
        return revisado

    # ------------------------------------------------------------------ consultas

    def listar(self) -> list[Processamento]:
        return self._repositorio.listar()

    def obter(self, processamento_id: int) -> Processamento:
        processamento = self._repositorio.obter(processamento_id)
        if processamento is None:
            raise ProcessamentoNaoEncontradoError(processamento_id)
        return processamento

    def obter_concluido(self, processamento_id: int) -> Processamento:
        processamento = self.obter(processamento_id)
        if processamento.status is not StatusProcessamento.CONCLUIDO:
            raise ProcessamentoNaoConcluidoError(processamento_id, processamento.status.value)
        return processamento

    def consolidacao(self, processamento_id: int) -> Consolidacao:
        """Tabela geral do lote, recalculada a partir dos resultados de cada arquivo."""
        return self.consolidar(self.obter_concluido(processamento_id))

    def consolidar(self, processamento: Processamento) -> Consolidacao:
        return self._consolidador.consolidar(processamento.resultados_validos)

    def tabela_geral(self, processamento_id: int, apenas_com_faltantes: bool = False) -> list[FichaCliente]:
        fichas = self.consolidacao(processamento_id).fichas
        return clientes_com_documentos_faltantes(fichas) if apenas_com_faltantes else fichas

    def resumo(self, processamento_id: int) -> ResumoGeral:
        return gerar_resumo(self.consolidacao(processamento_id).fichas)
