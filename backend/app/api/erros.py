"""Tradução das exceções dos services em respostas HTTP.

Um único lugar decide "qual erro de negócio vira qual código HTTP". As rotas
ficam limpas: não precisam de try/except.

    400 Bad Request   -> a requisição não faz sentido (ex.: nenhum arquivo)
    404 Not Found     -> o recurso não existe
    409 Conflict      -> o pedido conflita com o estado atual
                         (ex.: tabela geral de um lote ainda em processamento,
                          excluir cliente que tem documentos, nome já usado)
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.exceptions import (
    ChaveDeClienteEmUsoError,
    ClienteComDocumentosError,
    ClienteNaoEncontradoError,
    DocumentoNaoEncontradoError,
    ItemJaImportadoError,
    ItemNaoEncontradoError,
    LoteEmExecucaoError,
    LoteNaoRetomavelError,
    NenhumArquivoEnviadoError,
    OperacaoInvalidaError,
    ProcessamentoNaoConcluidoError,
    ProcessamentoNaoEncontradoError,
    ServicoError,
)

CODIGO_HTTP_POR_ERRO: dict[type[ServicoError], int] = {
    NenhumArquivoEnviadoError: status.HTTP_400_BAD_REQUEST,
    OperacaoInvalidaError: status.HTTP_400_BAD_REQUEST,
    ProcessamentoNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    ClienteNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    DocumentoNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    ItemNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    ProcessamentoNaoConcluidoError: status.HTTP_409_CONFLICT,
    ItemJaImportadoError: status.HTTP_409_CONFLICT,
    LoteEmExecucaoError: status.HTTP_409_CONFLICT,
    LoteNaoRetomavelError: status.HTTP_409_CONFLICT,
    ChaveDeClienteEmUsoError: status.HTTP_409_CONFLICT,
    ClienteComDocumentosError: status.HTTP_409_CONFLICT,
}


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    @app.exception_handler(ServicoError)
    async def tratar_erro_de_servico(_: Request, erro: ServicoError) -> JSONResponse:
        codigo = CODIGO_HTTP_POR_ERRO.get(type(erro), status.HTTP_400_BAD_REQUEST)
        # Mesmo formato dos erros do próprio FastAPI: {"detail": "..."}
        return JSONResponse(status_code=codigo, content={"detail": str(erro)})
