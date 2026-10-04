"""/api/v1/clientes: a tabela geral persistida e o remanejamento entre clientes.

    GET    /clientes                   tabela geral (?busca=joão, ?apenas_com_faltantes=true)
    GET    /clientes/{id}              um cliente com todos os documentos
    POST   /clientes                   cria um cliente (ex.: destino de um remanejamento)   201
    PUT    /clientes/{id}              corrige o nome / marca espólio
    DELETE /clientes/{id}              exclui um cliente SEM documentos                      204
    POST   /clientes/{id}/unir         absorve outro cliente (documentos + apelidos)

Por que "unir" é POST, e não PUT? Não é a substituição de um recurso: é uma
AÇÃO com efeitos em vários recursos (move documentos, transfere apelidos,
remove o cliente de origem). Ações assim são modeladas como POST.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import ClienteServiceDep
from app.schemas.cliente import ClienteEntradaSchema, ClienteSchema, UniaoClientesSchema

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteSchema], summary="Tabela geral dos clientes no banco")
def listar_clientes(
    servico: ClienteServiceDep,
    busca: Annotated[str | None, Query(description="Trecho do nome (sem diferenciar acentos e maiúsculas)")] = None,
    apenas_com_faltantes: bool = False,
) -> list[ClienteSchema]:
    return [ClienteSchema.de_dominio(f) for f in servico.listar(busca, apenas_com_faltantes)]


@router.get("/{cliente_id}", response_model=ClienteSchema, summary="Um cliente e todos os seus documentos")
def obter_cliente(cliente_id: int, servico: ClienteServiceDep) -> ClienteSchema:
    return ClienteSchema.de_dominio(servico.obter(cliente_id))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ClienteSchema, summary="Cria um cliente")
def criar_cliente(entrada: ClienteEntradaSchema, servico: ClienteServiceDep) -> ClienteSchema:
    return ClienteSchema.de_dominio(servico.criar(entrada.nome, entrada.espolio))


@router.put("/{cliente_id}", response_model=ClienteSchema, summary="Corrige o nome ou marca espólio")
def atualizar_cliente(cliente_id: int, entrada: ClienteEntradaSchema, servico: ClienteServiceDep) -> ClienteSchema:
    return ClienteSchema.de_dominio(servico.atualizar(cliente_id, entrada.nome, entrada.espolio))


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui um cliente sem documentos")
def excluir_cliente(cliente_id: int, servico: ClienteServiceDep) -> Response:
    servico.excluir(cliente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{cliente_id}/unir", response_model=ClienteSchema, summary="Une outro cliente a este")
def unir_clientes(cliente_id: int, entrada: UniaoClientesSchema, servico: ClienteServiceDep) -> ClienteSchema:
    return ClienteSchema.de_dominio(servico.unir(cliente_id, entrada.cliente_origem_id))
