"""GET /api/v1/comparacoes/{processamento_id}: o que o lote traria de diferente para o banco.

É um GET porque só LÊ: a comparação é calculada na hora (lote x estado atual do
banco) e nada é gravado. Por isso pode ser chamada quantas vezes for preciso,
por exemplo depois de corrigir algo no banco.
"""

from fastapi import APIRouter

from app.api.dependencies import ComparacaoServiceDep
from app.schemas.comparacao import ComparacaoSchema

router = APIRouter(prefix="/comparacoes", tags=["comparações"])


@router.get(
    "/{processamento_id}",
    response_model=ComparacaoSchema,
    summary="Compara um lote concluído com o banco: NOVO, IGUAL, ALTERADO, CONFLITO",
)
def comparar(processamento_id: int, servico: ComparacaoServiceDep) -> ComparacaoSchema:
    return ComparacaoSchema.de_dominio(servico.comparar(processamento_id))
