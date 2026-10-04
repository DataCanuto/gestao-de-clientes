"""Schemas da tabela geral (FichaCliente), do cliente persistido e das verificações do lote."""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities import Consolidacao, FichaCliente
from app.domain.enums import OrigemNome, Situacao, TipoDocumento
from app.schemas.documento import DocumentoArmazenadoSchema, DocumentoSchema


class FichaClienteSchema(BaseModel):
    """Uma linha da tabela geral: o cliente, todos os seus documentos e o que falta."""

    nome: str
    chave: str = Field(description="Nome lido do conteúdo, normalizado: é o que une os arquivos")
    origem_chave: OrigemNome
    espolio: bool
    quantidade_documentos: dict[TipoDocumento, int]
    documentos_faltantes: list[TipoDocumento]
    documentos_a_verificar: int
    datas_nf: list[date]
    numeros_processo: list[str]
    nomes_encontrados: list[str]
    situacoes: list[Situacao]
    corretores: list[str]
    documentos: list[DocumentoSchema]

    @classmethod
    def de_dominio(cls, ficha: FichaCliente) -> Self:
        return cls(
            nome=ficha.nome,
            chave=ficha.chave,
            origem_chave=ficha.origem_chave,
            espolio=ficha.espolio,
            quantidade_documentos={tipo: len(ficha.documentos_do_tipo(tipo)) for tipo in TipoDocumento},
            documentos_faltantes=ficha.documentos_faltantes,
            documentos_a_verificar=len(ficha.documentos_a_verificar),
            datas_nf=ficha.datas_nf,
            numeros_processo=ficha.numeros_processo,
            nomes_encontrados=ficha.nomes_encontrados,
            situacoes=ficha.situacoes,
            corretores=ficha.corretores,
            documentos=[DocumentoSchema.de_dominio(d) for d in ficha.documentos],
        )


class PossivelDuplicidadeSchema(BaseModel):
    # from_attributes: o Pydantic lê os atributos do objeto do domínio pelo nome
    # (conversão automática, possível porque os campos são idênticos).
    model_config = ConfigDict(from_attributes=True)

    chave_a: str
    chave_b: str
    motivo: str


class ReconciliacaoOcrSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nome_arquivo: str
    chave_lida: str
    chave_adotada: str
    similaridade: float


class VerificacoesSchema(BaseModel):
    """O que o usuário precisa revisar (e remanejar) no frontend."""

    possiveis_duplicidades: list[PossivelDuplicidadeSchema]
    reconciliacoes_ocr: list[ReconciliacaoOcrSchema]
    documentos_sem_cliente: list[str]

    @classmethod
    def de_dominio(cls, consolidacao: Consolidacao) -> Self:
        return cls(
            possiveis_duplicidades=[PossivelDuplicidadeSchema.model_validate(d) for d in consolidacao.possiveis_duplicidades],
            reconciliacoes_ocr=[ReconciliacaoOcrSchema.model_validate(r) for r in consolidacao.reconciliacoes_ocr],
            documentos_sem_cliente=[documento.nome_arquivo for documento in consolidacao.documentos_sem_cliente],
        )


class ClienteSchema(FichaClienteSchema):
    """Cliente do banco: a ficha da tabela geral + id e documentos com id (editáveis)."""

    id: int
    documentos: list[DocumentoArmazenadoSchema]

    @classmethod
    def de_dominio(cls, ficha: FichaCliente) -> Self:
        base = FichaClienteSchema.de_dominio(ficha).model_dump(exclude={"documentos"})
        return cls(
            **base,
            id=ficha.id,
            documentos=[DocumentoArmazenadoSchema.de_dominio(d) for d in ficha.documentos],
        )


class ClienteEntradaSchema(BaseModel):
    """Corpo do POST /clientes e do PUT /clientes/{id}."""

    nome: str = Field(min_length=2, max_length=300)
    espolio: bool = False


class UniaoClientesSchema(BaseModel):
    """Corpo do POST /clientes/{id}/unir: o cliente que será absorvido."""

    cliente_origem_id: int
