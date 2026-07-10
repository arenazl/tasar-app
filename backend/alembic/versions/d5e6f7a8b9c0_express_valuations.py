"""express_valuations — tasacion express anclada (WO F1-03)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-10 00:00:00.000000

WO F1-03: tabla que persiste cada Tasacion Express (input + output + ancla usada).
Multi-tenant: `workspace_id` (FK workspaces + indice), como toda tabla nueva.
Modelo: backend/models/express_valuation.py

NOTA (igual que baseline 1e616292cc4e, 7b3f9c2a1d84 y c4d5e6f7a8b9): se escribio A
MANO porque NO hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic
contra la Aiven compartida. El DDL usa tipos SQLAlchemy genericos validos para
MySQL. NO se verifico un `alembic upgrade head` real contra MySQL -- queda para un
entorno con MySQL (dev/Infra, etapa E1).

Ordenamiento MySQL-safe en `downgrade`: se dropean los indices antes de la tabla.
Al ser una tabla NUEVA sin FKs entrantes, el drop es directo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'express_valuations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        # Datos de la propiedad evaluada
        sa.Column('property_type', sa.String(length=40), nullable=False),
        sa.Column('province', sa.String(length=80), nullable=True),
        sa.Column('city', sa.String(length=120), nullable=True),
        sa.Column('neighborhood', sa.String(length=120), nullable=True),
        sa.Column('address', sa.String(length=250), nullable=True),
        sa.Column('total_area_m2', sa.Float(), nullable=True),
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('condition', sa.String(length=40), nullable=True),
        # Ancla usada (resumen)
        sa.Column('anchor_scope', sa.String(length=20), nullable=True),
        sa.Column('anchor_count', sa.Integer(), nullable=True),
        sa.Column('anchor_median_ppm2', sa.Float(), nullable=True),
        # Resultado (denormalizado)
        sa.Column('price_per_m2_typical', sa.Float(), nullable=True),
        sa.Column('total_price_usd', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=5), nullable=True),
        sa.Column('confidence', sa.String(length=10), nullable=True),
        sa.Column('ai_used', sa.Boolean(), nullable=True),
        # Contratos completos
        sa.Column('input_json', sa.Text(), nullable=True),
        sa.Column('output_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_express_valuations_workspace_id'), 'express_valuations', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_express_valuations_property_type'), 'express_valuations', ['property_type'], unique=False)
    op.create_index(op.f('ix_express_valuations_anchor_scope'), 'express_valuations', ['anchor_scope'], unique=False)
    op.create_index(op.f('ix_express_valuations_created_at'), 'express_valuations', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_express_valuations_created_at'), table_name='express_valuations')
    op.drop_index(op.f('ix_express_valuations_anchor_scope'), table_name='express_valuations')
    op.drop_index(op.f('ix_express_valuations_property_type'), table_name='express_valuations')
    op.drop_index(op.f('ix_express_valuations_workspace_id'), table_name='express_valuations')
    op.drop_table('express_valuations')
