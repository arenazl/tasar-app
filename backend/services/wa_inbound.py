"""Pipeline UNICO de mensajes entrantes de WhatsApp — Baileys y Meta (WO F3-02).

Cada webhook de canal (`api/whatsapp.py` para Baileys, `api/meta.py` para Meta
Cloud API oficial) resuelve el workspace por SU propio mecanismo (slug del
`tenant` vs `meta_phone_number_id`) y arma el MISMO `IncomingPayload`; a partir
de ahí TODO pasa por `process_incoming` — dedup, conversación, persistencia,
transcripción, coexistence (humano/bot pausado), motor del bot y el envío de
la respuesta (vía `services.wa_out`, que resuelve baileys|meta por
`workspace_bot_config.channel_provider`). Ningún otro lugar del código duplica
este pipeline — regla de la casa "cada regla en una capa".

Extraído de `api/whatsapp.py` (WO F2-03/F2-04/F3-01) al nacer el canal Meta
(F3-02): el `IncomingPayload` y todo el cuerpo de `webhook_incoming` desde la
resolución del workspace en adelante vivían ahí; ahora es compartido.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.client import Client
from models.workspace import Workspace
from models.conversation import WaConversation, STATUS_NUEVA, STATUS_BLOQUEADA
from models.message import WaMessage, DIRECTION_INBOUND, DIRECTION_OUTBOUND
from models.bot_config import WorkspaceBotConfig
from services.bot_tools import BotContext, _phone_from_jid
from services.bot_engine import procesar_mensaje_entrante, render_message, _business_name
from services.transcribe import transcribe_audio_from_url
from services.audio_out import synthesize_reply_audio, quiere_audio
from services import wa_out


# Coexistence: mientras un humano atiende (desde el Inbox, o -- canal Meta,
# best-effort -- desde el teléfono vía Coexistence), el bot queda pausado en
# esa conv por este lapso. Patrón SalesBot (`gupshup.py`, COEX_PAUSE_MINUTES).
COEXISTENCE_PAUSE = timedelta(minutes=45)


class IncomingPayload(BaseModel):
    """Payload interno ÚNICO al que normalizan los dos canales antes de entrar
    a `process_incoming`. Baileys lo recibe casi tal cual del gateway (WO
    F0-05/F2-03); Meta lo arma `api/meta.py` a partir del webhook oficial
    (`meta_client.parse_incoming_payload` + resolución de media a URL pública).
    """
    tenant: str
    telefono: str                      # JID del contacto
    phone_publico: Optional[str] = None
    nombre_contacto: Optional[str] = None
    contenido: str = ""
    tipo: str = "text"
    media_url: Optional[str] = None
    meta_message_id: Optional[str] = None
    timestamp: Optional[float] = None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _local_id(prefix: str) -> str:
    return f"{prefix}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"


def _make_sender(ws: Workspace, cfg: Optional[WorkspaceBotConfig]):
    """Sender ligado al workspace para las tools (notificación a vendedores).
    Pasa SIEMPRE por `wa_out.send` -- nunca golpea el gateway/Graph API directo,
    ni decide `channel_provider` acá (esa decisión vive únicamente en wa_out)."""
    async def _send(phone_or_jid: str, text: str) -> None:
        await wa_out.send(ws, cfg, phone_or_jid, text)
    return _send


async def _persist_bot_message(
    db: AsyncSession, conv: WaConversation, text: str, meta_id: Optional[str],
    media_url: Optional[str] = None, msg_type: str = "text",
) -> None:
    db.add(WaMessage(
        conversation_id=conv.id, direction=DIRECTION_OUTBOUND, type=msg_type,
        content=text, media_url=media_url, sender_id=None, is_read=True, meta_message_id=meta_id,
    ))


async def process_incoming(
    db: AsyncSession, ws: Workspace, cfg: Optional[WorkspaceBotConfig], payload: IncomingPayload,
) -> dict:
    """Procesa un mensaje entrante YA normalizado y con el workspace YA
    resuelto (por tenant/slug en Baileys, por meta_phone_number_id en Meta).
    Devuelve el mismo shape de dict que devolvía `webhook_incoming` original
    (ok/modo/conversation_id/bot/action)."""
    # 1. Idempotencia (Baileys reentrega por Multi-Device; Meta reintenta el
    #    webhook si no respondemos < 20s) -- mismo meta_message_id.
    if payload.meta_message_id:
        dup = (await db.execute(
            select(WaMessage.id).where(WaMessage.meta_message_id == payload.meta_message_id)
        )).first()
        if dup:
            return {"ok": True, "duplicate": True, "meta_message_id": payload.meta_message_id}

    now = datetime.now(timezone.utc)
    contact_pn = _phone_from_jid(payload.telefono)

    # 2. Buscar/crear conversación por (workspace, JID); si no, por PN normalizado.
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

    # 3. Guardar el mensaje entrante. Si es audio, transcribir con Groq Whisper
    # (WO F3-01) -- best-effort: si falla o no está configurado, el bot recibe
    # el placeholder "[audio]" y no rompe el webhook. `media_url` ya llega como
    # URL pública descargable en los dos canales (Baileys la da directa; Meta
    # la resuelve `api/meta.py` bajando el media_id y subiéndolo a Cloudinary
    # antes de armar este payload) -- este paso es 100% agnóstico del canal.
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

    # 4. Coexistence: no responde el bot si hay humano asignado, está bloqueada, o pausado.
    bot_paused = conv.bot_paused_until is not None and _aware(conv.bot_paused_until) > now
    if conv.assignee_id is not None or conv.status == STATUS_BLOQUEADA or bot_paused:
        await db.commit()
        return {"ok": True, "conversation_id": conv.id, "bot": "skipped"}

    if not cfg or not cfg.enabled:
        await db.commit()
        return {"ok": True, "conversation_id": conv.id, "bot": "disabled"}

    # 5. Correr el motor del bot.
    ctx = BotContext(
        db=db, workspace_id=ws.id, workspace_slug=ws.slug, workspace_name=ws.name,
        conversation=conv, bot_config=cfg, send=_make_sender(ws, cfg),
    )
    bot_text, action = await procesar_mensaje_entrante(ctx, inbound)

    if bot_text:
        # Audio saliente (WO F3-01): decide según voice_mode efectivo de la
        # conv (override) / bot_config.default_voice_mode (default del
        # workspace). Si el TTS falla, media_url da None y cae a texto sin
        # romper el envío (audio_out.synthesize_reply_audio nunca levanta
        # excepción). El envío en sí (texto o audio) pasa por wa_out.send,
        # que resuelve baileys|meta según cfg.channel_provider.
        media_url = None
        urls_aparte = ""
        if quiere_audio(conv.voice_mode, cfg.default_voice_mode, payload.tipo):
            media_url, urls_aparte = await synthesize_reply_audio(bot_text, voice_id=cfg.voice_id)
        if media_url:
            ok, meta_id, _err = await wa_out.send(
                ws, cfg, conv.phone_jid, contenido=urls_aparte, audio_url=media_url,
            )
            await _persist_bot_message(db, conv, bot_text, meta_id or _local_id("bot"), media_url=media_url, msg_type="audio")
        else:
            ok, meta_id, _err = await wa_out.send(ws, cfg, conv.phone_jid, bot_text)
            await _persist_bot_message(db, conv, bot_text, meta_id or _local_id("bot"))

    # Derivación: mandar al cliente el mensaje de derivación configurado (rendereado).
    if action == "derivar":
        negocio = _business_name(cfg, ws.name)
        deriv_msg = render_message(cfg.derivation_message, negocio)
        if deriv_msg:
            ok, meta_id, _err = await wa_out.send(ws, cfg, conv.phone_jid, deriv_msg)
            await _persist_bot_message(db, conv, deriv_msg, meta_id or _local_id("handoff"))

    await db.commit()
    return {"ok": True, "conversation_id": conv.id, "bot": "responded", "action": action}


async def pause_bot_for_coexistence_echo(db: AsyncSession, ws: Workspace, customer_jid: str) -> Optional[int]:
    """Pausa el bot por `COEXISTENCE_PAUSE` en la conv de `customer_jid` (WO
    F3-02, canal Meta): el dueño del número contestó ese cliente DESDE la app
    de WhatsApp Business en el teléfono, no desde este sistema. Devuelve el
    id de la conversación pausada, o None si no existía (no se crea una conv
    nueva solo por un echo -- se degrada con gracia).

    Llamado por `api/meta.py` cuando `meta_client.parse_echo` detecta un
    `message_echoes` en el webhook -- ver la nota de "no verificado" en ese
    parser."""
    conv = (await db.execute(
        select(WaConversation).where(
            WaConversation.workspace_id == ws.id,
            WaConversation.phone_jid == customer_jid,
        )
    )).scalar_one_or_none()
    if not conv:
        return None
    now = datetime.now(timezone.utc)
    conv.bot_paused_until = now + COEXISTENCE_PAUSE
    conv.last_activity_at = now
    await db.commit()
    return conv.id
