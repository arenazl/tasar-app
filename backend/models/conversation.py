"""WaConversation — hilo de WhatsApp por contacto y POR WORKSPACE (WO F2-03).

Portado del patron de AgentFlow (WhatsappConversation) + SalesBot (Conversacion),
adaptado a multi-tenant: cada conversacion lleva `workspace_id` (FK + indice) y es
UNICA por (workspace_id, phone_jid). El bot que la atiende, su KB y sus tools estan
scoped al workspace de la conversacion (NO hay singleton global — se evita el
anti-patron BotConfig id=1 de AgentFlow).

Convencion de la casa (TasAR): los "enum" se guardan como String con comentario de
valores validos (no SAEnum), para un DDL portable a MySQL.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func,
)
from core.database import Base


# Estados de la conversacion (equivalen a los de AgentFlow WaConversacionEstado).
STATUS_NUEVA = "nueva"
STATUS_ABIERTA = "abierta"
STATUS_CERRADA = "cerrada"
STATUS_BLOQUEADA = "bloqueada"


class WaConversation(Base):
    __tablename__ = "wa_conversations"
    __table_args__ = (
        # Una conversacion por contacto por workspace: clave del scoping y de la
        # dedup de contactos que reescriben desde el mismo JID.
        UniqueConstraint("workspace_id", "phone_jid", name="uq_wa_conv_workspace_jid"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    # JID del contacto (ej '5491122334455@s.whatsapp.net' o un '@lid').
    phone_jid = Column(String(80), nullable=False, index=True)
    # Numero publico del tenant (la agencia) por el que entro el mensaje.
    phone_public = Column(String(40), nullable=True)
    contact_name = Column(String(200), nullable=True)

    # Vinculo opcional con el CRM (clients) y con el vendedor asignado (users).
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(String(20), default=STATUS_NUEVA, index=True)
    # nueva | abierta | cerrada | bloqueada
    unread_count = Column(Integer, default=0)

    # Coexistence: mientras un humano atiende, el bot queda pausado hasta este
    # instante (patron SalesBot). NULL = bot activo.
    bot_paused_until = Column(DateTime(timezone=True), nullable=True)

    # Modo de voz (reservado para F3-02: off|auto|mirror). Inerte en F2-03.
    voice_mode = Column(String(10), default="off")

    # Memoria larga (rolling summary): bullets de datos duros de turnos viejos +
    # id del ultimo mensaje ya resumido (para no re-resumir todo cada turno).
    rolling_summary_md = Column(Text, nullable=True)
    summary_up_to_message_id = Column(Integer, nullable=True)

    # Conversacion de muestra generada por el onboarding self-service (WO F5-03).
    # `contact_name` va prefijado "[DEMO]"; se borra en bloque sin tocar
    # conversaciones reales del inbox (regla #11 CLAUDE.md global).
    is_demo = Column(Boolean, nullable=False, default=False, index=True)

    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
