"""/api/v1/documentos: consultar, corrigir, remanejar e excluir documentos importados.

    GET    /documentos                  filtros: ?tipo= ?cliente_id= ?sem_cliente= ?a_verificar=
    GET    /documentos/{id}             um documento
    GET    /documentos/{id}/historico   todas as alterações (versionamento)
    GET    /documentos/{id}/arquivo     o PDF original (para conferir na tela)
    PUT    /documentos/{id}             correção manual e/ou mudança de cliente
    DELETE /documentos/{id}             remove o documento (e o arquivo)            204
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import FileResponse

from app.api.dependencies import DocumentoServiceDep
from app.domain.enums import TipoDocumento
from app.schemas.documento import AlteracaoSchema, DocumentoArmazenadoSchema, EdicaoDocumentoSchema
from app.services.documento_service import EdicaoDocumento

router = APIRouter(prefix="/documentos", tags=["documentos"])


@router.get("", response_model=list[DocumentoArmazenadoSchema], summary="Lista documentos importados")
def listar_documentos(
    servico: DocumentoServiceDep,
    tipo: TipoDocumento | None = None,
    cliente_id: int | None = None,
    sem_cliente: Annotated[bool, Query(description="Só documentos sem cliente identificado")] = False,
    a_verificar: Annotated[bool, Query(description="Só documentos com campos não identificados")] = False,
) -> list[DocumentoArmazenadoSchema]:
    documentos = servico.listar(tipo, cliente_id, sem_cliente, a_verificar)
    return [DocumentoArmazenadoSchema.de_dominio(d) for d in documentos]


@router.get("/{documento_id}", response_model=DocumentoArmazenadoSchema, summary="Um documento")
def obter_documento(documento_id: int, servico: DocumentoServiceDep) -> DocumentoArmazenadoSchema:
    return DocumentoArmazenadoSchema.de_dominio(servico.obter(documento_id))


@router.get("/{documento_id}/historico", response_model=list[AlteracaoSchema], summary="Histórico de alterações")
def historico_do_documento(documento_id: int, servico: DocumentoServiceDep) -> list[AlteracaoSchema]:
    return [AlteracaoSchema.model_validate(a) for a in servico.historico(documento_id)]


@router.get("/{documento_id}/arquivo", response_class=FileResponse, summary="Abre o PDF original")
def arquivo_do_documento(documento_id: int, servico: DocumentoServiceDep) -> FileResponse:
    documento = servico.obter(documento_id)
    # "inline": o navegador exibe o PDF em vez de baixar.
    return FileResponse(
        servico.caminho_do_arquivo(documento_id),
        media_type="application/pdf",
        filename=documento.nome_arquivo,
        content_disposition_type="inline",
    )


@router.put("/{documento_id}", response_model=DocumentoArmazenadoSchema, summary="Corrige campos e/ou muda o cliente")
def atualizar_documento(
    documento_id: int, edicao: EdicaoDocumentoSchema, servico: DocumentoServiceDep
) -> DocumentoArmazenadoSchema:
    documento = servico.atualizar(documento_id, EdicaoDocumento(**edicao.model_dump()))
    return DocumentoArmazenadoSchema.de_dominio(documento)


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui o documento e o arquivo")
def excluir_documento(documento_id: int, servico: DocumentoServiceDep) -> Response:
    servico.excluir(documento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
