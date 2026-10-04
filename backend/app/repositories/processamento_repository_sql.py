"""ProcessamentoRepository com PostgreSQL. Cumpre o mesmo contrato da versão em memória.

Cada método abre a sua própria transação (`with self._sessoes.begin()`): o
commit acontece ao sair do bloco, e o rollback, se houver exceção. Isso é
importante aqui porque o processamento roda em segundo plano, fora de qualquer
requisição: cada item gravado é commitado na hora, e o frontend já vê o
progresso na consulta seguinte.
"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import defer, selectinload

from app.core.database import FabricaDeSessoes
from app.domain.enums import StatusProcessamento
from app.domain.processamento import ItemProcessamento, Processamento
from app.models import ProcessamentoItemModel, ProcessamentoModel
from app.repositories.conversao import resultado_de_json, resultado_para_json


class ProcessamentoRepositorySql:
    def __init__(self, sessoes: FabricaDeSessoes) -> None:
        self._sessoes = sessoes

    def criar(self, itens: list[ItemProcessamento], importar_automaticamente: bool = False) -> Processamento:
        with self._sessoes.begin() as sessao:
            model = ProcessamentoModel(
                status=StatusProcessamento.PENDENTE,
                importar_automaticamente=importar_automaticamente,
                itens=[_item_para_model(i) for i in itens],
            )
            sessao.add(model)
            sessao.flush()  # executa o INSERT agora, para o banco gerar o id
            return _para_dominio(model)

    def obter(self, processamento_id: int) -> Processamento | None:
        with self._sessoes() as sessao:
            # selectinload: busca os itens numa 2ª consulta (WHERE processamento_id IN ...),
            # evitando uma consulta por item (o famoso problema "N+1").
            model = sessao.get(ProcessamentoModel, processamento_id, options=[selectinload(ProcessamentoModel.itens)])
            return _para_dominio(model) if model else None

    def listar(self) -> list[Processamento]:
        with self._sessoes() as sessao:
            # A listagem só precisa dos contadores: não carrega o JSON dos resultados.
            consulta = (
                select(ProcessamentoModel)
                .options(selectinload(ProcessamentoModel.itens).options(defer(ProcessamentoItemModel.resultado)))
                .order_by(ProcessamentoModel.id.desc())
            )
            return [_para_dominio(model, com_resultados=False) for model in sessao.scalars(consulta)]

    def iniciar(self, processamento_id: int) -> None:
        # erro=None: um lote retomado depois de uma falha começa sem a mensagem antiga.
        self._atualizar(processamento_id, status=StatusProcessamento.PROCESSANDO, iniciado_em=func.now(), erro=None)

    def atualizar_item(self, processamento_id: int, item: ItemProcessamento) -> None:
        with self._sessoes.begin() as sessao:
            sessao.execute(
                update(ProcessamentoItemModel)
                .where(
                    ProcessamentoItemModel.processamento_id == processamento_id,
                    ProcessamentoItemModel.posicao == item.id,
                )
                .values(
                    status=item.status,
                    resultado=resultado_para_json(item.resultado) if item.resultado else None,
                    duplicado_de=item.duplicado_de,
                    erro=item.erro,
                )
            )

    def concluir(self, processamento_id: int) -> None:
        self._atualizar(processamento_id, status=StatusProcessamento.CONCLUIDO, finalizado_em=func.now())

    def falhar(self, processamento_id: int, erro: str) -> None:
        self._atualizar(processamento_id, status=StatusProcessamento.FALHOU, erro=erro, finalizado_em=func.now())

    def anotar_erro(self, processamento_id: int, erro: str) -> None:
        """Erro que não invalida o lote (ex.: a importação automática falhou; a leitura está boa)."""
        self._atualizar(processamento_id, erro=erro)

    def _atualizar(self, processamento_id: int, **valores) -> None:
        with self._sessoes.begin() as sessao:
            sessao.execute(update(ProcessamentoModel).where(ProcessamentoModel.id == processamento_id).values(**valores))


def _item_para_model(item: ItemProcessamento) -> ProcessamentoItemModel:
    return ProcessamentoItemModel(
        posicao=item.id,
        nome_arquivo=item.nome_arquivo,
        hash_sha256=item.hash_sha256,
        tamanho_bytes=item.tamanho_bytes,
        status=item.status,
        duplicado_de=item.duplicado_de,
        erro=item.erro,
        resultado=resultado_para_json(item.resultado) if item.resultado else None,
    )


def _para_dominio(model: ProcessamentoModel, com_resultados: bool = True) -> Processamento:
    return Processamento(
        id=model.id,
        criado_em=model.criado_em,
        status=model.status,
        iniciado_em=model.iniciado_em,
        finalizado_em=model.finalizado_em,
        erro=model.erro,
        importar_automaticamente=model.importar_automaticamente,
        itens=[
            ItemProcessamento(
                id=item.posicao,
                nome_arquivo=item.nome_arquivo,
                hash_sha256=item.hash_sha256,
                tamanho_bytes=item.tamanho_bytes,
                status=item.status,
                resultado=resultado_de_json(item.resultado) if com_resultados and item.resultado else None,
                duplicado_de=item.duplicado_de,
                erro=item.erro,
                documento_id=item.documento_id,
            )
            for item in model.itens
        ],
    )
