"""Schema dos números do dashboard."""

from typing import Self

from pydantic import BaseModel, Field

from app.domain.enums import TipoDocumento
from app.domain.relatorio import ResumoGeral

SEM_SITUACAO = "SEM_SITUACAO"


class ResumoGeralSchema(BaseModel):
    total_clientes: int
    total_documentos: dict[TipoDocumento, int] = Field(description="Total de cada tipo de arquivo")
    clientes_sem_documento: dict[TipoDocumento, int] = Field(description="Quantos clientes não têm cada tipo")
    clientes_com_varios_documentos: dict[TipoDocumento, int]
    clientes_com_documentos_faltantes: int
    clientes_completos: int = Field(description="Clientes com os três tipos de documento (aptos ao PDF mesclado)")
    documentos_a_verificar: int
    planilhas_por_situacao: dict[str, int]

    @classmethod
    def de_dominio(cls, resumo: ResumoGeral) -> Self:
        return cls(
            total_clientes=resumo.total_clientes,
            total_documentos=resumo.total_documentos,
            clientes_sem_documento=resumo.clientes_sem_documento,
            clientes_com_varios_documentos=resumo.clientes_com_varios_documentos,
            clientes_com_documentos_faltantes=resumo.clientes_com_documentos_faltantes,
            clientes_completos=resumo.clientes_completos,
            documentos_a_verificar=resumo.documentos_a_verificar,
            # Chave de JSON precisa ser texto: None vira "SEM_SITUACAO".
            planilhas_por_situacao={
                (situacao.value if situacao else SEM_SITUACAO): quantidade
                for situacao, quantidade in resumo.planilhas_por_situacao.items()
            },
        )
