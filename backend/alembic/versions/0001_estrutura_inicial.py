"""estrutura inicial

Cria as tabelas: cliente, cliente_chave, documento, alteracao_documento,
processamento, processamento_item e importacao.

Ajustes manuais sobre o que o `alembic revision --autogenerate` gerou:
- colunas de enum com `create_constraint=False` + um único CheckConstraint com o
  nome da convenção (o autogenerate repetia a mesma restrição três vezes).

Revision ID: 0001
Revises: 
Create Date: 2026-09-26 17:33:45.224284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cliente',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('nome', sa.String(length=300), nullable=False),
    sa.Column('chave', sa.String(length=300), nullable=False),
    sa.Column('espolio', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cliente')),
    sa.UniqueConstraint('chave', name=op.f('uq_cliente_chave'))
    )
    op.create_table('processamento',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('status', sa.Enum('PENDENTE', 'PROCESSANDO', 'CONCLUIDO', 'FALHOU', name='status_processamento', native_enum=False, create_constraint=False, length=30), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('iniciado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finalizado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('erro', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('PENDENTE', 'PROCESSANDO', 'CONCLUIDO', 'FALHOU')", name=op.f('ck_processamento_status_processamento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_processamento'))
    )
    op.create_table('cliente_chave',
    sa.Column('chave', sa.String(length=300), nullable=False),
    sa.Column('cliente_id', sa.BigInteger(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_cliente_chave_cliente_id_cliente'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('chave', name=op.f('pk_cliente_chave'))
    )
    op.create_index(op.f('ix_cliente_chave_cliente_id'), 'cliente_chave', ['cliente_id'], unique=False)
    op.create_table('documento',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('hash_sha256', sa.String(length=64), nullable=False),
    sa.Column('nome_arquivo', sa.String(length=500), nullable=False),
    sa.Column('tamanho_bytes', sa.BigInteger(), nullable=False),
    sa.Column('tipo', sa.Enum('NOTA_FISCAL', 'PLANILHA_COMISSAO', 'PRESTACAO_CONTAS', name='tipo_documento', native_enum=False, create_constraint=False, length=30), nullable=False),
    sa.Column('cliente_id', sa.BigInteger(), nullable=True),
    sa.Column('nome_pelo_conteudo', sa.String(length=300), nullable=True),
    sa.Column('nome_pelo_arquivo', sa.String(length=300), nullable=True),
    sa.Column('data_emissao', sa.Date(), nullable=True),
    sa.Column('situacao', sa.Enum('VALOR_TOTAL', 'VALOR_FINAL', 'VALOR_INCONTROVERSO', 'ACORDO', 'CANCELADO', 'VERIFICAR', name='situacao', native_enum=False, create_constraint=False, length=30), nullable=True),
    sa.Column('corretor', sa.String(length=200), nullable=True),
    sa.Column('anotacao', sa.String(length=300), nullable=True),
    sa.Column('nome_encontrado', sa.String(length=300), nullable=True),
    sa.Column('numero_processo', sa.String(length=60), nullable=True),
    sa.Column('avisos', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('campos_editados', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('importado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("situacao IN ('VALOR_TOTAL', 'VALOR_FINAL', 'VALOR_INCONTROVERSO', 'ACORDO', 'CANCELADO', 'VERIFICAR')", name=op.f('ck_documento_situacao')),
    sa.CheckConstraint("tipo IN ('NOTA_FISCAL', 'PLANILHA_COMISSAO', 'PRESTACAO_CONTAS')", name=op.f('ck_documento_tipo_documento')),
    sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], name=op.f('fk_documento_cliente_id_cliente'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documento')),
    sa.UniqueConstraint('hash_sha256', name=op.f('uq_documento_hash_sha256'))
    )
    op.create_index(op.f('ix_documento_cliente_id'), 'documento', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_documento_numero_processo'), 'documento', ['numero_processo'], unique=False)
    op.create_table('importacao',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('processamento_id', sa.BigInteger(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('clientes_criados', sa.Integer(), nullable=False),
    sa.Column('documentos_criados', sa.Integer(), nullable=False),
    sa.Column('documentos_ja_existentes', sa.Integer(), nullable=False),
    sa.Column('documentos_sem_cliente', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['processamento_id'], ['processamento.id'], name=op.f('fk_importacao_processamento_id_processamento'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_importacao'))
    )
    op.create_index(op.f('ix_importacao_processamento_id'), 'importacao', ['processamento_id'], unique=False)
    op.create_table('alteracao_documento',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('documento_id', sa.BigInteger(), nullable=False),
    sa.Column('campo', sa.String(length=50), nullable=False),
    sa.Column('valor_anterior', sa.Text(), nullable=True),
    sa.Column('valor_novo', sa.Text(), nullable=True),
    sa.Column('origem', sa.Enum('IMPORTACAO', 'EDICAO_MANUAL', 'REMANEJAMENTO', 'UNIAO_DE_CLIENTES', name='origem_alteracao', native_enum=False, create_constraint=False, length=30), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("origem IN ('IMPORTACAO', 'EDICAO_MANUAL', 'REMANEJAMENTO', 'UNIAO_DE_CLIENTES')", name=op.f('ck_alteracao_documento_origem_alteracao')),
    sa.ForeignKeyConstraint(['documento_id'], ['documento.id'], name=op.f('fk_alteracao_documento_documento_id_documento'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alteracao_documento'))
    )
    op.create_index(op.f('ix_alteracao_documento_documento_id'), 'alteracao_documento', ['documento_id'], unique=False)
    op.create_table('processamento_item',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('processamento_id', sa.BigInteger(), nullable=False),
    sa.Column('posicao', sa.Integer(), nullable=False),
    sa.Column('nome_arquivo', sa.String(length=500), nullable=False),
    sa.Column('hash_sha256', sa.String(length=64), nullable=True),
    sa.Column('tamanho_bytes', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Enum('PENDENTE', 'SUCESSO', 'TIPO_DESCONHECIDO', 'ERRO', 'DUPLICADO', name='status_item', native_enum=False, create_constraint=False, length=30), nullable=False),
    sa.Column('duplicado_de', sa.String(length=500), nullable=True),
    sa.Column('erro', sa.Text(), nullable=True),
    sa.Column('resultado', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('documento_id', sa.BigInteger(), nullable=True),
    sa.CheckConstraint("status IN ('PENDENTE', 'SUCESSO', 'TIPO_DESCONHECIDO', 'ERRO', 'DUPLICADO')", name=op.f('ck_processamento_item_status_item')),
    sa.ForeignKeyConstraint(['documento_id'], ['documento.id'], name=op.f('fk_processamento_item_documento_id_documento'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['processamento_id'], ['processamento.id'], name=op.f('fk_processamento_item_processamento_id_processamento'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_processamento_item')),
    sa.UniqueConstraint('processamento_id', 'posicao', name=op.f('uq_processamento_item_processamento_id_posicao'))
    )
    op.create_index(op.f('ix_processamento_item_hash_sha256'), 'processamento_item', ['hash_sha256'], unique=False)
    op.create_index(op.f('ix_processamento_item_processamento_id'), 'processamento_item', ['processamento_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_processamento_item_processamento_id'), table_name='processamento_item')
    op.drop_index(op.f('ix_processamento_item_hash_sha256'), table_name='processamento_item')
    op.drop_table('processamento_item')
    op.drop_index(op.f('ix_alteracao_documento_documento_id'), table_name='alteracao_documento')
    op.drop_table('alteracao_documento')
    op.drop_index(op.f('ix_importacao_processamento_id'), table_name='importacao')
    op.drop_table('importacao')
    op.drop_index(op.f('ix_documento_numero_processo'), table_name='documento')
    op.drop_index(op.f('ix_documento_cliente_id'), table_name='documento')
    op.drop_table('documento')
    op.drop_index(op.f('ix_cliente_chave_cliente_id'), table_name='cliente_chave')
    op.drop_table('cliente_chave')
    op.drop_table('processamento')
    op.drop_table('cliente')
