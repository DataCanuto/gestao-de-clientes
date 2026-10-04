"""/api/v1/organizacoes: organizar os documentos do sistema em pastas do computador.

    GET  /organizacoes/configuracao   para onde os arquivos vão (a pasta do .env)
    POST /organizacoes                gera/atualiza as pastas; devolve o resumo

Por que POST? Não é uma consulta: grava arquivos no disco (e remove os que o
próprio sistema gerou antes e ficaram obsoletos). Repetir é seguro: o
resultado é sempre o retrato atual do banco.

A pasta de destino vem da configuração (PASTA_DOCUMENTOS), e não do corpo da
requisição: a API não deve gravar em qualquer caminho que um cliente HTTP
mandar. Para mudar o destino, muda-se o .env.
"""

from fastapi import APIRouter

from app.api.dependencies import OrganizacaoServiceDep
from app.schemas.organizacao import ConfiguracaoOrganizacaoSchema, OrganizacaoEntradaSchema, ResultadoOrganizacaoSchema

router = APIRouter(prefix="/organizacoes", tags=["organização em pastas"])


@router.get("/configuracao", response_model=ConfiguracaoOrganizacaoSchema, summary="Pasta onde os documentos são organizados")
def configuracao(servico: OrganizacaoServiceDep) -> ConfiguracaoOrganizacaoSchema:
    return ConfiguracaoOrganizacaoSchema(pasta=str(servico.pasta))


@router.post("", response_model=ResultadoOrganizacaoSchema, summary="Organiza os documentos em pastas e gera os PDFs mesclados")
def organizar(entrada: OrganizacaoEntradaSchema, servico: OrganizacaoServiceDep) -> ResultadoOrganizacaoSchema:
    return ResultadoOrganizacaoSchema.de_dominio(servico.organizar(entrada.incluir_pendentes))
