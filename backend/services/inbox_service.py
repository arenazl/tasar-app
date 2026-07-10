"""Producer de eventos de la Bandeja (WO F2-04).

UNICO productor de filas de `inbox_messages` (la Bandeja de TasAR). Antes la
Bandeja era 100% seed demo (12 filas fijas, sin ningun productor real); ahora los
eventos del sistema generan filas aca. El seed queda SOLO para el workspace demo.

Contrato de transaccion: `notify(...)` hace `db.add` + `flush` pero **NO commitea**
— corre DENTRO de la transaccion del caller (webhook del bot, tool del bot, o el
endpoint que firma/comenta) y se persiste con el commit de ese flujo. Cada llamada
esta pensada para envolverse en `try/except` por el caller (patron ya usado en la
casa para las notificaciones de email): un fallo del producer NUNCA debe romper el
flujo de negocio.

Scoping: `user_id` = destinatario del evento (NULL => todo el workspace). La Bandeja
(`api/inbox.py`) aplica el scoping por rol al LEER (vendedor ve lo suyo + lo del
workspace; supervisor/admin ven todo). Cada regla en UNA capa: el productor solo
decide a quien apunta, no filtra la lectura.

Los 5 tipos de evento cableados (kind -> origen):
  bot_lead         -> services/bot_tools.registrar_lead   (lead nuevo del bot)
  bot_visit        -> services/bot_tools.agendar_visita    (visita agendada por bot)
  bot_handoff      -> services/bot_tools.derivar_a_humano  (derivada sin tomar)
  appraisal_signed -> api/appraisals.sign_appraisal        (tasacion firmada)
  study_comment    -> api/collaboration.add_comment        (comentario en estudio)
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.inbox import InboxMessage

log = logging.getLogger("tasar.inbox_service")


async def notify(
    db: AsyncSession,
    *,
    workspace_id: int,
    kind: str,
    subject: str,
    user_id: Optional[int] = None,
    sender_type: str = "system",
    sender_name: Optional[str] = None,
    sender_subtitle: Optional[str] = None,
    avatar_color: Optional[str] = None,
    preview: Optional[str] = None,
    body: Optional[str] = None,
    priority: str = "normal",
    related_appraisal_id: Optional[int] = None,
    related_property_id: Optional[int] = None,
    related_url: Optional[str] = None,
) -> InboxMessage:
    """Crea (add+flush, sin commit) una fila de Bandeja scoped al workspace.

    Devuelve el InboxMessage ya con id (post-flush). No commitea: lo hace el caller.
    """
    msg = InboxMessage(
        workspace_id=workspace_id,
        user_id=user_id,
        kind=kind,
        sender_type=sender_type,
        sender_name=sender_name,
        sender_subtitle=sender_subtitle,
        avatar_color=avatar_color,
        subject=subject[:250],
        preview=(preview or "")[:500] or None,
        body=body,
        priority=priority,
        # user_id explicito => va dirigido a esa persona (se marca "asignado a mi"
        # para el que lo lee). NULL => es del workspace (no "asignado" a nadie).
        is_assigned_to_me=user_id is not None,
        related_appraisal_id=related_appraisal_id,
        related_property_id=related_property_id,
        related_url=related_url,
    )
    db.add(msg)
    await db.flush()
    return msg


# ── Helpers por tipo de evento (cada forma vive en UNA sola funcion) ────────

def _conv_link(conversation_id: int) -> str:
    """Deep-link a la conversacion de WhatsApp (patron AgentFlow: ?conv={id})."""
    return f"/whatsapp?conv={conversation_id}"


async def lead_created(
    db: AsyncSession,
    *,
    workspace_id: int,
    conversation_id: int,
    contact_name: Optional[str],
    phone: Optional[str],
    user_id: Optional[int] = None,
    interes: Optional[str] = None,
) -> InboxMessage:
    """Lead nuevo captado por el bot de WhatsApp."""
    who = contact_name or phone or "contacto WhatsApp"
    return await notify(
        db, workspace_id=workspace_id, user_id=user_id,
        kind="bot_lead", sender_type="system", sender_name="Bot WhatsApp",
        sender_subtitle="lead nuevo", avatar_color="green",
        subject=f"Lead nuevo: {who}",
        preview=interes or "El bot registró un lead nuevo desde WhatsApp.",
        priority="high",
        related_url=_conv_link(conversation_id),
    )


async def visit_scheduled(
    db: AsyncSession,
    *,
    workspace_id: int,
    conversation_id: int,
    user_id: Optional[int],
    property_title: str,
    when_label: str,
    client_name: Optional[str],
) -> InboxMessage:
    """Visita agendada por el bot (pendiente de confirmacion del asesor)."""
    return await notify(
        db, workspace_id=workspace_id, user_id=user_id,
        kind="bot_visit", sender_type="system", sender_name="Bot WhatsApp",
        sender_subtitle="visita agendada", avatar_color="blue",
        subject=f"Visita agendada: {property_title}",
        preview=f"{when_label} · {client_name or 'cliente'} — pendiente de confirmación.",
        priority="high",
        related_url=_conv_link(conversation_id),
    )


async def conversation_handoff(
    db: AsyncSession,
    *,
    workspace_id: int,
    conversation_id: int,
    user_id: Optional[int],
    contact_name: Optional[str],
    motivo: Optional[str] = None,
) -> InboxMessage:
    """Conversacion derivada por el bot a un humano, todavia SIN tomar."""
    who = contact_name or "contacto"
    return await notify(
        db, workspace_id=workspace_id, user_id=user_id,
        kind="bot_handoff", sender_type="system", sender_name="Bot WhatsApp",
        sender_subtitle="derivación", avatar_color="orange",
        subject=f"Derivación sin tomar: {who}",
        preview=(motivo or "El bot derivó la conversación a un asesor.") + " Tomá el mando para responder.",
        priority="urgent",
        related_url=_conv_link(conversation_id),
    )


async def appraisal_signed(
    db: AsyncSession,
    *,
    workspace_id: int,
    appraisal_id: int,
    signer_name: Optional[str],
    client_name: Optional[str],
    user_id: Optional[int] = None,
) -> InboxMessage:
    """Tasacion firmada (evento de workspace: user_id=None => lo ve el equipo)."""
    return await notify(
        db, workspace_id=workspace_id, user_id=user_id,
        kind="appraisal_signed", sender_type="system", sender_name=signer_name or "Sistema",
        sender_subtitle="firma", avatar_color="purple",
        subject=f"Tasación #{appraisal_id} firmada",
        preview=f"{signer_name or 'Un tasador'} firmó la tasación de {client_name or 'un cliente'}.",
        priority="normal",
        related_appraisal_id=appraisal_id,
        related_url=f"/tasaciones/{appraisal_id}",
    )


async def study_comment(
    db: AsyncSession,
    *,
    workspace_id: int,
    study_id: int,
    study_code: str,
    author_name: str,
    recipient_user_id: int,
    snippet: str,
) -> InboxMessage:
    """Comentario nuevo en un estudio (una fila POR destinatario colaborador)."""
    return await notify(
        db, workspace_id=workspace_id, user_id=recipient_user_id,
        kind="study_comment", sender_type="user", sender_name=author_name,
        sender_subtitle=study_code, avatar_color="blue",
        subject=f"Comentario en {study_code}",
        preview=snippet,
        body=snippet,
        priority="normal",
        related_url=f"/estudios/{study_id}",
    )
