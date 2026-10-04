"""Exceções dos services.

Por que o service não lança HTTPException direto? Porque ele não deve saber que
existe HTTP: o mesmo service pode ser chamado por um script ou por um teste. A
tradução "exceção -> código HTTP" fica num lugar só (app/api/erros.py).
"""


class ServicoError(Exception):
    """Base das exceções de regra de aplicação."""


class NenhumArquivoEnviadoError(ServicoError):
    def __init__(self) -> None:
        super().__init__("Nenhum arquivo foi enviado.")


class ProcessamentoNaoEncontradoError(ServicoError):
    def __init__(self, processamento_id: int) -> None:
        super().__init__(f"Processamento {processamento_id} não encontrado.")


class ProcessamentoNaoConcluidoError(ServicoError):
    def __init__(self, processamento_id: int, status: str) -> None:
        super().__init__(f"Processamento {processamento_id} ainda não foi concluído (status: {status}).")


class ClienteNaoEncontradoError(ServicoError):
    def __init__(self, cliente_id: int) -> None:
        super().__init__(f"Cliente {cliente_id} não encontrado.")


class DocumentoNaoEncontradoError(ServicoError):
    def __init__(self, documento_id: int) -> None:
        super().__init__(f"Documento {documento_id} não encontrado.")


class ChaveDeClienteEmUsoError(ServicoError):
    def __init__(self, chave: str) -> None:
        super().__init__(f"Já existe um cliente identificado por '{chave}'. Use a união de clientes.")


class ClienteComDocumentosError(ServicoError):
    def __init__(self, cliente_id: int, quantidade: int) -> None:
        super().__init__(
            f"O cliente {cliente_id} tem {quantidade} documento(s). Mova os documentos ou una os clientes antes de excluir."
        )


class ItemNaoEncontradoError(ServicoError):
    def __init__(self, processamento_id: int, posicao: int) -> None:
        super().__init__(f"O processamento {processamento_id} não tem o arquivo {posicao}.")


class ItemJaImportadoError(ServicoError):
    def __init__(self, posicao: int, documento_id: int) -> None:
        super().__init__(
            f"O arquivo {posicao} já foi salvo no sistema (documento {documento_id}): corrija-o na tela de documentos."
        )


class LoteEmExecucaoError(ServicoError):
    def __init__(self, processamento_id: int) -> None:
        super().__init__(f"O processamento {processamento_id} já está em execução.")


class LoteNaoRetomavelError(ServicoError):
    def __init__(self, processamento_id: int, status: str) -> None:
        super().__init__(f"O processamento {processamento_id} não precisa ser retomado (status: {status}).")


class OperacaoInvalidaError(ServicoError):
    """Pedido que não faz sentido para a regra de negócio (ex.: unir um cliente com ele mesmo)."""
