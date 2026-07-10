"""push_subscriptions -- Web Push PWA (WO F3-03)

Revision ID: b7c8d9e0f1a2
Revises: a3b4c5d6e7f8
Create Date: 2026-07-10 20:00:00.000000

WO F3-03: porta el modelo de suscripciones Web Push de AgentFlow
(backend/models/push_subscription.py) sobre la base multi-tenant de TasAR.
Se agrega `workspace_id` (misma convencion que el resto de las tablas nuevas
desde F1-01/c4d5e6f7a8b9 -- "toda tabla nueva lleva workspace_id"), ausente
en el original de AgentFlow por ser single-tenant.

Las claves VAPID (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT) y el
CRON_KEY del endpoint de resumen semanal NO se persisten en ninguna columna
-- viven SOLO en env/Secret Manager (backend/core/config.py), regla dura de
credenciales.

Migracion UNICA para F3-03 y REVERSIBLE.

NOTA (igual que las migraciones previas de la suite): escrita A MANO porque
NO hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra
la Aiven compartida. NO se verifico un `alembic upgrade head` real contra
MySQL -- queda para un entorno con MySQL (dev/Infra).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.String(length=200), nullable=False),
        sa.Column('auth', sa.String(length=100), nullable=False),
        sa.Column('user_agent', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_push_subscriptions_workspace_id'), 'push_subscriptions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_push_subscriptions_user_id'), 'push_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_push_subscriptions_id'), 'push_subscriptions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_push_subscriptions_id'), table_name='push_subscriptions')
    op.drop_index(op.f('ix_push_subscriptions_user_id'), table_name='push_subscriptions')
    op.drop_index(op.f('ix_push_subscriptions_workspace_id'), table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
