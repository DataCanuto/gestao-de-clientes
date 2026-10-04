"""Tabelas `processamento` (um lote de upload) e `processamento_item` (um arquivo do lote)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import StatusItem, StatusProcessamento
from app.models.tipos import CriadoEm, IdPk, coluna_enum


class ProcessamentoModel(Base):
    __tablename__ = "processamento"

    id: Mapped[IdPk]
    status: Mapped[StatusProcessamento] = mapped_column(coluna_enum(StatusProcessamento, "status_processamento"))
    criado_em: Mapped[CriadoEm]
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro: Mapped[str | None] = mapped_column(Text)
    importar_automaticamente: Mapped[bool] = mapped_column(Boolean, server_default=false())

    itens: Mapped[list["ProcessamentoItemModel"]] = relationship(
        back_populates="processamento",
        cascade="all, delete-orphan",
        order_by="ProcessamentoItemModel.posicao",
    )


class ProcessamentoItemModel(Base):
    __tablename__ = "processamento_item"
    __table_args__ = (UniqueConstraint("processamento_id", "posicao"),)

    id: Mapped[IdPk]
    processamento_id: Mapped[int] = mapped_column(ForeignKey("processamento.id", ondelete="CASCADE"), index=True)
    posicao: Mapped[int]  # 1, 2, 3... dentro do lote (o "id" do item na API)
    nome_arquivo: Mapped[str] = mapped_column(String(500))
    hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[StatusItem] = mapped_column(coluna_enum(StatusItem, "status_item"))
    duplicado_de: Mapped[str | None] = mapped_column(String(500))
    erro: Mapped[str | None] = mapped_column(Text)
    # O que a extração encontrou, como JSON (ver repositories/serializacao.py).
    # Fica guardado para rever o lote e montar a tabela geral dele sem repetir o OCR.
    resultado: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Preenchido na importação: o documento do banco que veio deste arquivo.
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documento.id", ondelete="SET NULL"))

    processamento: Mapped[ProcessamentoModel] = relationship(back_populates="itens")
