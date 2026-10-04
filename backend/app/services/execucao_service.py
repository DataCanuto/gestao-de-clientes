"""ExecucaoDeLotes: roda um lote em segundo plano (leitura + importação automática) e o retoma se preciso.

Duas necessidades de produção que a Fase 2 não cobria:

1. **Salvar automaticamente.** "Receber uma lista de arquivos e salvar
   automaticamente": quando o upload pede, o lote é importado assim que a
   leitura termina, com a seleção padrão da comparação (NOVO e ALTERADO). O que
   exige decisão (CONFLITO, cliente parecido com um existente) fica de fora,
   esperando a pessoa na tela de comparação. Por que no servidor, e não o
   navegador chamando POST /importacoes ao fim do polling? Uma pasta inteira
   leva minutos de OCR; se a aba for fechada, a importação feita pelo navegador
   não aconteceria.

2. **Retomar.** O processamento roda dentro do processo do servidor
   (BackgroundTasks). Se o servidor for encerrado no meio (computador
   desligado), o lote fica PROCESSANDO para sempre. `retomar` processa só os
   arquivos que ainda estão PENDENTES (os já lidos ficam como estão).

Por que um conjunto de "lotes em execução" no nível da CLASSE? Os services são
criados a cada requisição, mas o servidor é um processo só: o conjunto é
compartilhado por todas as requisições e impede que o mesmo lote seja
processado duas vezes ao mesmo tempo (ex.: dois cliques em "Retomar").
Limitação conhecida: vale para UM processo; com vários workers seria preciso
um bloqueio no banco (ex.: SELECT ... FOR UPDATE SKIP LOCKED).
"""

import logging
import threading
from typing import ClassVar

from app.domain.enums import StatusProcessamento
from app.domain.processamento import Processamento
from app.repositories import ProcessamentoRepository
from app.services.exceptions import LoteEmExecucaoError, LoteNaoRetomavelError
from app.services.importacao_service import ImportacaoService
from app.services.processamento_service import ProcessamentoService

logger = logging.getLogger(__name__)

STATUS_RETOMAVEIS = frozenset({StatusProcessamento.PENDENTE, StatusProcessamento.PROCESSANDO, StatusProcessamento.FALHOU})


class ExecucaoDeLotes:
    _em_execucao: ClassVar[set[int]] = set()
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self, processamentos: ProcessamentoService, importacoes: ImportacaoService, repositorio: ProcessamentoRepository
    ) -> None:
        self._processamentos = processamentos
        self._importacoes = importacoes
        self._repositorio = repositorio

    @classmethod
    def em_execucao(cls, processamento_id: int) -> bool:
        with cls._lock:
            return processamento_id in cls._em_execucao

    def reservar(self, processamento_id: int) -> None:
        """Marca o lote como "em execução" ANTES de agendar a tarefa (evita duas tarefas para o mesmo lote)."""
        with self._lock:
            if processamento_id in self._em_execucao:
                raise LoteEmExecucaoError(processamento_id)
            self._em_execucao.add(processamento_id)

    def preparar_retomada(self, processamento_id: int) -> Processamento:
        processamento = self._processamentos.obter(processamento_id)
        if processamento.status not in STATUS_RETOMAVEIS:
            raise LoteNaoRetomavelError(processamento_id, processamento.status.value)
        self.reservar(processamento_id)
        return processamento

    def executar(self, processamento_id: int) -> None:
        """Tarefa em segundo plano. Nunca lança exceção (ninguém a capturaria)."""
        try:
            self._processamentos.processar(processamento_id)
            processamento = self._processamentos.obter(processamento_id)
            if processamento.importar_automaticamente and processamento.status is StatusProcessamento.CONCLUIDO:
                self._importar(processamento_id)
        except Exception:
            logger.exception("Execução do processamento %s falhou", processamento_id)
        finally:
            with self._lock:
                self._em_execucao.discard(processamento_id)

    def _importar(self, processamento_id: int) -> None:
        try:
            importacao = self._importacoes.importar(processamento_id)
            logger.info(
                "Processamento %s salvo automaticamente: %s documentos novos, %s ignorados (exigem decisão)",
                processamento_id, importacao.documentos_criados, importacao.documentos_ignorados,
            )
        except Exception as erro:
            logger.exception("Importação automática do processamento %s falhou", processamento_id)
            self._repositorio.anotar_erro(
                processamento_id, f"A importação automática falhou ({erro}). Salve pela tela de comparação."
            )
