"""GET /api/v1/dashboard: os números da tela inicial, calculados sobre os dados do banco."""

from fastapi import APIRouter

from app.api.dependencies import ClienteServiceDep, DocumentoServiceDep
from app.schemas.importacao import DashboardSchema
from app.schemas.relatorio import ResumoGeralSchema

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSchema, summary="Totais, faltantes e pendências")
def obter_dashboard(clientes: ClienteServiceDep, documentos: DocumentoServiceDep) -> DashboardSchema:
    resumo = ResumoGeralSchema.de_dominio(clientes.resumo())
    return DashboardSchema(**resumo.model_dump(), documentos_sem_cliente=len(documentos.listar(sem_cliente=True)))
