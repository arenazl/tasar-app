"""invitations -- invitacion por email al equipo (workspace + rol pre-asignados) (WO F4-05)

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-07-10 23:30:00.000000

WO F4-05: gestion de equipo real. El admin invita a un miembro por email con
un rol pre-asignado -> se crea una fila en `invitations` con un `token` opaco
unico; el invitado lo abre y se da de alta (User) en `invitations.workspace_id`
con `invitations.role`. La fila es la que porta workspace+rol (revocable,
expirable, un solo uso), no el JWT.

Tabla NUEVA, aditiva, con `workspace_id` (FK workspaces + indice) igual que el
resto del CRM multi-tenant (WO F1-01). Reversible.

NOTA (igual que baseline 1e616292cc4e / c4d5e6f7a8b9 / d9e0f1a2b3c4): escrita A
MANO, NO verificada con un `alembic upgrade head` real contra MySQL (no hay
MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la Aiven
compartida). DDL con tipos SQLAlchemy genericos validos para MySQL. La ejecuta
Infra en su entorno con MySQL (etapa E1).

Ordenamiento MySQL-safe en `downgrade`: se dropean las FK ANTES de la tabla
(InnoDB no permite soltar una tabla con constraints FK vivas apuntando fuera;
al hacer drop_table Alembic ya las remueve, pero mantenemos el patron explicito
de la casa dropeando indices antes de la tabla).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invitations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=True),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('invited_by', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invitations_workspace_id'), 'invitations', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_invitations_email'), 'invitations', ['email'], unique=False)
    op.create_index(op.f('ix_invitations_token'), 'invitations', ['token'], unique=True)
    op.create_index(op.f('ix_invitations_status'), 'invitations', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invitations_status'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_token'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_email'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_workspace_id'), table_name='invitations')
    op.drop_table('invitations')
