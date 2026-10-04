"""Repositório de processamentos (lotes de upload).

Duas partes:
- ProcessamentoRepository: o CONTRATO (o que se pode fazer com processamentos);
- ProcessamentoRepositoryEmMemoria: guarda tudo num dicionário. Foi a
  implementação da Fase 2 (API ainda sem banco) e hoje serve para testes
  rápidos da API, sem PostgreSQL. Os dados somem quando o processo termina.
- ProcessamentoRepositorySql (processamento_repository_sql.py): a implementação
  de produção, com PostgreSQL.

Por que um lock (threading.Lock)? O processamento roda em segundo plano, numa
thread diferente da que atende as requisições. Sem o lock, duas threads podem
alterar o mesmo dicionário ao mesmo tempo (ex.: gerar dois lotes com o mesmo id).
"""

import threading
from datetime import datetime
from typing import Protocol

from app.domain.enums import StatusProcessamento
from app.domain.processamento import ItemProcessamento, Processamento


class ProcessamentoRepository(Protocol):
    def criar(self, itens: list[ItemProcessamento], importar_automaticamente: bool = False) -> Processamento: ...

    def obter(self, processamento_id: int) -> Processamento | None: ...

    def listar(self) -> list[Processamento]: ...

    def iniciar(self, processamento_id: int) -> None: ...

    def atualizar_item(self, processamento_id: int, item: ItemProcessamento) -> None: ...

    def concluir(self, processamento_id: int) -> None: ...

    def falhar(self, processamento_id: int, erro: str) -> None: ...

    def anotar_erro(self, processamento_id: int, erro: str) -> None: ...


class ProcessamentoRepositoryEmMemoria:
    def __init__(self) -> None:
        self._processamentos: dict[int, Processamento] = {}
        self._proximo_id = 1
        self._lock = threading.Lock()

    def criar(self, itens: list[ItemProcessamento], importar_automaticamente: bool = False) -> Processamento:
        with self._lock:
            processamento = Processamento(
                id=self._proximo_id, criado_em=_agora(), itens=itens, importar_automaticamente=importar_automaticamente
            )
            self._processamentos[processamento.id] = processamento
            self._proximo_id += 1
            return processamento

    def obter(self, processamento_id: int) -> Processamento | None:
        return self._processamentos.get(processamento_id)

    def listar(self) -> list[Processamento]:
        return sorted(self._processamentos.values(), key=lambda p: p.id, reverse=True)

    def iniciar(self, processamento_id: int) -> None:
        with self._lock:
            processamento = self._processamentos[processamento_id]
            processamento.status = StatusProcessamento.PROCESSANDO
            processamento.iniciado_em = _agora()
            processamento.erro = None

    def atualizar_item(self, processamento_id: int, item: ItemProcessamento) -> None:
        with self._lock:
            itens = self._processamentos[processamento_id].itens
            itens[[i.id for i in itens].index(item.id)] = item

    def concluir(self, processamento_id: int) -> None:
        with self._lock:
            processamento = self._processamentos[processamento_id]
            processamento.status = StatusProcessamento.CONCLUIDO
            processamento.finalizado_em = _agora()

    def falhar(self, processamento_id: int, erro: str) -> None:
        with self._lock:
            processamento = self._processamentos[processamento_id]
            processamento.status = StatusProcessamento.FALHOU
            processamento.erro = erro
            processamento.finalizado_em = _agora()

    def anotar_erro(self, processamento_id: int, erro: str) -> None:
        with self._lock:
            self._processamentos[processamento_id].erro = erro


def _agora() -> datetime:
    return datetime.now().astimezone()
