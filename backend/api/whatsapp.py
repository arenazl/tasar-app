"""WhatsApp — webhook entrante + inbox + envio (WO F2-03).

UN solo webhook entrante (`POST /api/whatsapp/webhook/incoming`, auth X-API-Key ==
WA_GATEWAY_KEY, contrato de F0-05) y UN solo camino de salida (`_send_via_gateway`
-> `POST {WA_GATEWAY_URL}/send`). Todo scoped al workspace resuelto por el `tenant`
(slug) del payload.

Flujo del webhook:
  1. Idempotencia por meta_message_id (WhatsApp Multi-Device reentrega).
  2. Resolucion @lid -> PN normalizado.
  3. Ruteo al workspace por slug (anti-cross-tenant).
  4. Guarda el mensaje entrante.
  5. Coexistence: si hay assignee humano o el bot esta pausado -> NO responde el bot
     (lo maneja el humano desde el inbox). Si no, y el bot esta habilitado, corre el
     motor, envia la respuesta y, si deriva, manda el mensaje de derivación al cliente.

Inbox (JWT, scoped al workspace del usuario): listar/ver conversaciones, responder
(el humano toma la conv y pausa el bot 45'), marcar leidas, asignar/cerrar.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal, get_db
from core.security import get_current_user
from models.user import User
from models.client import Client
from models.workspace import Workspace
from models.conversation import (
    WaConversation, STATUS_NUEVA, STATUS_ABIERTA, STATUS_CERRADA, STATUS_BLOQUEADA,
)
from models.message import WaMessage, DIRECTION_INBOUND, DIRECTION_OUTBOUND
from models.bot_config import WorkspaceBotConfig
from services.bot_tools import BotContext, _phone_from_jid
from services.bot_engine import procesar_mensaje_entrante, render_message, _business_name


log = logging.getLogger("tasar.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Coexistence: cuando un humano responde, el bot se calla en esa conv por este lapso.
COEXISTENCE_PAUSE = timedelta(minutes=45)


# ── Camino UNICO de salida a WhatsApp (proxy al wa-gateway) ────────────────

async def _send_via_gateway(
    slug: str, telefono: str, contenido: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    """Envia un mensaje de texto por el gateway del workspace. (ok, meta_message_id, error)."""
    base = (settings.WA_GATEWAY_URL or "").rstrip("/")
    if not base or not settings.WA_GATEWAY_KEY:
        return (False, None, "wa-gateway no configurado")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{base}/send",
                json={"tenant": slug, "telefono": telefono, "contenido": contenido},
                headers={"X-API-Key": settings.WA_GATEWAY_KEY},
            )
            data = r.json()
            return (bool(data.get("ok")), data.get("meta_message_id"), data.get("error"))
    except Exception as e:  # noqa: BLE001
        return (False, None, str(e))


def _make_sender(slug: str):
    """Sender ligado al workspace para las tools (notificacion a vendedores)."""
    async def _send(phone_or_jid: str, text: str) -> None:
        await _send_via_gateway(slug, phone_or_jid, text)
    return _send


# ── Webhook entrante ────────────────────────────────────────────────────────

class IncomingPayload(BaseModel):
    tenant: str
    telefono: str                      # JID del contacto
    phone_publico: Optional[str] = None
    nombre_contacto: Optional[str] = None
    contenido: str = ""
    tipo: str = "text"
    media_url: Optional[str] = None
    meta_message_id: Optional[str] = None
    timestamp: Optional[float] = None


def _check_gateway_key(x_api_key: Optional[str]) -> None:
    if not settings.WA_GATEWAY_KEY:
        raise HTTPException(503, "WA_GATEWAY_KEY no configurada")
    if x_api_key != settings.WA_GATEWAY_KEY:
        raise HTTPException(401, "API key invalida")


async def _persist_bot_message(
    db: AsyncSession, conv: WaConversation, text: str, meta_id: Optional[str],
) -> None:
    db.add(WaMessage(
        conversation_id=conv.id, direction=DIRECTION_OUTBOUND, type="text",
        content=text, sender_id=None, is_read=True, meta_message_id=meta_id,
    ))


@router.post("/webhook/incoming")
async def webhook_incoming(
    payload: IncomingPayload,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_gateway_key(x_api_key)

    # 1. Idempotencia.
    if payload.meta_message_id:
        dup = (await db.execute(
            select(WaMessage.id).where(WaMessage.meta_message_id == payload.meta_message_id)
        )).first()
        if dup:
            return {"ok": True, "duplicate": True, "meta_message_id": payload.meta_message_id}

    # 2. Ruteo al workspace por slug (anti-cross-tenant).
    ws = (await db.execute(
        select(Workspace).where(Workspace.slug == payload.tenant)
    )).scalar_one_or_none()
    if not ws:
        raise HTTPException(404, f"Workspace (tenant) desconocido: {payload.tenant}")

    now = datetime.now(timezone.utc)
    contact_pn = _phone_from_jid(payload.telefono)

    # 3. Buscar/crear conversacion por (workspace, JID); si no, por PN normalizado.
    conv = (await db.execute(
        select(WaConversation).where(
            WaConversation.workspace_id == ws.id,
            WaConversation.phone_jid == payload.telefono,
        )
    )).scalar_one_or_none()
    if not conv and contact_pn:
        conv = (await db.execute(
            select(WaConversation).where(
                WaConversation.workspace_id == ws.id,
                WaConversation.phone_jid == contact_pn,
            )
        )).scalar_one_or_none()
        if conv:
            conv.phone_jid = payload.telefono  # normalizar al JID real

    if not conv:
        # Vincular con un cliente del workspace si matchea por telefono.
        cli = None
        if contact_pn:
            cli = (await db.execute(
                select(Client).where(Client.workspace_id == ws.id, Client.phone == contact_pn)
            )).scalar_one_or_none()
        conv = WaConversation(
            workspace_id=ws.id,
            phone_jid=payload.telefono,
            phone_public=payload.phone_publico,
            contact_name=payload.nombre_contacto,
            client_id=cli.id if cli else None,
            status=STATUS_NUEVA,
            unread_count=0,
            last_activity_at=now,
        )
        db.add(conv)
        await db.flush()

    # 4. Guardar el mensaje entrante.
    content = payload.contenido
    if payload.tipo == "audio" and payload.media_url:
        # La transcripcion de audio es de F3 (voice). Por ahora se guarda la referencia.
        content = content or "[audio]"
    inbound = WaMessage(
        conversation_id=conv.id,
        direction=DIRECTION_INBOUND,
        type=payload.tipo or "text",
        content=content,
        media_url=payload.media_url,
        meta_message_id=payload.meta_message_id,
        is_read=False,
    )
    db.add(inbound)
    conv.last_activity_at = now
    conv.unread_count = (conv.unread_count or 0) + 1
    if payload.nombre_contacto and not conv.contact_name:
        conv.contact_name = payload.nombre_contacto
    await db.flush()

    # 5. Coexistence: no responde el bot si hay humano asignado, esta bloqueada, o pausado.
    bot_paused = conv.bot_paused_until is not None and _aware(conv.bot_paused_until) > now
    if conv.assignee_id is not None or conv.status == STATUS_BLOQUEADA or bot_paused:
        await db.commit()
        return {"ok": True, "conversation_id": conv.id, "bot": "skipped"}

    cfg = (await db.execute(
        select(WorkspaceBotConfig).where(WorkspaceBotConfig.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not cfg or not cfg.enabled:
        await db.commit()
        return {"ok": True, "conversation_id": conv.id, "bot": "disabled"}

    # Correr el motor del bot.
    ctx = BotContext(
        db=db, workspace_id=ws.id, workspace_slug=ws.slug, workspace_name=ws.name,
        conversation=conv, bot_config=cfg, send=_make_sender(ws.slug),
    )
    bot_text, action = await procesar_mensaje_entrante(ctx, inbound)

    if bot_text:
        ok, meta_id, _err = await _send_via_gateway(ws.slug, conv.phone_jid, bot_text)
        await _persist_bot_message(db, conv, bot_text, meta_id or _local_id("bot"))

    # Derivacion: mandar al cliente el mensaje de derivación configurado (rendereado).
    if action == "derivar":
        negocio = _business_name(cfg, ws.name)
        deriv_msg = render_message(cfg.derivation_message, negocio)
        if deriv_msg:
            ok, meta_id, _err = await _send_via_gateway(ws.slug, conv.phone_jid, deriv_msg)
            await _persist_bot_message(db, conv, deriv_msg, meta_id or _local_id("handoff"))

    await db.commit()
    return {"ok": True, "conversation_id": conv.id, "bot": "responded", "action": action}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _local_id(prefix: str) -> str:
    return f"{prefix}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"


# ── Inbox (JWT, scoped al workspace del usuario) ───────────────────────────

def _conv_dict(c: WaConversation, last: Optional[WaMessage] = None) -> dict:
    d = {
        "id": c.id,
        "phone_jid": c.phone_jid,
        "contact_name": c.contact_name,
        "client_id": c.client_id,
        "assignee_id": c.assignee_id,
        "status": c.status,
        "unread_count": c.unread_count,
        "bot_paused_until": c.bot_paused_until.isoformat() if c.bot_paused_until else None,
        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
    }
    if last:
        d["last_message"] = (last.content or "")[:200]
        d["last_direction"] = last.direction
    return d


@router.get("/conversations")
async def list_conversations(
    status: Optional[str] = Query(None),
    only_mine: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = [WaConversation.workspace_id == user.workspace_id]
    if status:
        filters.append(WaConversation.status == status)
    if only_mine:
        filters.append(WaConversation.assignee_id == user.id)
    convs = (await db.execute(
        select(WaConversation).where(and_(*filters)).order_by(desc(WaConversation.last_activity_at)).limit(200)
    )).scalars().all()
    out = []
    for c in convs:
        last = (await db.execute(
            select(WaMessage).where(WaMessage.conversation_id == c.id)
            .order_by(desc(WaMessage.created_at)).limit(1)
        )).scalar_one_or_none()
        out.append(_conv_dict(c, last))
    return out


async def _get_conv_scoped(db: AsyncSession, conv_id: int, user: User) -> WaConversation:
    c = (await db.execute(
        select(WaConversation).where(
            WaConversation.id == conv_id, WaConversation.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Conversación no encontrada")
    return c


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await _get_conv_scoped(db, conv_id, user)
    msgs = (await db.execute(
        select(WaMessage).where(WaMessage.conversation_id == c.id).order_by(WaMessage.created_at.asc())
    )).scalars().all()
    d = _conv_dict(c)
    d["messages"] = [
        {
            "id": m.id, "direction": m.direction, "type": m.type, "content": m.content,
            "media_url": m.media_url, "sender_id": m.sender_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
    return d


class SendBody(BaseModel):
    contenido: str


@router.post("/conversations/{conv_id}/send")
async def send_message(
    conv_id: int,
    body: SendBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """El humano responde: envia por el gateway, toma la conv y PAUSA el bot 45'
    (coexistence, patron SalesBot)."""
    c = await _get_conv_scoped(db, conv_id, user)
    ws = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalar_one()

    ok, meta_id, err = await _send_via_gateway(ws.slug, c.phone_jid, body.contenido)
    db.add(WaMessage(
        conversation_id=c.id, direction=DIRECTION_OUTBOUND, type="text",
        content=body.contenido, sender_id=user.id, is_read=True,
        meta_message_id=meta_id or _local_id(f"u{user.id}"),
    ))
    if c.assignee_id is None:
        c.assignee_id = user.id
    if c.status == STATUS_NUEVA:
        c.status = STATUS_ABIERTA
    c.bot_paused_until = datetime.now(timezone.utc) + COEXISTENCE_PAUSE
    c.last_activity_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "sent_via_gateway": ok, "error": err}


@router.post("/conversations/{conv_id}/mark-read")
async def mark_read(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await _get_conv_scoped(db, conv_id, user)
    await db.execute(
        update(WaMessage)
        .where(and_(WaMessage.conversation_id == c.id, WaMessage.direction == DIRECTION_INBOUND, WaMessage.is_read == False))  # noqa: E712
        .values(is_read=True)
    )
    c.unread_count = 0
    await db.commit()
    return {"ok": True}


class ConvUpdate(BaseModel):
    assignee_id: Optional[int] = None
    status: Optional[str] = None
    client_id: Optional[int] = None


@router.patch("/conversations/{conv_id}")
async def update_conversation(
    conv_id: int,
    body: ConvUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = await _get_conv_scoped(db, conv_id, user)
    data = body.model_dump(exclude_unset=True)
    if "assignee_id" in data:
        c.assignee_id = data["assignee_id"]
        if c.assignee_id is not None and c.status == STATUS_NUEVA:
            c.status = STATUS_ABIERTA
    if "status" in data and data["status"]:
        if data["status"] not in (STATUS_NUEVA, STATUS_ABIERTA, STATUS_CERRADA, STATUS_BLOQUEADA):
            raise HTTPException(400, "status inválido")
        c.status = data["status"]
    if "client_id" in data:
        c.client_id = data["client_id"]
    await db.commit()
    return _conv_dict(c)
