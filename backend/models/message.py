"""WaMessage — mensaje de una conversacion de WhatsApp (WO F2-03).

Portado de AgentFlow (WhatsappMessage) + SalesBot (Mensaje). El scoping por
workspace es via la conversacion (wa_conversations.workspace_id): un mensaje
pertenece a exactamente una conversacion.

`sender_id` NULL => lo escribio el BOT (outbound). `meta_message_id` unico => la
llave de idempotencia (WhatsApp Multi-Device entrega el mismo mensaje 2-3 veces).
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func,
)
from core.database import Base


DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"


class WaMessage(Base):
    __tablename__ = "wa_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("wa_conversations.id"), nullable=False, index=True)

    direction = Column(String(10), nullable=False)  # inbound | outbound
    type = Column(String(20), default="text")        # text | audio | image | video | document
    content = Column(Text, nullable=True)
    media_url = Column(String(500), nullable=True)
    transcription = Column(Text, nullable=True)

    # Idempotencia: unico. Baileys/Meta reentregan el mismo id; si ya existe, se
    # ignora el reenvio. Nullable porque los mensajes salientes del bot generan un
    # id local hasta que el gateway devuelve el real.
    meta_message_id = Column(String(128), nullable=True, unique=True, index=True)

    # NULL => bot; un id => vendedor humano que respondio desde el inbox.
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
