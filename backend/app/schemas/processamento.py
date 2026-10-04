"""Schemas de um processamento (lote de upload) e dos seus itens."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from app.domain.enums import Situacao, StatusItem, StatusProcessamento, TipoDocumento
from app.domain.processamento import ItemProcessamento, Processamento
from app.domain.revisao import RevisaoDeItem
from app.schemas.documento import DocumentoSchema


class ItemProcessamentoSchema(BaseModel):
    id: int
    nome_arquivo: str = Field(description="Nome como enviado (no upload de pasta, com o caminho relativo)")
    hash_sha256: str | None
    tamanho_bytes: int
    status: StatusItem
    duplicado_de: str | None = Field(description="Arquivo idêntico (mesmo hash) enviado no mesmo lote")
    erro: str | None
    documento: DocumentoSchema | None = Field(description="Dados extraídos (quando o arquivo foi processado)")
    documento_id: int | None = Field(description="Documento no banco, depois da importação")

    @classmethod
    def de_dominio(cls, item: ItemProcessamento) -> Self:
        return cls(
            id=item.id,
            nome_arquivo=item.nome_arquivo,
            hash_sha256=item.hash_sha256,
            tamanho_bytes=item.tamanho_bytes,
            status=item.status,
            duplicado_de=item.duplicado_de,
            erro=item.erro,
            documento=DocumentoSchema.de_dominio(item.resultado) if item.resultado else None,
            documento_id=item.documento_id,
        )


class ProcessamentoResumoSchema(BaseModel):
    """Situação do lote: o que o frontend consulta repetidamente para mostrar o progresso."""

    id: int
    status: StatusProcessamento
    criado_em: datetime
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    total_arquivos: int
    arquivos_processados: int
    arquivos_com_erro: int
    progresso_percentual: int
    erro: str | None
    importar_automaticamente: bool = Field(description="Salvar no sistema sozinho ao terminar a leitura")
    em_execucao: bool = Field(
        default=False, description="Sendo processado agora. PENDENTE/PROCESSANDO sem execução = interrompido: retomar"
    )

    @classmethod
    def de_dominio(cls, processamento: Processamento, em_execucao: bool = False) -> Self:
        return cls(
            id=processamento.id,
            status=processamento.status,
            criado_em=processamento.criado_em,
            iniciado_em=processamento.iniciado_em,
            finalizado_em=processamento.finalizado_em,
            total_arquivos=processamento.total_arquivos,
            arquivos_processados=processamento.arquivos_processados,
            arquivos_com_erro=processamento.arquivos_com_erro,
            progresso_percentual=processamento.progresso_percentual,
            erro=processamento.erro,
            importar_automaticamente=processamento.importar_automaticamente,
            em_execucao=em_execucao,
        )


class ProcessamentoDetalheSchema(ProcessamentoResumoSchema):
    itens: list[ItemProcessamentoSchema]

    @classmethod
    def de_dominio(cls, processamento: Processamento, em_execucao: bool = False) -> Self:
        resumo = ProcessamentoResumoSchema.de_dominio(processamento, em_execucao)
        return cls(**resumo.model_dump(), itens=[ItemProcessamentoSchema.de_dominio(i) for i in processamento.itens])


class RevisaoItemSchema(BaseModel):
    """Corpo do PUT /processamentos/{id}/itens/{posicao}: o arquivo como a pessoa conferiu.

    Estado COMPLETO (semântica de PUT): tipo, nome do cliente e os campos do tipo.
    Campos que não se aplicam ao tipo devem ir como null (ex.: corretor numa NF).
    """

    tipo: TipoDocumento
    nome_cliente: str | None = Field(default=None, max_length=300, description="Nome que une os arquivos do cliente")
    data_emissao: date | None = None
    situacao: Situacao | None = None
    corretor: str | None = Field(default=None, max_length=200)
    nome_encontrado: str | None = Field(default=None, max_length=300)
    numero_processo: str | None = Field(default=None, max_length=60)

    def para_dominio(self) -> RevisaoDeItem:
        return RevisaoDeItem(**self.model_dump())
