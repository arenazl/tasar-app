"""demo_data_flags -- is_demo en properties/users/wa_conversations (WO F5-03)

Revision ID: f7a8b9c0d1e2
Revises: e1f2a3b4c5d6
Create Date: 2026-07-10 23:50:00.000000

WO F5-03: onboarding self-service + generador de demo. El wizard post-registro
ofrece "cargar datos de ejemplo" (N propiedades + 3 vendedores + DMO asignado +
5 conversaciones de WhatsApp), y un boton "borrar datos de ejemplo" que borra
SOLO lo marcado demo, sin tocar datos reales (regla #11 CLAUDE.md global: los
datos demo van SIEMPRE marcados y NUNCA se presentan como reales).

3 columnas NUEVAS, aditivas, NOT NULL con default False (no rompen filas
existentes): properties.is_demo, users.is_demo, wa_conversations.is_demo.
`dmo_assignments`/`wa_messages` NO necesitan su propio flag: se identifican y
se purgan por pertenecer a un vendor_id/conversation_id ya marcado demo (ver
services/demo_service.py).

NOTA (igual que el resto de migraciones de la casa, ver e1f2a3b4c5d6): escrita
A MANO, NO verificada con un `alembic upgrade head` real contra MySQL (no hay
MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la Aiven
compartida). La ejecuta Infra en su entorno con MySQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('properties', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f('ix_properties_is_demo'), 'properties', ['is_demo'], unique=False)

    op.add_column('users', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f('ix_users_is_demo'), 'users', ['is_demo'], unique=False)

    op.add_column('wa_conversations', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f('ix_wa_conversations_is_demo'), 'wa_conversations', ['is_demo'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_wa_conversations_is_demo'), table_name='wa_conversations')
    op.drop_column('wa_conversations', 'is_demo')

    op.drop_index(op.f('ix_users_is_demo'), table_name='users')
    op.drop_column('users', 'is_demo')

    op.drop_index(op.f('ix_properties_is_demo'), table_name='properties')
    op.drop_column('properties', 'is_demo')
