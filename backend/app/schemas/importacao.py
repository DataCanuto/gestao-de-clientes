"""Schemas da importação (lote -> banco) e do dashboard."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.relatorio import ResumoGeralSchema


class ImportacaoEntradaSchema(BaseModel):
    """Corpo do POST /importacoes. Só `processamento_id` é obrigatório.

    Sem `itens`, vale a seleção padrão da comparação (`selecionado_por_padrao`).
    """

    processamento_id: int
    itens: list[int] | None = Field(default=None, description="Posições do lote a importar")
    vincular_clientes: dict[str, int] = Field(
        default_factory=dict, description="Chave do cliente no lote -> id de cliente existente"
    )
    sobrescrever_campos_editados: list[int] = Field(
        default_factory=list, description="Posições em que o valor extraído substitui a correção manual"
    )


class ImportacaoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processamento_id: int
    criado_em: datetime
    clientes_criados: int
    documentos_criados: int
    documentos_atualizados: int = Field(description="Novas versões aplicadas a documentos existentes")
    documentos_ja_existentes: int = Field(description="Mesmo arquivo (hash) já estava no banco: nada foi alterado")
    documentos_ignorados: int = Field(description="Não selecionados para importação")
    documentos_sem_cliente: int


class DashboardSchema(ResumoGeralSchema):
    """Números do dashboard sobre os dados do BANCO (e não de um lote)."""

    documentos_sem_cliente: int = Field(description="Documentos importados sem cliente identificado")
