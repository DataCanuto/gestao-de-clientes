"""Schemas de um documento (um PDF): dados extraídos, versão armazenada, edição e histórico."""

from dataclasses import asdict
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities import DadosExtraidos, DocumentoArmazenado, ResultadoExtracao
from app.domain.enums import OrigemAlteracao, OrigemNome, Situacao, TipoDocumento


class DadosDocumentoSchema(BaseModel):
    """Campos extraídos. Cada tipo de documento preenche só os seus:
    NF -> data_emissao, situacao; Planilha -> corretor, situacao, anotacao;
    Prestação -> nome_encontrado, numero_processo, situacao.

    Um único formato "achatado" (em vez de três) simplifica o frontend: a tela
    de edição mostra os campos que vierem preenchidos para o tipo.
    """

    data_emissao: date | None = None
    situacao: Situacao | None = None
    corretor: str | None = None
    anotacao: str | None = Field(default=None, description="Texto entre parênteses no nome do arquivo")
    nome_encontrado: str | None = None
    numero_processo: str | None = None

    @classmethod
    def de_dominio(cls, dados: DadosExtraidos | None) -> Self | None:
        return None if dados is None else cls(**asdict(dados))


class DocumentoSchema(BaseModel):
    nome_arquivo: str
    tipo: TipoDocumento | None
    nome_cliente: str | None = Field(description="Nome lido do conteúdo (ou, na falta dele, do nome do arquivo)")
    origem_nome: OrigemNome | None
    dados: DadosDocumentoSchema | None
    campos_a_verificar: list[str] = Field(description="Campos não identificados: corrigir manualmente")
    avisos: list[str]
    campos_corrigidos: list[str]

    @classmethod
    def de_dominio(cls, resultado: ResultadoExtracao) -> Self:
        return cls(
            nome_arquivo=resultado.nome_arquivo,
            tipo=resultado.tipo,
            nome_cliente=resultado.nome_cliente,
            origem_nome=resultado.origem_nome,
            dados=DadosDocumentoSchema.de_dominio(resultado.dados),
            campos_a_verificar=resultado.campos_a_verificar,
            avisos=resultado.avisos,
            campos_corrigidos=resultado.campos_corrigidos,
        )


class DocumentoArmazenadoSchema(DocumentoSchema):
    """Documento já importado: tem id (para editar), cliente e campos corrigidos à mão."""

    id: int
    hash_sha256: str
    tamanho_bytes: int
    cliente_id: int | None = Field(description="null = documento sem cliente (a verificar)")
    campos_editados: list[str] = Field(description="Campos corrigidos manualmente")
    importado_em: datetime | None

    @classmethod
    def de_dominio(cls, documento: DocumentoArmazenado) -> Self:
        return cls(
            **DocumentoSchema.de_dominio(documento).model_dump(),
            id=documento.id,
            hash_sha256=documento.hash_sha256,
            tamanho_bytes=documento.tamanho_bytes,
            cliente_id=documento.cliente_id,
            campos_editados=documento.campos_editados,
            importado_em=documento.importado_em,
        )


class EdicaoDocumentoSchema(BaseModel):
    """Corpo do PUT /documentos/{id}: o estado COMPLETO dos campos editáveis.

    PUT substitui a representação: o frontend envia todos os campos editáveis do
    tipo (os que não mudaram vão com o valor atual). `null` apaga o valor.
    Campos que não se aplicam ao tipo devem ir como null (ex.: corretor numa NF).
    Para mover o documento para outro cliente, basta mudar `cliente_id`.
    """

    cliente_id: int | None
    data_emissao: date | None = None
    situacao: Situacao | None = None
    corretor: str | None = None
    nome_encontrado: str | None = None
    numero_processo: str | None = None


class AlteracaoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campo: str
    valor_anterior: str | None
    valor_novo: str | None
    origem: OrigemAlteracao
    criado_em: datetime
