"""DocumentoService: consultar, corrigir, remanejar e excluir documentos importados.

Correção manual: cada tipo de documento tem os SEUS campos editáveis. Enviar um
corretor para uma NF, por exemplo, é um erro (400), e não um valor ignorado em
silêncio.
"""

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from app.core.armazenamento import ArmazenamentoDeArquivos
from app.domain.entities import Alteracao, DocumentoArmazenado
from app.domain.enums import OrigemAlteracao, Situacao, TipoDocumento
from app.repositories import ClienteRepository, DocumentoRepository
from app.services.exceptions import ClienteNaoEncontradoError, DocumentoNaoEncontradoError, OperacaoInvalidaError

CAMPOS_EDITAVEIS: dict[TipoDocumento, frozenset[str]] = {
    TipoDocumento.NOTA_FISCAL: frozenset({"data_emissao", "situacao"}),
    TipoDocumento.PLANILHA_COMISSAO: frozenset({"situacao", "corretor"}),
    TipoDocumento.PRESTACAO_CONTAS: frozenset({"nome_encontrado", "numero_processo", "situacao"}),
}


@dataclass(frozen=True, slots=True)
class EdicaoDocumento:
    """Estado desejado do documento, como o usuário deixou na tela (semântica do PUT)."""

    cliente_id: int | None
    data_emissao: date | None = None
    situacao: Situacao | None = None
    corretor: str | None = None
    nome_encontrado: str | None = None
    numero_processo: str | None = None


class DocumentoService:
    def __init__(
        self, repositorio: DocumentoRepository, clientes: ClienteRepository, armazenamento: ArmazenamentoDeArquivos
    ) -> None:
        self._repositorio = repositorio
        self._clientes = clientes
        self._armazenamento = armazenamento

    def listar(
        self,
        tipo: TipoDocumento | None = None,
        cliente_id: int | None = None,
        sem_cliente: bool = False,
        a_verificar: bool = False,
    ) -> list[DocumentoArmazenado]:
        documentos = self._repositorio.listar(tipo, cliente_id, sem_cliente)
        # "A verificar" usa a regra do domínio (campos_a_verificar), e não um SQL
        # paralelo: a definição fica num lugar só.
        return [d for d in documentos if d.campos_a_verificar] if a_verificar else documentos

    def obter(self, documento_id: int) -> DocumentoArmazenado:
        documento = self._repositorio.obter(documento_id)
        if documento is None:
            raise DocumentoNaoEncontradoError(documento_id)
        return documento

    def historico(self, documento_id: int) -> list[Alteracao]:
        self.obter(documento_id)
        return self._repositorio.historico(documento_id)

    def atualizar(self, documento_id: int, edicao: EdicaoDocumento) -> DocumentoArmazenado:
        documento = self.obter(documento_id)
        if edicao.cliente_id is not None and self._clientes.obter(edicao.cliente_id) is None:
            raise ClienteNaoEncontradoError(edicao.cliente_id)

        valores = asdict(edicao)
        editaveis = CAMPOS_EDITAVEIS[documento.tipo]
        nao_aplicaveis = sorted(c for c, v in valores.items() if c != "cliente_id" and v is not None and c not in editaveis)
        if nao_aplicaveis:
            raise OperacaoInvalidaError(f"Campos que não se aplicam a {documento.tipo.value}: {', '.join(nao_aplicaveis)}.")

        # Percorre `valores` (ordem fixa dos campos de EdicaoDocumento), e não o
        # frozenset `editaveis`: a ordem de um set de strings muda de uma execução
        # do Python para outra, e o histórico sairia em ordem diferente a cada vez.
        novos_valores = {campo: valor for campo, valor in valores.items() if campo in editaveis or campo == "cliente_id"}
        return self._repositorio.atualizar(documento_id, novos_valores, OrigemAlteracao.EDICAO_MANUAL)

    def excluir(self, documento_id: int) -> None:
        documento = self.obter(documento_id)
        self._repositorio.excluir(documento_id)
        self._armazenamento.excluir(documento.hash_sha256)

    def caminho_do_arquivo(self, documento_id: int) -> Path:
        return self._armazenamento.caminho(self.obter(documento_id).hash_sha256)
