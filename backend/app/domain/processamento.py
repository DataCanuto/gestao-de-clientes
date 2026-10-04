"""Processamento: um lote de arquivos enviados de uma vez (um upload).

No notebook, o "lote" era a pasta inteira, processada de cima a baixo numa
execução. Na aplicação, cada upload vira um Processamento com um item por
arquivo, e o progresso pode ser acompanhado enquanto o OCR roda.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.entities import ResultadoExtracao
from app.domain.enums import StatusExtracao, StatusItem, StatusProcessamento

# Como o status da extração se traduz no status do item.
STATUS_DO_ITEM = {
    StatusExtracao.SUCESSO: StatusItem.SUCESSO,
    StatusExtracao.TIPO_DESCONHECIDO: StatusItem.TIPO_DESCONHECIDO,
    StatusExtracao.ERRO: StatusItem.ERRO,
}


@dataclass(slots=True)
class ItemProcessamento:
    id: int
    nome_arquivo: str  # como veio do navegador; no upload de pasta, inclui o caminho relativo
    hash_sha256: str | None  # None quando o arquivo foi recusado antes de ser salvo
    tamanho_bytes: int
    status: StatusItem = StatusItem.PENDENTE
    resultado: ResultadoExtracao | None = None
    duplicado_de: str | None = None  # nome do arquivo idêntico, quando DUPLICADO
    erro: str | None = None
    documento_id: int | None = None  # documento do banco, depois da importação

    @property
    def concluido(self) -> bool:
        return self.status is not StatusItem.PENDENTE


@dataclass(slots=True)
class Processamento:
    id: int
    criado_em: datetime
    itens: list[ItemProcessamento] = field(default_factory=list)
    status: StatusProcessamento = StatusProcessamento.PENDENTE
    iniciado_em: datetime | None = None
    finalizado_em: datetime | None = None
    erro: str | None = None
    # Salvar no banco sozinho ao terminar a leitura (seleção padrão da comparação).
    # Fica gravado para que um lote retomado depois de uma queda também seja salvo.
    importar_automaticamente: bool = False

    @property
    def total_arquivos(self) -> int:
        return len(self.itens)

    @property
    def arquivos_processados(self) -> int:
        return sum(1 for item in self.itens if item.concluido)

    @property
    def arquivos_com_erro(self) -> int:
        return sum(1 for item in self.itens if item.status is StatusItem.ERRO)

    @property
    def progresso_percentual(self) -> int:
        return round(100 * self.arquivos_processados / self.total_arquivos) if self.itens else 100

    @property
    def resultados_validos(self) -> list[ResultadoExtracao]:
        """Resultados que entram na tabela geral (duplicados e erros ficam de fora).

        A tabela geral do lote não é guardada: é recalculada a partir destes
        resultados sempre que consultada (ver ProcessamentoService.consolidacao).
        """
        return [item.resultado for item in self.itens if item.status is StatusItem.SUCESSO and item.resultado]
