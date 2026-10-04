"""Tabelas `documento` e `alteracao_documento`.

Uma tabela para os TRÊS tipos de documento (NF, Planilha, Prestação), com uma
coluna `tipo` e colunas opcionais para os campos de cada tipo.

Alternativa descartada: uma tabela por tipo (nota_fiscal, planilha_comissao,
prestacao_contas). Seria mais "normalizada", mas a tabela geral (cliente + todos
os documentos) exigiria três consultas ou junções, e a edição manual, três
endpoints. Com seis colunas opcionais, a tabela única é mais simples de ler,
consultar e editar.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import OrigemAlteracao, Situacao, TipoDocumento
from app.models.tipos import CriadoEm, IdPk, coluna_enum

if TYPE_CHECKING:
    from app.models.cliente import ClienteModel


class DocumentoModel(Base):
    __tablename__ = "documento"

    id: Mapped[IdPk]
    # Identidade do ARQUIVO: o mesmo conteúdo nunca entra duas vezes.
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    nome_arquivo: Mapped[str] = mapped_column(String(500))
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger)
    tipo: Mapped[TipoDocumento] = mapped_column(coluna_enum(TipoDocumento, "tipo_documento"))

    # NULL = documento sem cliente identificado ("a verificar" no frontend).
    # ON DELETE SET NULL: excluir um cliente não apaga os documentos dele.
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("cliente.id", ondelete="SET NULL"), index=True)
    nome_pelo_conteudo: Mapped[str | None] = mapped_column(String(300))
    nome_pelo_arquivo: Mapped[str | None] = mapped_column(String(300))

    # --- campos extraídos (cada tipo usa os seus; os demais ficam NULL) ---
    data_emissao: Mapped[date | None] = mapped_column(Date)  # NF
    situacao: Mapped[Situacao | None] = mapped_column(coluna_enum(Situacao, "situacao"))  # todos
    corretor: Mapped[str | None] = mapped_column(String(200))  # Planilha
    anotacao: Mapped[str | None] = mapped_column(String(300))  # Planilha
    nome_encontrado: Mapped[str | None] = mapped_column(String(300))  # Prestação
    numero_processo: Mapped[str | None] = mapped_column(String(60), index=True)  # Prestação

    # JSONB: listas curtas que só são lidas junto com o documento.
    avisos: Mapped[list[str]] = mapped_column(JSONB, default=list)
    campos_editados: Mapped[list[str]] = mapped_column(JSONB, default=list)

    importado_em: Mapped[CriadoEm]
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cliente: Mapped["ClienteModel | None"] = relationship(back_populates="documentos")
    alteracoes: Mapped[list["AlteracaoDocumentoModel"]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
        order_by="AlteracaoDocumentoModel.id",
    )


class AlteracaoDocumentoModel(Base):
    """Histórico (versionamento) de cada documento: quem mudou o quê, de quanto para quanto.

    Os valores ficam como texto ("2023-03-08", "VALOR_TOTAL", "12 - ANA SOUZA")
    porque a coluna guarda campos de tipos diferentes; o histórico é para leitura
    humana e auditoria, não para cálculos.
    """

    __tablename__ = "alteracao_documento"

    id: Mapped[IdPk]
    documento_id: Mapped[int] = mapped_column(ForeignKey("documento.id", ondelete="CASCADE"), index=True)
    campo: Mapped[str] = mapped_column(String(50))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_novo: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[OrigemAlteracao] = mapped_column(coluna_enum(OrigemAlteracao, "origem_alteracao"))
    criado_em: Mapped[CriadoEm]

    documento: Mapped[DocumentoModel] = relationship(back_populates="alteracoes")
