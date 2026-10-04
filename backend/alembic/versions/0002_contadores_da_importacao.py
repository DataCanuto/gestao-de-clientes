"""contadores de atualizados e ignorados na importacao

Fase 4 (comparação): a importação passa a atualizar documentos existentes (novas
versões) e a respeitar a seleção do usuário (itens ignorados).

Ajuste manual: server_default='0'. Sem ele, adicionar uma coluna NOT NULL falha
em qualquer banco que JÁ TENHA importações registradas (as linhas existentes
ficariam sem valor).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-26 22:10:06.174679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('importacao', sa.Column('documentos_atualizados', sa.Integer(), server_default='0', nullable=False))
    op.add_column('importacao', sa.Column('documentos_ignorados', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('importacao', 'documentos_ignorados')
    op.drop_column('importacao', 'documentos_atualizados')
