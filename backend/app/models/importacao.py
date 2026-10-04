"""Tabela `importacao`: cada vez que um lote foi levado para o banco, e o que aconteceu."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.tipos import CriadoEm, IdPk


class ImportacaoModel(Base):
    __tablename__ = "importacao"

    id: Mapped[IdPk]
    processamento_id: Mapped[int] = mapped_column(ForeignKey("processamento.id", ondelete="CASCADE"), index=True)
    criado_em: Mapped[CriadoEm]
    clientes_criados: Mapped[int]
    documentos_criados: Mapped[int]
    documentos_atualizados: Mapped[int] = mapped_column(server_default="0")  # Fase 4 (migration 0002)
    documentos_ja_existentes: Mapped[int]
    documentos_ignorados: Mapped[int] = mapped_column(server_default="0")  # Fase 4 (migration 0002)
    documentos_sem_cliente: Mapped[int]
