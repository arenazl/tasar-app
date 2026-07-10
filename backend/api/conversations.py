"""Inbox humano de WhatsApp — conversaciones (WO F2-04).

La bandeja OPERATIVA del equipo sobre las conversaciones de WhatsApp: listar con
filtros, ver el historial, TOMAR el mando (asignarme + pausar el bot), responder
como operador por el gateway, reactivar el bot y vincular a un cliente del CRM.

Convive con:
  - `api/whatsapp.py`  -> webhook entrante + `_send_via_gateway` (camino UNICO de
    salida a WhatsApp; se reutiliza aca, NO se duplica).
  - `api/inbox.py`     -> Bandeja de EVENTOS (inbox_messages). Otra cosa: esto es el
    chat de WhatsApp; aquello son las notificaciones del sistema.

Scoping (multi-tenant + rol):
  - Siempre `workspace_id == user.workspace_id` (anti cross-tenant).
  - vendedor: ve lo SUYO (assignee == el) + lo SIN asignar (para poder tomarlo).
  - supervisor/admin: ven TODO el workspace.

Anti N+1: el "ultimo mensaje" de cada conversacion sale en la MISMA query del list
(subquery de max(id) por conversacion + join), no una query por fila como hacian el
list de AgentFlow y el de SalesBot. El unread ya vive denormalizado en la conv.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.workspace import Workspace
from models.client import Client
from models.conversation import (
    WaConversation, STATUS_NUEVA, STATUS_ABIERTA, STATUS_CERRADA, STATUS_BLOQUEADA,
)
from models.message import WaMessage, DIRECTION_INBOUND, DIRECTION_OUTBOUND
from services.cloudinary_service import upload_audio
# Camino UNICO de salida + pausa de coexistence (definidos en el modulo del webhook;
# NO se duplican aca para no tener dos rutas de envio ni dos constantes de pausa).
from api.whatsapp import _send_via_gateway, _local_id, COEXISTENCE_PAUSE

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

_VALID_STATUS = {STATUS_NUEVA, STATUS_ABIERTA, STATUS_CERRADA, STATUS_BLOQUEADA}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _role_filter(user: User):
    """Predicado de scoping por rol para el WHERE del list/get."""
    if user.role in ("supervisor", "admin"):
        return None
    # vendedor: lo suyo + lo sin asignar (nuevas que puede tomar).
    return or_(WaConversation.assignee_id == user.id, WaConversation.assignee_id.is_(None))


def _conv_row(c: WaConversation, last: Optional[WaMessage], assignee_name: Optional[str]) -> dict:
    return {
        "id": c.id,
        "phone_jid": c.phone_jid,
        "contact_name": c.contact_name,
        "client_id": c.client_id,
        "assignee_id": c.assignee_id,
        "assignee_name": assignee_name,
        "status": c.status,
        "unread_count": c.unread_count or 0,
        "bot_paused_until": _aware(c.bot_paused_until).isoformat() if c.bot_paused_until else None,
        "bot_paused": bool(c.bot_paused_until and _aware(c.bot_paused_until) > _now()),
        "voice_mode": c.voice_mode,
        "last_activity_at": _aware(c.last_activity_at).isoformat() if c.last_activity_at else None,
        "last_message": (last.content or "")[:200] if last else None,
        "last_direction": last.direction if last else None,
    }


@router.get("")
async def list_conversations(
    filter: str = Query("todas"),           # todas | mias | nuevas | sin_asignar
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista scoped por workspace+rol. UNA query (conv + ultimo mensaje + assignee)."""
    filters = [WaConversation.workspace_id == user.workspace_id]
    role_pred = _role_filter(user)
    if role_pred is not None:
        filters.append(role_pred)

    if filter == "mias":
        filters.append(WaConversation.assignee_id == user.id)
    elif filter == "nuevas":
        filters.append(WaConversation.status == STATUS_NUEVA)
    elif filter == "sin_asignar":
        filters.append(WaConversation.assignee_id.is_(None))
    if status:
        filters.append(WaConversation.status == status)
    if q:
        like = f"%{q}%"
        filters.append(or_(
            WaConversation.contact_name.ilike(like),
            WaConversation.phone_jid.ilike(like),
        ))

    # Subquery: id del ultimo mensaje por conversacion (max(id) ~ mas reciente, el
    # id es autoincrement). Evita el N+1 de traer el ultimo mensaje fila por fila.
    last_sq = (
        select(
            WaMessage.conversation_id.label("cid"),
            func.max(WaMessage.id).label("mid"),
        )
        .group_by(WaMessage.conversation_id)
        .subquery()
    )
    Assignee = User  # alias semantico
    stmt = (
        select(WaConversation, WaMessage, Assignee.full_name)
        .outerjoin(last_sq, last_sq.c.cid == WaConversation.id)
        .outerjoin(WaMessage, WaMessage.id == last_sq.c.mid)
        .outerjoin(Assignee, Assignee.id == WaConversation.assignee_id)
        .where(and_(*filters))
        .order_by(desc(WaConversation.last_activity_at))
        .limit(200)
    )
    rows = (await db.execute(stmt)).all()
    return [_conv_row(c, last, name) for (c, last, name) in rows]


@router.get("/assignees")
async def list_assignees(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Usuarios del workspace asignables (para el desplegable de reasignacion)."""
    rows = (await db.execute(
        select(User.id, User.full_name, User.role)
        .where(
            User.workspace_id == user.workspace_id,
            User.is_active == True,  # noqa: E712
            User.role.in_(["vendedor", "supervisor", "admin"]),
        )
        .order_by(User.full_name.asc())
    )).all()
    return [{"id": r.id, "full_name": r.full_name, "role": r.role} for r in rows]


async def _get_scoped(db: AsyncSession, conv_id: int, user: User) -> WaConversation:
    filters = [WaConversation.id == conv_id, WaConversation.workspace_id == user.workspace_id]
    role_pred = _role_filter(user)
    if role_pred is not None:
        filters.append(role_pred)
    c = (await db.execute(select(WaConversation).where(and_(*filters)))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Conversación no encontrada")
    return c


@router.get("/{conv_id}")
async def get_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await _get_scoped(db, conv_id, user)
    assignee_name = None
    if c.assignee_id:
        assignee_name = (await db.execute(
            select(User.full_name).where(User.id == c.assignee_id)
        )).scalar_one_or_none()
    msgs = (await db.execute(
        select(WaMessage).where(WaMessage.conversation_id == c.id).order_by(WaMessage.created_at.asc())
    )).scalars().all()
    d = _conv_row(c, msgs[-1] if msgs else None, assignee_name)
    d["messages"] = [
        {
            "id": m.id, "direction": m.direction, "type": m.type, "content": m.content,
            "media_url": m.media_url, "sender_id": m.sender_id,
            "created_at": _aware(m.created_at).isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
    return d


class ReplyBody(BaseModel):
    contenido: str


def _take_control(c: WaConversation, user: User) -> None:
    """Tomar el mando + pausar el bot (coexistence). Compartido por `reply`
    (texto) y `reply_audio` (nota de voz, WO F3-01) -- una sola regla, un
    solo lugar; no se duplica por canal."""
    if c.assignee_id is None:
        c.assignee_id = user.id
    if c.status == STATUS_NUEVA:
        c.status = STATUS_ABIERTA
    c.bot_paused_until = _now() + COEXISTENCE_PAUSE
    c.last_activity_at = _now()


@router.post("/{conv_id}/reply")
async def reply(
    conv_id: int,
    body: ReplyBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """El operador responde: sale por el gateway, TOMA la conv y PAUSA el bot.

    Herencia de la decision de SalesBot (`conversaciones.py:420-422`): el
    `sender_name` NO se antepone al texto de WhatsApp (algunos clientes lo rompian);
    queda solo como metadato de UI via `sender_id`. Reutiliza el mecanismo
    `bot_paused_until` de F2-03 para la pausa de coexistence (no se inventa otro).
    """
    contenido = (body.contenido or "").strip()
    if not contenido:
        raise HTTPException(400, "Mensaje vacío")
    c = await _get_scoped(db, conv_id, user)
    if c.status == STATUS_BLOQUEADA:
        raise HTTPException(400, "Conversación bloqueada")
    ws = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalar_one()

    ok, meta_id, err = await _send_via_gateway(ws.slug, c.phone_jid, contenido)
    db.add(WaMessage(
        conversation_id=c.id, direction=DIRECTION_OUTBOUND, type="text",
        content=contenido, sender_id=user.id, is_read=True,
        meta_message_id=meta_id or _local_id(f"u{user.id}"),
    ))
    _take_control(c, user)
    await db.commit()
    return {"ok": True, "sent_via_gateway": ok, "error": err}


@router.post("/{conv_id}/reply-audio")
async def reply_audio(
    conv_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Nota de voz grabada por el vendedor desde el Inbox (press-and-hold en
    `InboxWhatsApp.tsx`, WO F3-01). Va TAL CUAL la grabo el vendedor -- SIN
    TTS ni sanitizador de <<PAUSE>>/URLs (eso es solo para audio SINTETIZADO
    del bot, ver `services.audio_out`): se sube a Cloudinary y sale por el
    MISMO camino unico de envio (`_send_via_gateway`, con audio_url), tal
    como el reply de texto.
    """
    c = await _get_scoped(db, conv_id, user)
    if c.status == STATUS_BLOQUEADA:
        raise HTTPException(400, "Conversación bloqueada")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Audio vacío")
    ws = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalar_one()

    up = await upload_audio(raw, folder="wa-audio")
    media_url = up.get("url")
    if not media_url:
        raise HTTPException(502, "No se pudo subir el audio")

    ok, meta_id, err = await _send_via_gateway(ws.slug, c.phone_jid, audio_url=media_url, ptt=True)
    db.add(WaMessage(
        conversation_id=c.id, direction=DIRECTION_OUTBOUND, type="audio",
        media_url=media_url, sender_id=user.id, is_read=True,
        meta_message_id=meta_id or _local_id(f"u{user.id}"),
    ))
    _take_control(c, user)
    await db.commit()
    return {"ok": True, "sent_via_gateway": ok, "error": err, "media_url": media_url}


@router.post("/{conv_id}/assign-me")
async def assign_me(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Tomar el mando sin responder todavia: me asigno la conv y pauso el bot."""
    c = await _get_scoped(db, conv_id, user)
    c.assignee_id = user.id
    if c.status == STATUS_NUEVA:
        c.status = STATUS_ABIERTA
    c.bot_paused_until = _now() + COEXISTENCE_PAUSE
    await db.commit()
    return {"ok": True, "assignee_id": user.id, "bot_paused_until": c.bot_paused_until.isoformat()}


@router.post("/{conv_id}/reactivate-bot")
async def reactivate_bot(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Levanta la pausa del bot (bot_paused_until -> NULL) para que vuelva a atender."""
    c = await _get_scoped(db, conv_id, user)
    c.bot_paused_until = None
    await db.commit()
    return {"ok": True, "bot_paused_until": None}


@router.post("/{conv_id}/mark-read")
async def mark_read(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import update
    c = await _get_scoped(db, conv_id, user)
    await db.execute(
        update(WaMessage)
        .where(and_(
            WaMessage.conversation_id == c.id,
            WaMessage.direction == DIRECTION_INBOUND,
            WaMessage.is_read == False,  # noqa: E712
        ))
        .values(is_read=True)
    )
    c.unread_count = 0
    await db.commit()
    return {"ok": True}


_VALID_VOICE_MODES = {"off", "auto", "mirror"}


class ConvUpdate(BaseModel):
    assignee_id: Optional[int] = None
    status: Optional[str] = None
    client_id: Optional[int] = None
    # Override de voice_mode SOLO de esta conversación (WO F3-01). None/ausente
    # -> hereda bot_config.default_voice_mode del workspace.
    voice_mode: Optional[str] = None


@router.patch("/{conv_id}")
async def update_conversation(
    conv_id: int,
    body: ConvUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reasignar / cambiar estado / vincular cliente.

    Reasignar a OTRA persona es solo de supervisor/admin; un vendedor solo puede
    tomar/soltar la conv (asignarse a si mismo o desasignar).
    """
    c = await _get_scoped(db, conv_id, user)
    data = body.model_dump(exclude_unset=True)

    if "assignee_id" in data:
        target = data["assignee_id"]
        if user.role == "vendedor" and target not in (None, user.id):
            raise HTTPException(403, "Un vendedor solo puede tomar o soltar la conversación")
        if target is not None:
            valid = (await db.execute(
                select(User.id).where(User.id == target, User.workspace_id == user.workspace_id)
            )).scalar_one_or_none()
            if not valid:
                raise HTTPException(404, "Usuario inexistente en el workspace")
        c.assignee_id = target
        if target is not None and c.status == STATUS_NUEVA:
            c.status = STATUS_ABIERTA

    if "status" in data and data["status"]:
        if data["status"] not in _VALID_STATUS:
            raise HTTPException(400, "status inválido")
        c.status = data["status"]

    if "client_id" in data:
        cid = data["client_id"]
        if cid is not None:
            valid = (await db.execute(
                select(Client.id).where(Client.id == cid, Client.workspace_id == user.workspace_id)
            )).scalar_one_or_none()
            if not valid:
                raise HTTPException(404, "Cliente inexistente en el workspace")
        c.client_id = cid

    if "voice_mode" in data:
        vm = data["voice_mode"]
        if vm is not None and vm not in _VALID_VOICE_MODES:
            raise HTTPException(400, "voice_mode inválido (off|auto|mirror)")
        c.voice_mode = vm

    await db.commit()
    assignee_name = None
    if c.assignee_id:
        assignee_name = (await db.execute(
            select(User.full_name).where(User.id == c.assignee_id)
        )).scalar_one_or_none()
    return _conv_row(c, None, assignee_name)
