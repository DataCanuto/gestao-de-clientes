"""Schemas da organização dos documentos em pastas."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.services.organizacao_service import ResultadoOrganizacao


class OrganizacaoEntradaSchema(BaseModel):
    incluir_pendentes: bool = Field(
        default=False, description="Copiar também documentos com campos a verificar (e mesclar os clientes deles)"
    )


class ConfiguracaoOrganizacaoSchema(BaseModel):
    pasta: str


class PendenciaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cliente: str | None
    nome_arquivo: str | None
    motivo: str


class ResultadoOrganizacaoSchema(BaseModel):
    pasta: str
    documentos_copiados: int
    pdfs_mesclados: int
    arquivos_removidos: int = Field(description="Gerados antes pelo sistema e que não fazem mais parte das pastas")
    clientes_incompletos: int = Field(description="Sem algum dos três tipos: não ganham PDF mesclado")
    relatorio: str | None
    pendencias: list[PendenciaSchema]

    @classmethod
    def de_dominio(cls, resultado: ResultadoOrganizacao) -> Self:
        return cls(
            pasta=str(resultado.pasta),
            documentos_copiados=resultado.documentos_copiados,
            pdfs_mesclados=resultado.pdfs_mesclados,
            arquivos_removidos=resultado.arquivos_removidos,
            clientes_incompletos=resultado.clientes_incompletos,
            relatorio=str(resultado.relatorio) if resultado.relatorio else None,
            pendencias=[PendenciaSchema.model_validate(p) for p in resultado.pendencias],
        )
