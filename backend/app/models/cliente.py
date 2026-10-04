"""Tabelas `cliente` e `cliente_chave`."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.tipos import CriadoEm, IdPk

if TYPE_CHECKING:
    from app.models.documento import DocumentoModel


class ClienteModel(Base):
    __tablename__ = "cliente"

    id: Mapped[IdPk]
    nome: Mapped[str] = mapped_column(String(300))  # como exibir (grafia do documento)
    # Chave de NEGÓCIO: o nome lido do conteúdo, normalizado. Única.
    chave: Mapped[str] = mapped_column(String(300), unique=True)
    espolio: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[CriadoEm]
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documentos: Mapped[list["DocumentoModel"]] = relationship(back_populates="cliente")
    chaves: Mapped[list["ClienteChaveModel"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")


class ClienteChaveModel(Base):
    """Todas as chaves que identificam um cliente (a principal e os apelidos).

    Quando o usuário une dois clientes (ex.: "ROBERTO ALVEZ" com "ROBERTO
    ALVES"), a chave do cliente removido vira apelido do que ficou. Na
    próxima importação, um documento com a grafia antiga já vai direto para o
    cliente certo: o remanejamento feito à mão "ensina" o sistema.
    """

    __tablename__ = "cliente_chave"

    chave: Mapped[str] = mapped_column(String(300), primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id", ondelete="CASCADE"), index=True)
    criado_em: Mapped[CriadoEm]

    cliente: Mapped[ClienteModel] = relationship(back_populates="chaves")
