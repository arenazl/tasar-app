"""Bot WhatsApp embebido — wa_conversations/wa_messages/workspace_bot_config/bot_faqs

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-07-10 12:00:00.000000

WO F2-03: bot conversacional de WhatsApp con tools nativas, POR WORKSPACE. Tablas y
columnas en INGLES; toda tabla nueva lleva `workspace_id` (FK workspaces + indice).
Modelos:
  backend/models/conversation.py  -> wa_conversations
  backend/models/message.py       -> wa_messages
  backend/models/bot_config.py    -> workspace_bot_config + bot_faqs

Migracion UNICA para el paquete F2-03 y REVERSIBLE: `downgrade` deshace exactamente
lo que `upgrade` crea.

NOTA (igual que las migraciones previas de la suite): escrita A MANO porque NO hay
MySQL en el entorno de autoria y esta PROHIBIDO correr Alembic contra la Aiven
compartida. El DDL usa tipos SQLAlchemy genericos validos para MySQL. NO se verifico
un `alembic upgrade head` real contra MySQL -- queda para un entorno con MySQL
(dev/Infra, etapa E1).

Ordenamiento MySQL-safe: en `downgrade` se dropea la FK ANTES del indice/columna que
sostiene, y las tablas hijas ANTES que las padres (wa_messages antes de
wa_conversations).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 1) wa_conversations (NUEVA) ===
    op.create_table(
        'wa_conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('phone_jid', sa.String(length=80), nullable=False),
        sa.Column('phone_public', sa.String(length=40), nullable=True),
        sa.Column('contact_name', sa.String(length=200), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('unread_count', sa.Integer(), nullable=True),
        sa.Column('bot_paused_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voice_mode', sa.String(length=10), nullable=True),
        sa.Column('rolling_summary_md', sa.Text(), nullable=True),
        sa.Column('summary_up_to_message_id', sa.Integer(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'phone_jid', name='uq_wa_conv_workspace_jid'),
    )
    op.create_index(op.f('ix_wa_conversations_workspace_id'), 'wa_conversations', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_wa_conversations_phone_jid'), 'wa_conversations', ['phone_jid'], unique=False)
    op.create_index(op.f('ix_wa_conversations_client_id'), 'wa_conversations', ['client_id'], unique=False)
    op.create_index(op.f('ix_wa_conversations_assignee_id'), 'wa_conversations', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_wa_conversations_status'), 'wa_conversations', ['status'], unique=False)
    op.create_index(op.f('ix_wa_conversations_last_activity_at'), 'wa_conversations', ['last_activity_at'], unique=False)

    # === 2) wa_messages (NUEVA) ===
    op.create_table(
        'wa_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('media_url', sa.String(length=500), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('meta_message_id', sa.String(length=128), nullable=True),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['wa_conversations.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_wa_messages_conversation_id'), 'wa_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_wa_messages_meta_message_id'), 'wa_messages', ['meta_message_id'], unique=True)
    op.create_index(op.f('ix_wa_messages_created_at'), 'wa_messages', ['created_at'], unique=False)

    # === 3) workspace_bot_config (NUEVA, 1 por workspace) ===
    op.create_table(
        'workspace_bot_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('business_name', sa.String(length=200), nullable=True),
        sa.Column('business_description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=300), nullable=True),
        sa.Column('zones', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=60), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('website', sa.String(length=200), nullable=True),
        sa.Column('services', sa.Text(), nullable=True),
        sa.Column('commissions_text', sa.Text(), nullable=True),
        sa.Column('differentials', sa.Text(), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('off_hours_message', sa.Text(), nullable=True),
        sa.Column('derivation_message', sa.Text(), nullable=True),
        sa.Column('business_hours', sa.Text(), nullable=True),
        sa.Column('derivation_words', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(length=30), nullable=True),
        sa.Column('channel_provider', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', name='uq_workspace_bot_config_workspace'),
    )
    op.create_index(op.f('ix_workspace_bot_config_workspace_id'), 'workspace_bot_config', ['workspace_id'], unique=False)

    # === 4) bot_faqs (NUEVA) ===
    op.create_table(
        'bot_faqs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_faqs_workspace_id'), 'bot_faqs', ['workspace_id'], unique=False)


def downgrade() -> None:
    # === 4) bot_faqs ===
    op.drop_index(op.f('ix_bot_faqs_workspace_id'), table_name='bot_faqs')
    op.drop_table('bot_faqs')

    # === 3) workspace_bot_config ===
    op.drop_index(op.f('ix_workspace_bot_config_workspace_id'), table_name='workspace_bot_config')
    op.drop_table('workspace_bot_config')

    # === 2) wa_messages (hija de wa_conversations -> se dropea primero) ===
    op.drop_index(op.f('ix_wa_messages_created_at'), table_name='wa_messages')
    op.drop_index(op.f('ix_wa_messages_meta_message_id'), table_name='wa_messages')
    op.drop_index(op.f('ix_wa_messages_conversation_id'), table_name='wa_messages')
    op.drop_table('wa_messages')

    # === 1) wa_conversations ===
    op.drop_index(op.f('ix_wa_conversations_last_activity_at'), table_name='wa_conversations')
    op.drop_index(op.f('ix_wa_conversations_status'), table_name='wa_conversations')
    op.drop_index(op.f('ix_wa_conversations_assignee_id'), table_name='wa_conversations')
    op.drop_index(op.f('ix_wa_conversations_client_id'), table_name='wa_conversations')
    op.drop_index(op.f('ix_wa_conversations_phone_jid'), table_name='wa_conversations')
    op.drop_index(op.f('ix_wa_conversations_workspace_id'), table_name='wa_conversations')
    op.drop_table('wa_conversations')
