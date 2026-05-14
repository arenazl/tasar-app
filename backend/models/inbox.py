"""InboxMessage — Bandeja del tasador (inbox unificado).

Patrón Gmail/Inbox: lista de items con dot sin-leer + detalle al click.
Soporta múltiples kinds: mensaje de cliente, alerta de sistema, mención interna,
recordatorio propio, notificación de pago.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, func
from core.database import Base


class InboxMessage(Base):
    __tablename__ = "inbox_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    # A quién va dirigido (el dueño de la bandeja). NULL = todos del workspace
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Categorización
    kind = Column(String(40), nullable=False, index=True)
    # Valores: client_message | system_alert | user_mention | self_reminder |
    #          billing | overdue_task | appraisal_assigned | comparable_added
    sender_type = Column(String(40), default="user")  # user | system | client | billing
    sender_name = Column(String(200), nullable=True)   # ej "Mariana Sosa", "Sistema · Modelo"
    sender_subtitle = Column(String(200), nullable=True)  # ej "Banco Río Plata", "auto"
    avatar_color = Column(String(20), nullable=True)  # green | yellow | blue | orange | purple

    # Contenido
    subject = Column(String(250), nullable=False)
    preview = Column(String(500), nullable=True)  # 2 líneas para la lista
    body = Column(Text, nullable=True)             # cuerpo completo del mensaje

    # Referencias (al item al que apunta)
    related_appraisal_id = Column(Integer, ForeignKey("appraisals.id"), nullable=True, index=True)
    related_property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    related_url = Column(String(500), nullable=True)  # link interno arbitrario

    # Estado
    is_read = Column(Boolean, default=False, index=True)
    is_assigned_to_me = Column(Boolean, default=False, index=True)
    priority = Column(String(20), default="normal")  # urgent | high | normal | low

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)  # recordatorios futuros

    # Acciones disponibles (JSON list)
    actions = Column(Text, nullable=True)  # ej [{"label":"Responder","kind":"reply"}, ...]
