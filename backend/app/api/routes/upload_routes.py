"""POST /api/v1/uploads: recebe um ou vários PDFs (ou uma pasta) e inicia o processamento.

Por que POST? Cria um recurso novo (um processamento). E por que 202 Accepted,
e não 200 ou 201? Porque o trabalho ainda NÃO terminou: o arquivo foi aceito, e
a extração (OCR) roda em segundo plano. A resposta traz o id e o cabeçalho
Location com o endereço onde acompanhar o progresso.

multipart/form-data é o formato que o navegador usa para enviar arquivos: cada
arquivo vai numa "parte" do corpo, com o seu nome. No upload de pasta, o
frontend envia o caminho relativo como nome ("Lote/NF Ana.pdf").

`importar_automaticamente=true` (campo do formulário): ao terminar a leitura, o
lote é salvo no banco com a seleção padrão da comparação (ver
services/execucao_service.py). Sem ele, nada é salvo até a pessoa confirmar.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import ExecucaoDeLotesDep, UploadServiceDep
from app.schemas.processamento import ProcessamentoResumoSchema
from app.services.upload_service import ArquivoRecebido

router = APIRouter(tags=["uploads"])


@router.post(
    "/uploads",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessamentoResumoSchema,
    summary="Envia arquivos para processamento",
)
async def enviar_arquivos(
    response: Response,
    tarefas: BackgroundTasks,
    upload_service: UploadServiceDep,
    execucao: ExecucaoDeLotesDep,
    arquivos: Annotated[list[UploadFile], File(description="Um ou mais PDFs (campo repetido 'arquivos')")],
    importar_automaticamente: Annotated[bool, Form(description="Salvar no sistema ao terminar a leitura")] = False,
) -> ProcessamentoResumoSchema:
    # `async` para ler os arquivos da requisição sem travar o servidor...
    recebidos = [ArquivoRecebido(nome=arquivo.filename or "sem_nome", conteudo=await arquivo.read()) for arquivo in arquivos]
    # ...e run_in_threadpool para o trabalho síncrono (gravar em disco) não bloquear
    # as outras requisições enquanto os arquivos são salvos.
    processamento = await run_in_threadpool(upload_service.registrar_lote, recebidos, importar_automaticamente)

    # Roda DEPOIS que a resposta é enviada (ver docs/architecture.md, decisão D12).
    execucao.reservar(processamento.id)
    tarefas.add_task(execucao.executar, processamento.id)

    response.headers["Location"] = f"/api/v1/processamentos/{processamento.id}"
    return ProcessamentoResumoSchema.de_dominio(processamento, em_execucao=True)
