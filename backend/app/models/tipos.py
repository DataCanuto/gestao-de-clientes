"""Tipos de coluna reutilizados pelos models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Enum, Identity, func
from sqlalchemy.orm import mapped_column

# Chave primária técnica: BIGINT gerado pelo banco (IDENTITY, o padrão SQL
# moderno, no lugar do antigo SERIAL). Não tem significado de negócio: por isso
# nunca precisa mudar, mesmo que o nome do cliente seja corrigido.
IdPk = Annotated[int, mapped_column(BigInteger, Identity(), primary_key=True)]

# Data e hora COM fuso horário, preenchida pelo próprio banco.
CriadoEm = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]


def coluna_enum(enum: type[StrEnum], nome: str) -> Enum:
    """Enum guardado como VARCHAR + CHECK, e não como tipo ENUM nativo do PostgreSQL.

    Por quê? Acrescentar um valor a um ENUM nativo exige um ALTER TYPE especial
    na migration; com VARCHAR + CHECK, basta recriar a restrição. O Python
    continua recebendo o membro do enum (ex.: Situacao.VERIFICAR).
    """
    return Enum(
        enum,
        name=nome,
        native_enum=False,
        create_constraint=True,
        length=30,
        values_callable=lambda membros: [membro.value for membro in membros],
    )
