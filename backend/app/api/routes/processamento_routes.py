"""GET /api/v1/processamentos...: acompanhar um lote e consultar o resultado.

Todas as rotas são GET: só leem, não alteram nada (são "seguras" e podem ser
repetidas à vontade, por exemplo pelo polling de progresso do frontend).

    /processamentos                         lista os lotes (mais recentes primeiro)
    /processamentos/{id}                    progresso + cada arquivo e seus dados
    /processamentos/{id}/clientes           tabela geral (clientes e seus arquivos)
    /processamentos/{id}/resumo             números do dashboard
    /processamentos/{id}/verificacoes       o que revisar: duplicidades, OCR, sem cliente

E duas que ALTERAM o lote (antes de ele ir para o banco):

    GET  /processamentos/{id}/itens/{posicao}/arquivo   o PDF, para conferir na revisão
    PUT  /processamentos/{id}/itens/{posicao}   corrige o que foi lido de um arquivo
    POST /processamentos/{id}/retomar           continua um lote interrompido (202)

As rotas são funções comuns (def, sem async): o FastAPI as executa numa thread
separada, e o processamento em segundo plano não trava as consultas.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Response, status
from fastapi.responses import FileResponse

from app.api.dependencies import ExecucaoDeLotesDep, ProcessamentoServiceDep
from app.schemas.cliente import FichaClienteSchema, VerificacoesSchema
from app.schemas.processamento import (
    ItemProcessamentoSchema,
    ProcessamentoDetalheSchema,
    ProcessamentoResumoSchema,
    RevisaoItemSchema,
)
from app.services.execucao_service import ExecucaoDeLotes
from app.schemas.relatorio import ResumoGeralSchema

router = APIRouter(prefix="/processamentos", tags=["processamentos"])


@router.get("", response_model=list[ProcessamentoResumoSchema], summary="Lista os processamentos")
def listar_processamentos(servico: ProcessamentoServiceDep) -> list[ProcessamentoResumoSchema]:
    return [ProcessamentoResumoSchema.de_dominio(p, ExecucaoDeLotes.em_execucao(p.id)) for p in servico.listar()]


@router.get("/{processamento_id}", response_model=ProcessamentoDetalheSchema, summary="Progresso e arquivos do lote")
def obter_processamento(processamento_id: int, servico: ProcessamentoServiceDep) -> ProcessamentoDetalheSchema:
    return ProcessamentoDetalheSchema.de_dominio(servico.obter(processamento_id), ExecucaoDeLotes.em_execucao(processamento_id))


@router.get(
    "/{processamento_id}/clientes",
    response_model=list[FichaClienteSchema],
    summary="Tabela geral: cada cliente, seus arquivos e o que falta",
)
def listar_clientes(
    processamento_id: int,
    servico: ProcessamentoServiceDep,
    apenas_com_faltantes: Annotated[bool, Query(description="Só clientes com algum tipo de documento faltando")] = False,
) -> list[FichaClienteSchema]:
    fichas = servico.tabela_geral(processamento_id, apenas_com_faltantes)
    return [FichaClienteSchema.de_dominio(ficha) for ficha in fichas]


@router.get("/{processamento_id}/resumo", response_model=ResumoGeralSchema, summary="Números do dashboard")
def obter_resumo(processamento_id: int, servico: ProcessamentoServiceDep) -> ResumoGeralSchema:
    return ResumoGeralSchema.de_dominio(servico.resumo(processamento_id))


@router.get(
    "/{processamento_id}/verificacoes",
    response_model=VerificacoesSchema,
    summary="Possíveis duplicidades, nomes corrigidos do OCR e documentos sem cliente",
)
def obter_verificacoes(processamento_id: int, servico: ProcessamentoServiceDep) -> VerificacoesSchema:
    return VerificacoesSchema.de_dominio(servico.consolidacao(processamento_id))


@router.put(
    "/{processamento_id}/itens/{posicao}",
    response_model=ItemProcessamentoSchema,
    summary="Revisa o que foi lido de um arquivo, antes de salvar no sistema",
)
def revisar_item(
    processamento_id: int, posicao: int, revisao: RevisaoItemSchema, servico: ProcessamentoServiceDep
) -> ItemProcessamentoSchema:
    return ItemProcessamentoSchema.de_dominio(servico.revisar_item(processamento_id, posicao, revisao.para_dominio()))


@router.post(
    "/{processamento_id}/retomar",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessamentoResumoSchema,
    summary="Retoma um lote interrompido (servidor reiniciado no meio da leitura)",
)
def retomar(
    processamento_id: int, response: Response, tarefas: BackgroundTasks, execucao: ExecucaoDeLotesDep
) -> ProcessamentoResumoSchema:
    processamento = execucao.preparar_retomada(processamento_id)
    tarefas.add_task(execucao.executar, processamento_id)
    response.headers["Location"] = f"/api/v1/processamentos/{processamento_id}"
    return ProcessamentoResumoSchema.de_dominio(processamento, em_execucao=True)


@router.get(
    "/{processamento_id}/itens/{posicao}/arquivo",
    response_class=FileResponse,
    summary="Abre o PDF de um arquivo do lote (para conferir antes de salvar)",
)
def arquivo_do_item(processamento_id: int, posicao: int, servico: ProcessamentoServiceDep) -> FileResponse:
    item = servico.obter_item(processamento_id, posicao)
    return FileResponse(
        servico.caminho_do_arquivo(processamento_id, posicao),
        media_type="application/pdf",
        filename=item.nome_arquivo.replace("\\", "/").split("/")[-1],
        content_disposition_type="inline",
    )
