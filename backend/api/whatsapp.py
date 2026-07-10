"""WhatsApp — webhook entrante + inbox + envio (WO F2-03, audio en F3-01).

UN solo webhook entrante (`POST /api/whatsapp/webhook/incoming`, auth X-API-Key ==
WA_GATEWAY_KEY, contrato de F0-05) y UN solo camino de salida (`_send_via_gateway`
-> `POST {WA_GATEWAY_URL}/send`). Todo scoped al workspace resuelto por el `tenant`
(slug) del payload.

`_send_via_gateway` es el UNICO camino de salida tanto para texto como para
audio (params `audio_url`/`ptt` opcionales) — regla de la casa "un solo camino
de salida de audio". La generacion del audio (TTS + sanitizado de <<PAUSE>>/URLs)
vive aparte en `services.audio_out` (WO F3-01); este modulo solo lo LLAMA y
manda el resultado por el mismo POST /send de siempre.

Flujo del webhook:
  1. Idempotencia por meta_message_id (WhatsApp Multi-Device reentrega).
  2. Resolucion @lid -> PN normalizado.
  3. Ruteo al workspace por slug (anti-cross-tenant).
  4. Guarda el mensaje entrante. Si es audio, lo transcribe con Groq Whisper
     (F3-01) y guarda la transcripcion en `WaMessage.transcription`.
  5. Coexistence: si hay assignee humano o el bot esta pausado -> NO responde el bot
     (lo maneja el humano desde el inbox). Si no, y el bot esta habilitado, corre el
     motor, decide si responde en audio (`voice_mode` de la conv, default del
     workspace) y envia la respuesta; si deriva, manda el mensaje de derivación.

El inbox HUMANO (listar/ver/responder/tomar mando/reactivar) vive en
`api/conversations.py` (WO F2-04) y reutiliza de aca el camino UNICO de salida
(`_send_via_gateway`), la constante de pausa de coexistence (`COEXISTENCE_PAUSE`)
y el generador de id local (`_local_id`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.client import Client
from models.workspace import Workspace
from models.conversation import WaConversation, STATUS_NUEVA, STATUS_BLOQUEADA
from models.message import WaMessage, DIRECTION_INBOUND, DIRECTION_OUTBOUND
from models.bot_config import WorkspaceBotConfig
from services.bot_tools import BotContext, _phone_from_jid
from services.bot_engine import procesar_mensaje_entrante, render_message, _business_name
from services.transcribe import transcribe_audio_from_url
from services.audio_out import synthesize_reply_audio, quiere_audio


log = logging.getLogger("tasar.whatsapp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Coexistence: cuando un humano responde, el bot se calla en esa conv por este lapso.
COEXISTENCE_PAUSE = timedelta(minutes=45)


# ── Camino UNICO de salida a WhatsApp (proxy al wa-gateway) ────────────────

async def _send_via_gateway(
    slug: str, telefono: str, contenido: str = "",
    audio_url: Optional[str] = None, ptt: bool = True,
) -> tuple[bool, Optional[str], Optional[str]]:
    """Envia un mensaje por el gateway del workspace: texto, o audio (ptt) +
    opcionalmente un texto aparte (ej. URLs que se cortaron antes del TTS).

    UNICO camino de salida a WhatsApp -- texto Y audio pasan por aca, nunca
    por un POST /send separado. (ok, meta_message_id, error).
    """
    base = (settings.WA_GATEWAY_URL or "").rstrip("/")
    if not base or not settings.WA_GATEWAY_KEY:
        return (False, None, "wa-gateway no configurado")
    payload: dict = {"tenant": slug, "telefono": telefono, "contenido": contenido}
    if audio_url:
        payload["audio_url"] = audio_url
        payload["ptt"] = ptt
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{base}/send",
                json=payload,
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
    media_url: Optional[str] = None, msg_type: str = "text",
) -> None:
    db.add(WaMessage(
        conversation_id=conv.id, direction=DIRECTION_OUTBOUND, type=msg_type,
        content=text, media_url=media_url, sender_id=None, is_read=True, meta_message_id=meta_id,
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

    # 4. Guardar el mensaje entrante. Si es audio, transcribir con Groq Whisper
    # (WO F3-01) -- best-effort: si falla o no esta configurado, el bot recibe
    # el placeholder "[audio]" (ver bot_engine._msg_text) y no rompe el webhook.
    content = payload.contenido
    transcription: Optional[str] = None
    if payload.tipo == "audio" and payload.media_url:
        transcription = await transcribe_audio_from_url(payload.media_url)
        if not content:
            content = "[audio]"
    inbound = WaMessage(
        conversation_id=conv.id,
        direction=DIRECTION_INBOUND,
        type=payload.tipo or "text",
        content=content,
        media_url=payload.media_url,
        transcription=transcription,
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
        # Audio saliente (WO F3-01): decide segun voice_mode efectivo de la
        # conv (override) / bot_config.default_voice_mode (default del
        # workspace). Si el TTS falla por lo que sea, media_url da None y cae
        # a texto sin romper el envio (audio_out.synthesize_reply_audio nunca
        # levanta excepcion).
        media_url = None
        urls_aparte = ""
        if quiere_audio(conv.voice_mode, cfg.default_voice_mode, payload.tipo):
            media_url, urls_aparte = await synthesize_reply_audio(bot_text, voice_id=cfg.voice_id)
        if media_url:
            ok, meta_id, _err = await _send_via_gateway(
                ws.slug, conv.phone_jid, contenido=urls_aparte, audio_url=media_url,
            )
            await _persist_bot_message(db, conv, bot_text, meta_id or _local_id("bot"), media_url=media_url, msg_type="audio")
        else:
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
