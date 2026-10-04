"""ImportacaoService: leva um lote para o banco, respeitando as escolhas do usuário.

    1. valida as escolhas (clientes vinculados existem? itens pertencem ao lote?);
    2. COMPARA de novo o lote com o banco, já com as vinculações aplicadas
       (o banco pode ter mudado desde que a tela de comparação foi aberta);
    3. DECIDE (domain/importacao.decidir): o que é novo, o que atualiza, o que
       fica igual, quais correções manuais são preservadas;
    4. o repositório grava o plano decidido numa única transação.

Escolhas do usuário (todas opcionais):
- itens: posições do lote a importar. Sem elas, vale a seleção padrão
  (NOVO e ALTERADO; CONFLITO e clientes que precisam de decisão ficam de fora);
- vincular: chave do lote -> cliente existente (para clientes "parecidos");
- sobrescrever: posições em que o valor extraído substitui a correção manual.
"""

from app.domain.importacao import Importacao, decidir
from app.repositories import ClienteRepository, ImportacaoRepository
from app.services.comparacao_service import ComparacaoService
from app.services.exceptions import ClienteNaoEncontradoError, OperacaoInvalidaError


class ImportacaoService:
    def __init__(
        self, comparacoes: ComparacaoService, clientes: ClienteRepository, repositorio: ImportacaoRepository
    ) -> None:
        self._comparacoes = comparacoes
        self._clientes = clientes
        self._repositorio = repositorio

    def importar(
        self,
        processamento_id: int,
        itens: list[int] | None = None,
        vincular: dict[str, int] | None = None,
        sobrescrever: list[int] | None = None,
    ) -> Importacao:
        vincular = vincular or {}
        for cliente_id in vincular.values():
            if self._clientes.obter(cliente_id) is None:
                raise ClienteNaoEncontradoError(cliente_id)

        plano, comparacao = self._comparacoes.plano_e_comparacao(processamento_id, vincular)

        chaves_desconhecidas = set(vincular) - {c.chave for c in plano.clientes}
        if chaves_desconhecidas:
            raise OperacaoInvalidaError(f"Clientes que não estão no lote: {', '.join(sorted(chaves_desconhecidas))}.")

        selecionados = comparacao.selecao_padrao() if itens is None else set(itens)
        importaveis = {d.posicao_item for d in comparacao.todos_os_documentos()}
        _exigir_subconjunto(selecionados, importaveis, "Itens que não podem ser importados (erro, duplicado ou inexistente)")
        sobrescrever_set = set(sobrescrever or [])
        _exigir_subconjunto(sobrescrever_set, selecionados, "Itens para sobrescrever que não foram selecionados")

        plano_decidido = decidir(plano, comparacao, selecionados, vincular, sobrescrever_set)
        return self._repositorio.importar(plano_decidido)

    def listar(self) -> list[Importacao]:
        return self._repositorio.listar()


def _exigir_subconjunto(itens: set[int], permitidos: set[int], mensagem: str) -> None:
    fora = sorted(itens - permitidos)
    if fora:
        raise OperacaoInvalidaError(f"{mensagem}: {', '.join(map(str, fora))}.")
