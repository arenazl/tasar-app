"""UNICO modulo de salida de WhatsApp (WO F3-02) — resuelve baileys|meta.

Lección negativa que esta WO evita a propósito: en SalesBot el `if provider ==
...` de envío quedó duplicado en 3 archivos sin un módulo único. Acá nace
centralizado desde el día uno — regla de la casa "cada regla en una capa":
NINGÚN otro archivo del backend debe comparar `channel_provider` para decidir
cómo enviar. `grep -rn "provider ==" backend/` fuera de este archivo debe dar 0.

`send()` es el reemplazo directo de lo que hasta F3-01 era
`api.whatsapp._send_via_gateway` (camino único de salida Baileys, vía
wa-gateway) — esa función se movió tal cual acá como `_send_via_baileys` y se
le agregó el carril Meta Cloud API (`_send_via_meta`, WO F3-02) al lado.
Cualquier caller (webhook entrante de los dos canales, reply humano del
Inbox, notificación de tools) pasa por acá.
"""
from __future__ import annotations

from typing import Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.bot_config import WorkspaceBotConfig
from models.workspace import Workspace
from services import meta_client
from services.bot_tools import _phone_from_jid

SendResult = Tuple[bool, Optional[str], Optional[str]]  # (ok, message_id, error)


async def _send_via_baileys(
    slug: str, telefono: str, contenido: str = "",
    *, audio_url: Optional[str] = None, ptt: bool = True,
) -> SendResult:
    """Envia un mensaje por el gateway del workspace: texto, o audio (ptt) +
    opcionalmente un texto aparte (ej. URLs que se cortaron antes del TTS).

    Portado 1:1 de `api.whatsapp._send_via_gateway` (WO F2-03/F2-04/F3-01),
    solo movido de modulo. Sigue siendo el UNICO POST /send al wa-gateway.
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
                f"{base}/send", json=payload,
                headers={"X-API-Key": settings.WA_GATEWAY_KEY},
            )
            data = r.json()
            return (bool(data.get("ok")), data.get("meta_message_id"), data.get("error"))
    except Exception as e:  # noqa: BLE001
        return (False, None, str(e))


async def _send_via_meta(
    cfg: Optional[WorkspaceBotConfig], telefono: str, contenido: str = "",
    *, audio_url: Optional[str] = None, ptt: bool = True,  # noqa: ARG001 (ptt no aplica a Meta, siempre PTT)
) -> SendResult:
    """Envia por Meta Cloud API (WO F3-02). `telefono` puede venir como JID
    (`549...@s.whatsapp.net`) o numero E.164 -- se normaliza igual que el
    resto del pipeline (`services.bot_tools._phone_from_jid`).

    Simplificación consciente vs. el donante (SalesBot): manda el audio por
    `link` directo (Cloudinary ya es una URL pública estable), sin el paso
    intermedio de `upload_media` a Graph API que SalesBot usa como respaldo
    de confiabilidad. Si en producción el render de nota de voz por link
    falla, ese `upload_media` (ya portado en `meta_client` como
    `download_media`'s hermano simétrico) es la mejora natural a sumar.
    """
    if not cfg or not cfg.meta_phone_number_id:
        return False, None, "workspace sin meta_phone_number_id configurado"
    access_token = (settings.META_ACCESS_TOKEN or "").strip()
    if not access_token:
        return False, None, "META_ACCESS_TOKEN no configurado"
    to = _phone_from_jid(telefono) or telefono
    if audio_url:
        return await meta_client.send_audio(cfg.meta_phone_number_id, to, access_token, link=audio_url)
    return await meta_client.send_text(cfg.meta_phone_number_id, to, contenido, access_token)


async def send(
    workspace: Workspace, cfg: Optional[WorkspaceBotConfig], telefono: str, contenido: str = "",
    *, audio_url: Optional[str] = None, ptt: bool = True,
) -> SendResult:
    """Envia por el canal configurado del workspace. ÚNICO punto de decisión
    baileys|meta de todo el backend (ver módulo). `cfg` es
    `WorkspaceBotConfig` del workspace; si es `None` (workspace sin fila de
    config todavía) cae a Baileys por default, igual que
    `channel_provider` default en el modelo.
    """
    provider = (cfg.channel_provider if cfg and cfg.channel_provider else "baileys")
    if provider == "meta":
        return await _send_via_meta(cfg, telefono, contenido, audio_url=audio_url, ptt=ptt)
    return await _send_via_baileys(workspace.slug, telefono, contenido, audio_url=audio_url, ptt=ptt)


async def load_target(db: AsyncSession, workspace_id: int) -> Tuple[Workspace, Optional[WorkspaceBotConfig]]:
    """Carga `Workspace` + su `WorkspaceBotConfig` en 1 sola query (outer
    join) -- el "target" que necesita `send()`. Usado por `api/conversations.py`
    (reply humano del Inbox) para no hacer 2 queries separadas ni duplicar el
    resolve del provider."""
    row = (await db.execute(
        select(Workspace, WorkspaceBotConfig)
        .outerjoin(WorkspaceBotConfig, WorkspaceBotConfig.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id)
    )).first()
    if not row:
        raise ValueError(f"Workspace {workspace_id} no encontrado")
    return row[0], row[1]
