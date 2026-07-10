"""dmo — coaches (global) + templates/blocks/assignments/logs (multi-tenant) [WO F2-01]

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-10 00:00:00.000000

WO F2-01: porta el DMO (Daily Method of Operation) de AgentFlow al schema de la
suite (INGLES + multi-tenant). Tablas:
  - coaches            : CATALOGO GLOBAL (sin workspace_id). Metodologias oficiales.
  - dmo_templates      : workspace_id NULLABLE (NULL = catalogo oficial global;
                         set = custom del tenant). FK coaches + workspaces.
  - dmo_blocks         : bloques del template. FK dmo_templates.
  - dmo_assignments    : template asignado a cada vendedor. UNIQUE (workspace_id,
                         vendor_id). FK workspaces + users + dmo_templates.
  - dmo_logs           : reporte diario. UNIQUE (vendor_id, block_id, date) para
                         proteger contra duplicados (lo que en AgentFlow se
                         parcheaba a mano con `fix_dmo_duplicates`). FK workspaces
                         + users + dmo_blocks.

Modelos: backend/models/dmo.py

NOTA (igual que baseline 1e616292cc4e y las de F1): se escribio A MANO porque NO
hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la
Aiven compartida. El DDL usa tipos SQLAlchemy genericos validos para MySQL. NO se
verifico un `alembic upgrade head` real contra MySQL -- queda para un entorno con
MySQL (dev/Infra, etapa E1).

Ordenamiento MySQL-safe en `downgrade`: se dropean indices antes de las tablas y
las tablas hijas antes de las padre (dmo_logs/dmo_assignments/dmo_blocks ->
dmo_templates -> coaches).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- coaches (catalogo global) ----------
    op.create_table(
        'coaches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('is_official', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ---------- dmo_templates (workspace_id NULLABLE) ----------
    op.create_table(
        'dmo_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('coach_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('market', sa.String(length=40), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_office_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['coach_id'], ['coaches.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dmo_templates_workspace_id'), 'dmo_templates', ['workspace_id'], unique=False)

    # ---------- dmo_blocks ----------
    op.create_table(
        'dmo_blocks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_money_block', sa.Boolean(), nullable=False),
        sa.Column('metric_type', sa.String(length=20), nullable=False),
        sa.Column('metric_label', sa.String(length=60), nullable=True),
        sa.Column('metric_goal', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['dmo_templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dmo_blocks_template_id'), 'dmo_blocks', ['template_id'], unique=False)

    # ---------- dmo_assignments ----------
    op.create_table(
        'dmo_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['dmo_templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'vendor_id', name='uq_dmo_assignment_workspace_vendor'),
    )
    op.create_index(op.f('ix_dmo_assignments_workspace_id'), 'dmo_assignments', ['workspace_id'], unique=False)

    # ---------- dmo_logs ----------
    op.create_table(
        'dmo_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('metric_value', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['block_id'], ['dmo_blocks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vendor_id', 'block_id', 'date', name='uq_dmo_log_vendor_block_date'),
    )
    op.create_index(op.f('ix_dmo_logs_workspace_id'), 'dmo_logs', ['workspace_id'], unique=False)
    op.create_index('ix_dmo_logs_vendor_date', 'dmo_logs', ['vendor_id', 'date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_dmo_logs_vendor_date', table_name='dmo_logs')
    op.drop_index(op.f('ix_dmo_logs_workspace_id'), table_name='dmo_logs')
    op.drop_table('dmo_logs')

    op.drop_index(op.f('ix_dmo_assignments_workspace_id'), table_name='dmo_assignments')
    op.drop_table('dmo_assignments')

    op.drop_index(op.f('ix_dmo_blocks_template_id'), table_name='dmo_blocks')
    op.drop_table('dmo_blocks')

    op.drop_index(op.f('ix_dmo_templates_workspace_id'), table_name='dmo_templates')
    op.drop_table('dmo_templates')

    op.drop_table('coaches')
