"""Audio full-duplex WhatsApp — voice_id + default_voice_mode en workspace_bot_config

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-10 15:00:00.000000

WO F3-01: TTS saliente (ElevenLabs, voz GENERICA — gate del dueno: SIN
voice-clone) + transcripcion entrante (Groq Whisper). `voice_mode` por
conversacion (wa_conversations.voice_mode) y `transcription` por mensaje
(wa_messages.transcription) YA EXISTEN desde F2-03 (a1b2c3d4e5f6) — esta
migracion SOLO agrega lo que faltaba: la voz y el default de modo por
workspace en workspace_bot_config.
  backend/models/bot_config.py -> workspace_bot_config.voice_id / .default_voice_mode

Migracion UNICA para F3-01 y REVERSIBLE.

NOTA (igual que las migraciones previas de la suite): escrita A MANO porque NO
hay MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la
Aiven compartida. NO se verifico un `alembic upgrade head` real contra MySQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workspace_bot_config', sa.Column('voice_id', sa.String(length=80), nullable=True))
    op.add_column('workspace_bot_config', sa.Column('default_voice_mode', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('workspace_bot_config', 'default_voice_mode')
    op.drop_column('workspace_bot_config', 'voice_id')
