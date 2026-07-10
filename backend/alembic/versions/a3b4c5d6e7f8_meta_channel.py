"""Canal Meta Cloud API oficial — meta_phone_number_id en workspace_bot_config

Revision ID: a3b4c5d6e7f8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-10 18:00:00.000000

WO F3-02: canal Meta Cloud API oficial por workspace (el serio, vs Baileys no
oficial). El unico dato de Meta que vive en DB es `meta_phone_number_id` -- la
clave de RUTEO del webhook compartido (Meta manda el phone_number_id en cada
mensaje y con eso resolvemos el workspace, igual que el `slug` resuelve el
canal Baileys). El access_token, el verify_token y el app_secret son
credenciales de verdad y viven SOLO en env/Secret Manager
(settings.META_ACCESS_TOKEN / META_WEBHOOK_VERIFY_TOKEN / META_APP_SECRET) --
no se agrega ninguna columna para ellos (regla dura de credenciales).

`channel_provider` (baileys|meta) YA EXISTE desde F2-03 (a1b2c3d4e5f6) -- esta
migracion SOLO agrega lo que faltaba:
  backend/models/bot_config.py -> workspace_bot_config.meta_phone_number_id

Migracion UNICA para F3-02 y REVERSIBLE.

NOTA (igual que las migraciones previas de la suite): escrita A MANO porque NO
hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la
Aiven compartida. NO se verifico un `alembic upgrade head` real contra MySQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workspace_bot_config',
        sa.Column('meta_phone_number_id', sa.String(length=40), nullable=True),
    )
    op.create_unique_constraint(
        'uq_workspace_bot_config_meta_phone_number_id',
        'workspace_bot_config',
        ['meta_phone_number_id'],
    )
    op.create_index(
        'ix_workspace_bot_config_meta_phone_number_id',
        'workspace_bot_config',
        ['meta_phone_number_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_workspace_bot_config_meta_phone_number_id', table_name='workspace_bot_config')
    op.drop_constraint('uq_workspace_bot_config_meta_phone_number_id', 'workspace_bot_config', type_='unique')
    op.drop_column('workspace_bot_config', 'meta_phone_number_id')
