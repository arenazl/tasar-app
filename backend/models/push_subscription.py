"""PushSubscription — suscripciones Web Push de los usuarios (WO F3-03).

Portado de AgentFlow (backend/models/push_subscription.py), adaptado a la
suite multi-tenant: se agrega `workspace_id` (misma convencion que el resto
de las tablas nuevas desde F1-01 -- "toda tabla nueva lleva workspace_id").
Notifica eventos clave (lead nuevo, derivacion sin tomar, visita agendada)
aunque el usuario tenga la PWA cerrada -- ver services/push_notif.py y el
cableo en services/bot_tools._emit_inbox_event.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from core.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Datos del PushSubscription del navegador (PushManager.subscribe())
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(200), nullable=False)
    auth = Column(String(100), nullable=False)

    # Metadata util
    user_agent = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
