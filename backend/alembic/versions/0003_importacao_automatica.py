"""importacao automatica do lote

Fase 6 (integração): o upload pode pedir para salvar o lote no banco assim que
a leitura terminar ("receber uma lista de arquivos e salvar automaticamente").
A escolha fica gravada no lote para valer também quando um lote interrompido
(ex.: o computador desligou) é retomado depois.

Como na 0002: coluna NOT NULL com server_default, para funcionar num banco que
já tem lotes gravados (eles ficam com "false", que era o comportamento de antes).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30 12:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'processamento',
        sa.Column('importar_automaticamente', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('processamento', 'importar_automaticamente')
