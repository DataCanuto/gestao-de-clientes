"""ClienteService: a tabela geral persistida e o remanejamento entre clientes.

Operações:
- listar / obter: a tabela geral (cada cliente com todos os documentos e o que falta);
- criar: cliente novo, por exemplo para receber documentos remanejados;
- atualizar: corrigir o nome (a chave antiga vira apelido) ou marcar espólio;
- excluir: só clientes sem documentos;
- unir: juntar duas fichas que são o mesmo cliente (as "possíveis duplicidades").
"""

from app.domain.entities import FichaCliente
from app.domain.nomes import gerar_chave_cliente
from app.domain.relatorio import ResumoGeral, clientes_com_documentos_faltantes, gerar_resumo
from app.repositories import ClienteRepository
from app.services.exceptions import (
    ChaveDeClienteEmUsoError,
    ClienteComDocumentosError,
    ClienteNaoEncontradoError,
    OperacaoInvalidaError,
)


class ClienteService:
    def __init__(self, repositorio: ClienteRepository) -> None:
        self._repositorio = repositorio

    def listar(self, busca: str | None = None, apenas_com_faltantes: bool = False) -> list[FichaCliente]:
        # A busca usa a mesma normalização da chave: "joão" encontra "JOAO DA SILVA".
        fichas = self._repositorio.listar(gerar_chave_cliente(busca) if busca else None)
        return clientes_com_documentos_faltantes(fichas) if apenas_com_faltantes else fichas

    def obter(self, cliente_id: int) -> FichaCliente:
        ficha = self._repositorio.obter(cliente_id)
        if ficha is None:
            raise ClienteNaoEncontradoError(cliente_id)
        return ficha

    def criar(self, nome: str, espolio: bool = False) -> FichaCliente:
        chave = self._chave_livre(nome)
        return self._repositorio.criar(nome.strip(), chave, espolio)

    def atualizar(self, cliente_id: int, nome: str, espolio: bool) -> FichaCliente:
        self.obter(cliente_id)
        chave = self._chave_livre(nome, cliente_id)
        return self._repositorio.atualizar(cliente_id, nome.strip(), chave, espolio)

    def excluir(self, cliente_id: int) -> None:
        self.obter(cliente_id)
        quantidade = self._repositorio.contar_documentos(cliente_id)
        if quantidade:
            raise ClienteComDocumentosError(cliente_id, quantidade)
        self._repositorio.excluir(cliente_id)

    def unir(self, destino_id: int, origem_id: int) -> FichaCliente:
        """Os documentos de `origem` passam para `destino`, e `origem` deixa de existir."""
        if destino_id == origem_id:
            raise OperacaoInvalidaError("Não é possível unir um cliente com ele mesmo.")
        self.obter(destino_id)
        self.obter(origem_id)
        return self._repositorio.unir(destino_id, origem_id)

    def resumo(self) -> ResumoGeral:
        return gerar_resumo(self._repositorio.listar())

    def _chave_livre(self, nome: str, cliente_id: int | None = None) -> str:
        chave = gerar_chave_cliente(nome)
        if not chave:
            raise OperacaoInvalidaError("Informe um nome de cliente válido.")
        dono = self._repositorio.id_pela_chave(chave)
        if dono is not None and dono != cliente_id:
            raise ChaveDeClienteEmUsoError(chave)
        return chave
