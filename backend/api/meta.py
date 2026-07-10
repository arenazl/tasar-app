"""Webhook Meta Cloud API oficial (WO F3-02) — canal SERIO de WhatsApp.

Baileys (`api/whatsapp.py`) es no-oficial (riesgo de ban de WhatsApp) — sirve
para arrancar sin trámites; Meta Cloud API es el canal serio para producción.
Patrones portados: `SalesBot/backend/api/meta.py` (webhook verify + ruteo por
`phone_number_id`) + `services/meta_client.py`, y la verificación HMAC de
`HouseApp/backend/core/whatsapp.py`.

UN webhook (`GET/POST /api/meta/webhook`) compartido por TODOS los workspaces
conectados por Meta: el ruteo es por `meta_phone_number_id` (columna en
`workspace_bot_config`), igual que el ruteo Baileys es por `tenant` (slug). El
`verify_token`, el `access_token` y el `app_secret` son GLOBALES al server
(un único Meta Business Manager / System User que agrupa los WABA de todos
los workspaces conectados por este canal, patrón Tech Provider) — SOLO viven
en env/Secret Manager (`core/config.py`), nunca en la DB ni se exponen al
frontend.

El mensaje entrante se normaliza al MISMO `IncomingPayload` que procesa el
canal Baileys y se le pasa a `services.wa_inbound.process_incoming` — UN solo
pipeline aguas abajo para los dos canales (regla "cada regla en una capa").
El envío de la respuesta usa `services.wa_out` (resuelve baileys|meta por
`channel_provider`); este archivo NUNCA llama a Graph API para enviar, solo
para bajar media entrante (`meta_client.download_media`).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.workspace import Workspace
from models.bot_config import WorkspaceBotConfig
from services import meta_client
from services.cloudinary_service import upload_audio, upload_image
from services.wa_inbound import IncomingPayload, process_incoming, pause_bot_for_coexistence_echo

log = logging.getLogger("tasar.meta")

router = APIRouter(prefix="/api/meta", tags=["meta"])

# Tipos de media que Meta manda como media_id (hay que bajarlos de Graph API
# y subirlos a Cloudinary antes de entrar al pipeline común -- ver abajo).
_MEDIA_TYPES = ("audio", "voice", "image", "document")


@router.get("/webhook")
async def meta_webhook_verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
) -> PlainTextResponse:
    """Verificación del webhook por Meta (GET con hub.challenge). El
    verify_token es GLOBAL al server (settings.META_WEBHOOK_VERIFY_TOKEN):
    Meta exige un único valor por URL de webhook registrada, y esta suite
    expone UNA sola URL de webhook Meta para todos los workspaces."""
    expected = (settings.META_WEBHOOK_VERIFY_TOKEN or "").strip()
    if hub_mode == "subscribe" and expected and hub_verify_token == expected:
        log.info("[meta] webhook verificado")
        return PlainTextResponse(hub_challenge)
    log.warning("[meta] verificacion fallida: mode=%s token_match=%s", hub_mode, hub_verify_token == expected)
    raise HTTPException(status_code=403, detail="Forbidden")


async def _resolve_workspace(
    db: AsyncSession, phone_number_id: str,
) -> tuple[Optional[Workspace], Optional[WorkspaceBotConfig]]:
    """Resuelve (Workspace, WorkspaceBotConfig) por `meta_phone_number_id`.
    Ruteo INDEPENDIENTE por workspace, sin env vars -- igual que Baileys rutea
    por `tenant` (slug)."""
    if not phone_number_id:
        return None, None
    row = (await db.execute(
        select(Workspace, WorkspaceBotConfig)
        .join(WorkspaceBotConfig, WorkspaceBotConfig.workspace_id == Workspace.id)
        .where(WorkspaceBotConfig.meta_phone_number_id == phone_number_id)
        .limit(1)
    )).first()
    if not row:
        log.warning("[meta] phone_number_id '%s' sin workspace (meta_phone_number_id)", phone_number_id)
        return None, None
    return row[0], row[1]


@router.post("/webhook")
async def meta_webhook_incoming(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Recibe webhook POST de Meta Cloud API. Verifica firma, normaliza,
    delega en el pipeline común (`services.wa_inbound.process_incoming`)."""
    raw_body = await request.body()

    sig = request.headers.get("X-Hub-Signature-256")
    if not meta_client.verify_signature(settings.META_APP_SECRET, raw_body, sig):
        log.warning("[meta] firma HMAC invalida o META_APP_SECRET no configurado")
        raise HTTPException(status_code=403, detail="Firma invalida")

    try:
        raw = json.loads(raw_body)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"JSON invalido: {e}")

    # Coexistence (best-effort, NO verificado -- ver meta_client.parse_echo):
    # el dueño contestó desde el teléfono. Se chequea ANTES que `messages`
    # normales porque un webhook de Meta trae como mucho un tipo de evento útil.
    if settings.COEX_HANDOFF_ENABLED:
        echo = meta_client.parse_echo(raw)
        if echo:
            ws, _cfg = await _resolve_workspace(db, echo["phone_number_id"])
            if not ws:
                return {"ok": True, "modo": "coex_echo_sin_workspace"}
            cust = (echo.get("customer") or "").split("@")[0]
            if not cust:
                return {"ok": True, "modo": "coex_echo_incompleto"}
            jid = f"{cust}@s.whatsapp.net"
            conv_id = await pause_bot_for_coexistence_echo(db, ws, jid)
            if conv_id is None:
                return {"ok": True, "modo": "coex_echo_sin_conv"}
            return {"ok": True, "modo": "coex_echo_handoff", "conversation_id": conv_id}

    parsed = meta_client.parse_incoming_payload(raw)
    if not parsed:
        return {"ok": True, "modo": "skip_no_message"}

    phone_number_id = parsed["phone_number_id"]
    ws, cfg = await _resolve_workspace(db, phone_number_id)
    if not ws:
        return {"ok": True, "modo": "skip_no_workspace"}

    access_token = (settings.META_ACCESS_TOKEN or "").strip()
    if not access_token:
        log.error("[meta] META_ACCESS_TOKEN no configurado")
        return {"ok": False, "error": "token_missing"}

    tel = parsed["telefono_sender"]
    if not tel:
        return {"ok": True, "modo": "skip_no_sender"}

    # Media entrante: Meta manda media_id (no URL) -- bajarlo de Graph API y
    # subirlo a Cloudinary para que quede una URL pública descargable, igual
    # que Baileys. A partir de ahí el pipeline común (`process_incoming`) es
    # 100% agnóstico del canal: transcribe por URL como si fuera Baileys.
    media_url_public: Optional[str] = None
    tipo = parsed["tipo"]
    if tipo in _MEDIA_TYPES and parsed["media_url"]:
        media = await meta_client.download_media(parsed["media_url"], access_token)
        if media:
            media_bytes, _filename, _mime = media
            try:
                if tipo in ("audio", "voice"):
                    up = await upload_audio(media_bytes, folder="wa-audio")
                else:
                    up = await upload_image(media_bytes, folder="wa-media")
                media_url_public = up.get("url")
            except Exception as e:  # noqa: BLE001 -- Cloudinary caído no rompe el webhook
                log.warning("[meta] upload de media a Cloudinary fallo: %s", e)

    tipo_norm = "audio" if tipo in ("audio", "voice") else tipo

    payload = IncomingPayload(
        tenant=ws.slug,
        telefono=f"{tel}@s.whatsapp.net",
        phone_publico=parsed.get("business_phone"),
        nombre_contacto=parsed["nombre_sender"] or None,
        contenido=parsed["contenido"],
        tipo=tipo_norm,
        media_url=media_url_public,
        meta_message_id=parsed["meta_message_id"],
    )
    return await process_incoming(db, ws, cfg, payload)
