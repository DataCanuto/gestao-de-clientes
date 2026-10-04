"""/api/v1/importacoes: levar um processamento concluído para o banco.

POST cria uma importação (um recurso novo, com id e contadores): 201 Created.
Antes de importar, o frontend mostra GET /comparacoes/{processamento_id}, e o
usuário escolhe o que entra. Repetir a importação é seguro: arquivos já
importados são reconhecidos pelo hash e contados como "já existentes".
"""

from fastapi import APIRouter, status

from app.api.dependencies import ImportacaoServiceDep
from app.schemas.importacao import ImportacaoEntradaSchema, ImportacaoSchema

router = APIRouter(prefix="/importacoes", tags=["importações"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ImportacaoSchema, summary="Importa um lote para o banco")
def importar(entrada: ImportacaoEntradaSchema, servico: ImportacaoServiceDep) -> ImportacaoSchema:
    importacao = servico.importar(
        entrada.processamento_id,
        itens=entrada.itens,
        vincular=entrada.vincular_clientes,
        sobrescrever=entrada.sobrescrever_campos_editados,
    )
    return ImportacaoSchema.model_validate(importacao)


@router.get("", response_model=list[ImportacaoSchema], summary="Lista as importações")
def listar(servico: ImportacaoServiceDep, processamento_id: int | None = None) -> list[ImportacaoSchema]:
    importacoes = servico.listar()
    if processamento_id is not None:  # ex.: "este lote já foi salvo (automaticamente)?"
        importacoes = [i for i in importacoes if i.processamento_id == processamento_id]
    return [ImportacaoSchema.model_validate(i) for i in importacoes]
