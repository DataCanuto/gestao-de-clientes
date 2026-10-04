"""Schemas da comparação lote x banco (a tela "Comparação" do frontend).

Estrutura pensada para a tabela da tela:

    Cliente | Status | Campo | Valor atual | Novo valor | Ação
            └─ clientes[].status  └─ documentos[].diferencas[]  └─ selecionado_por_padrao
"""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from app.domain.comparacao import Comparacao, ComparacaoCliente, ComparacaoDocumento
from app.domain.enums import StatusComparacao, StatusItem, TipoDocumento


class DiferencaDeCampoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campo: str
    valor_atual: Any
    valor_novo: Any
    editado_manualmente: bool = Field(description="O valor atual foi corrigido à mão: só é substituído se pedido")


class ComparacaoDocumentoSchema(BaseModel):
    posicao_item: int
    nome_arquivo: str
    tipo: TipoDocumento
    status: StatusComparacao
    documento_id: int | None = Field(description="Documento do banco (IGUAL, ALTERADO, CONFLITO)")
    cliente_id_no_banco: int | None
    diferencas: list[DiferencaDeCampoSchema]
    observacao: str | None
    selecionado_por_padrao: bool = Field(description="Se o frontend deve marcar este item de início")

    @classmethod
    def de_dominio(cls, documento: ComparacaoDocumento, selecao_padrao: set[int]) -> Self:
        return cls(
            posicao_item=documento.posicao_item,
            nome_arquivo=documento.nome_arquivo,
            tipo=documento.tipo,
            status=documento.status,
            documento_id=documento.documento_id,
            cliente_id_no_banco=documento.cliente_id_no_banco,
            diferencas=[DiferencaDeCampoSchema.model_validate(d) for d in documento.diferencas],
            observacao=documento.observacao,
            selecionado_por_padrao=documento.posicao_item in selecao_padrao,
        )


class SugestaoDeClienteSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cliente_id: int
    nome: str
    similaridade: float


class ComparacaoClienteSchema(BaseModel):
    chave: str
    nome: str
    status: StatusComparacao
    cliente_id: int | None = Field(description="Cliente do banco com esta chave (null = cliente novo)")
    precisa_decisao: bool = Field(description="Nome parecido com cliente existente: vincular ou criar novo")
    sugestoes: list[SugestaoDeClienteSchema]
    documentos: list[ComparacaoDocumentoSchema]

    @classmethod
    def de_dominio(cls, cliente: ComparacaoCliente, selecao_padrao: set[int]) -> Self:
        return cls(
            chave=cliente.chave,
            nome=cliente.nome,
            status=cliente.status,
            cliente_id=cliente.cliente_id,
            precisa_decisao=cliente.precisa_decisao,
            sugestoes=[SugestaoDeClienteSchema.model_validate(s) for s in cliente.sugestoes],
            documentos=[ComparacaoDocumentoSchema.de_dominio(d, selecao_padrao) for d in cliente.documentos],
        )


class ItemForaDaImportacaoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    posicao_item: int
    nome_arquivo: str
    status: StatusItem
    motivo: str | None


class ResumoComparacaoSchema(BaseModel):
    clientes: dict[StatusComparacao, int]
    documentos: dict[StatusComparacao, int]


class ComparacaoSchema(BaseModel):
    processamento_id: int
    resumo: ResumoComparacaoSchema
    clientes: list[ComparacaoClienteSchema]
    documentos_sem_cliente: list[ComparacaoDocumentoSchema]
    fora_da_importacao: list[ItemForaDaImportacaoSchema] = Field(description="Arquivos com status ERRO na comparação")

    @classmethod
    def de_dominio(cls, comparacao: Comparacao) -> Self:
        selecao = comparacao.selecao_padrao()
        return cls(
            processamento_id=comparacao.processamento_id,
            resumo=ResumoComparacaoSchema(**comparacao.resumo),
            clientes=[ComparacaoClienteSchema.de_dominio(c, selecao) for c in comparacao.clientes],
            documentos_sem_cliente=[ComparacaoDocumentoSchema.de_dominio(d, selecao) for d in comparacao.documentos_sem_cliente],
            fora_da_importacao=[ItemForaDaImportacaoSchema.model_validate(i) for i in comparacao.fora_da_importacao],
        )
