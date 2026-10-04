"""GET /api/v1/relatorios/clientes.xlsx: a planilha-relatório dos clientes (download).

GET porque só lê: a planilha é gerada na hora, a partir do banco, e não fica
guardada. `Content-Disposition: attachment` faz o navegador baixar o arquivo
com o nome sugerido, em vez de tentar abri-lo.
"""

from datetime import date

from fastapi import APIRouter, Response

from app.api.dependencies import ClienteServiceDep, DocumentoServiceDep
from app.exportacao.planilha_clientes import gerar_planilha_clientes

router = APIRouter(prefix="/relatorios", tags=["relatórios"])

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/clientes.xlsx",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}, "description": "Planilha .xlsx"}},
    summary="Baixa a planilha-relatório dos clientes (.xlsx)",
)
def baixar_planilha_clientes(clientes: ClienteServiceDep, documentos: DocumentoServiceDep) -> Response:
    conteudo = gerar_planilha_clientes(clientes.listar(), documentos.listar(sem_cliente=True))
    nome = f"relatorio_clientes_{date.today():%Y-%m-%d}.xlsx"
    return Response(conteudo, media_type=TIPO_XLSX, headers={"Content-Disposition": f'attachment; filename="{nome}"'})
