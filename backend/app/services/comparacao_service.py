"""ComparacaoService: compara um lote concluído com o que já está no banco.

O service só reúne os dados:
    - o PLANO do lote (clientes e documentos, com hash e posição);
    - a FOTO do banco (clientes com documentos, apelidos, documentos sem cliente);
e entrega os dois para a função pura domain/comparacao.comparar, onde está a regra.

A comparação não é guardada: é recalculada a cada consulta. Se o usuário
corrigir algo no banco (ou importar outro lote) entre a consulta e a
importação, a importação compara de novo e usa o estado atual.
"""

from app.domain.comparacao import Comparacao, EstadoDoBanco, comparar
from app.domain.importacao import PlanoDoLote, montar_plano
from app.repositories import ClienteRepository, DocumentoRepository
from app.services.processamento_service import ProcessamentoService


class ComparacaoService:
    def __init__(
        self, processamentos: ProcessamentoService, clientes: ClienteRepository, documentos: DocumentoRepository
    ) -> None:
        self._processamentos = processamentos
        self._clientes = clientes
        self._documentos = documentos

    def comparar(self, processamento_id: int, vincular: dict[str, int] | None = None) -> Comparacao:
        return self.plano_e_comparacao(processamento_id, vincular)[1]

    def plano_e_comparacao(
        self, processamento_id: int, vincular: dict[str, int] | None = None
    ) -> tuple[PlanoDoLote, Comparacao]:
        processamento = self._processamentos.obter_concluido(processamento_id)
        plano = montar_plano(processamento, self._processamentos.consolidar(processamento))
        return plano, comparar(plano, self._estado_do_banco(), vincular)

    def _estado_do_banco(self) -> EstadoDoBanco:
        return EstadoDoBanco(
            clientes=self._clientes.listar(),
            cliente_por_chave=self._clientes.mapa_de_chaves(),
            documentos_sem_cliente=self._documentos.listar(sem_cliente=True),
        )
