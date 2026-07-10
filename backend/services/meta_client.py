"""Cliente HTTP para Meta Cloud API (WhatsApp oficial, WO F3-02).

Portado de `SalesBot/backend/services/meta_client.py` (envio + parseo del
webhook) + la verificacion HMAC de `HouseApp/backend/core/whatsapp.py`
(`verify_signature`). Cada funcion de envio recibe `phone_number_id` y
`access_token` explicitos -- nunca de un settings global "de una sola app" --
porque la suite es multi-tenant: cada workspace tiene su propio
`phone_number_id` (columna en `workspace_bot_config`), pero TODOS comparten el
mismo token de sistema (`settings.META_ACCESS_TOKEN`, ver `core/config.py`) --
un System User de Meta con acceso a todos los WABA conectados (patron Tech
Provider, igual que SalesBot).

Este modulo es SOLO el cliente HTTP + parsing/verificacion del webhook. El
envio real de la respuesta del bot/operador pasa SIEMPRE por
`services.wa_out` (camino unico de salida); `api/meta.py` usa este modulo
para el handshake del webhook y para bajar la media entrante.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Optional, Tuple

import httpx

log = logging.getLogger("tasar.meta_client")

_GRAPH_BASE = "https://graph.facebook.com/v23.0"

# mime_type de Meta -> extension para nombrar el archivo (Whisper/Cloudinary
# infieren el formato por extension).
_AUDIO_MIME_EXT = {
    "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a",
    "audio/amr": "amr", "audio/aac": "aac", "audio/wav": "wav",
}


# ── Verificacion HMAC del webhook ───────────────────────────────────────────

def verify_signature(app_secret: str, raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verifica `X-Hub-Signature-256` (HMAC-SHA256 del body CRUDO con el app
    secret del Meta Developer App). Portado de HouseApp
    (`core/whatsapp.py:verify_signature`).

    A diferencia de HouseApp (que deja pasar sin `app_secret` configurado),
    aca es FAIL-CLOSED: sin `app_secret` no hay forma de validar nada, y este
    canal escribe en el CRM/conversaciones -- se prefiere 403 antes que
    aceptar un webhook sin verificar. Ver decision en el reporte del WO F3-02.
    """
    if not app_secret:
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


# ── Envio ────────────────────────────────────────────────────────────────────

async def send_text(
    phone_number_id: str, to: str, text: str, access_token: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Envia texto via Meta Cloud API. Returns (ok, message_id, error)."""
    url = f"{_GRAPH_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", "to": to, "type": "text",
        "text": {"body": text},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            data = r.json()
            msg_id = ((data.get("messages") or [{}])[0]).get("id")
            return True, msg_id, None
        return False, None, f"http {r.status_code}: {r.text[:300]}"
    except Exception as e:  # noqa: BLE001
        return False, None, str(e)


async def send_audio(
    phone_number_id: str, to: str, access_token: str,
    *, media_id: Optional[str] = None, link: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Envia un audio via Meta Cloud API por `media_id` (preferido) o `link`.

    `voice: true` hace que WhatsApp lo muestre como NOTA DE VOZ (micrófono) en
    vez de archivo de audio -- requiere OGG/OPUS. Returns (ok, message_id, error).
    """
    audio: dict = {"id": media_id} if media_id else {"link": link}
    audio["voice"] = True
    url = f"{_GRAPH_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": audio}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            data = r.json()
            msg_id = ((data.get("messages") or [{}])[0]).get("id")
            return True, msg_id, None
        return False, None, f"http {r.status_code}: {r.text[:300]}"
    except Exception as e:  # noqa: BLE001
        return False, None, str(e)


# ── Media entrante ───────────────────────────────────────────────────────────

async def download_media(media_id: str, access_token: str) -> Optional[Tuple[bytes, str, str]]:
    """Descarga media de Meta por su ID (2 pasos: resolver URL + bajar bytes).

    A diferencia de Baileys (que ya entrega una URL descargable via el
    gateway), Meta entrega un `media_id`: hay que pedir GET /{media_id} para
    obtener la URL real y luego descargarla, ambas con el Bearer token.
    Devuelve (bytes, filename, mime) o None.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            meta = await client.get(f"{_GRAPH_BASE}/{media_id}", headers=headers)
            if meta.status_code != 200:
                log.warning("[meta_client] resolve de media fallo %s: %s", meta.status_code, meta.text[:200])
                return None
            info = meta.json()
            media_url = info.get("url")
            mime = (info.get("mime_type") or "").split(";")[0].strip()
            if not media_url:
                return None
            blob = await client.get(media_url, headers=headers)
            if blob.status_code != 200:
                log.warning("[meta_client] download de media fallo %s", blob.status_code)
                return None
            ext = _AUDIO_MIME_EXT.get(mime, "ogg" if mime.startswith("audio/") else "bin")
            return blob.content, f"media.{ext}", mime
    except Exception as e:  # noqa: BLE001
        log.warning("[meta_client] error bajando media: %s", e)
        return None


# ── Parseo del webhook entrante ─────────────────────────────────────────────

def parse_incoming_payload(raw: dict) -> Optional[dict]:
    """Extrae el primer mensaje inbound de un webhook Meta Cloud API.

    Retorna dict con keys: telefono_sender, nombre_sender, contenido, tipo,
    media_url (en realidad un media_id -- se llama asi para que el shape
    calce 1:1 con el resto del pipeline; `api/meta.py` lo resuelve a URL
    publica antes de pasarlo al pipeline comun), meta_message_id,
    phone_number_id, business_phone (numero propio del WABA, para el
    heuristico de coexistence).

    None si el payload no contiene un mensaje real (ej. status update).
    """
    try:
        changes = (raw.get("entry") or [{}])[0].get("changes") or [{}]
        value = (changes[0] if changes else {}).get("value") or {}

        messages = value.get("messages")
        if not messages:
            return None

        msg = messages[0]
        metadata = value.get("metadata") or {}
        contacts = (value.get("contacts") or [{}])[0]
        profile = contacts.get("profile") or {}

        msg_type = msg.get("type", "text")
        contenido = ""
        media_id = None

        if msg_type == "text":
            contenido = (msg.get("text") or {}).get("body", "")
        elif msg_type in ("audio", "voice"):
            audio = msg.get("audio") or msg.get("voice") or {}
            media_id = audio.get("id")
        elif msg_type == "image":
            image = msg.get("image") or {}
            media_id = image.get("id")
            contenido = image.get("caption", "")
        elif msg_type == "document":
            doc = msg.get("document") or {}
            media_id = doc.get("id")
            contenido = doc.get("caption", "")

        return {
            "telefono_sender": msg.get("from", ""),
            "nombre_sender": profile.get("name", ""),
            "contenido": contenido,
            "tipo": msg_type,
            "media_url": media_id,
            "meta_message_id": msg.get("id"),
            "phone_number_id": metadata.get("phone_number_id", ""),
            "business_phone": metadata.get("display_phone_number"),
        }
    except Exception:  # noqa: BLE001 -- payload inesperado, nunca romper el webhook
        return None


def parse_echo(raw: dict) -> Optional[dict]:
    """Detecta un mensaje de COEXISTENCE (WO F3-02): el dueno del numero
    contesta un cliente DESDE la app WhatsApp Business en el telefono (no
    desde este sistema), y Meta lo reenvia al webhook para que el bot se
    calle en esa conversacion.

    NO VERIFICADO contra un webhook real de Coexistence (feature de Meta sin
    sandbox disponible en este entorno; ninguno de los donantes -- SalesBot
    ni HouseApp -- la implementa para Meta, solo SalesBot la tiene para
    Gupshup). El shape usado aca (`value.message_echoes`, paralelo a
    `value.messages`, cada item con `to`/`id`/`type`/contenido igual que un
    mensaje normal) es el documentado por Meta para WhatsApp Business App
    Coexistence al momento de escribir esto -- pero ES UN BEST-EFFORT: hay
    que confirmarlo contra un webhook real antes de confiar en produccion.
    Ver el reporte del WO F3-02 para la mitigacion (feature flag + logueo).
    """
    try:
        changes = (raw.get("entry") or [{}])[0].get("changes") or [{}]
        value = (changes[0] if changes else {}).get("value") or {}
        echoes = value.get("message_echoes")
        if not echoes:
            return None
        echo = echoes[0]
        to = (echo.get("to") or "").strip()
        if not to:
            return None
        return {
            "customer": to,
            "meta_message_id": echo.get("id"),
            "phone_number_id": (value.get("metadata") or {}).get("phone_number_id", ""),
        }
    except Exception:  # noqa: BLE001
        return None
