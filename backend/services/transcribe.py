"""Transcripcion de audios via Groq Whisper (WO F3-01).

Usado por el webhook de WhatsApp (`api/whatsapp.py`) cuando llega una nota de
voz: 1) el gateway ya subio la media a Cloudinary y nos paso `media_url`,
2) bajamos los bytes, 3) los mandamos a Groq Whisper con prompt sesgado para
argentino coloquial, 4) devolvemos el texto transcripto.

Portado 1:1 de SalesBot/backend/services/transcribe.py (version robusta, con
manejo de errores por status code) — no tiene nada de voice-clone, es pura
transcripcion entrante.

Si falla cualquier paso, devolvemos None y el bot recibe el mensaje sin
transcripcion (el webhook cae al placeholder "[audio]").
"""
from __future__ import annotations

from typing import Optional, Tuple

import httpx

from core.config import settings


GROQ_BASE = "https://api.groq.com/openai/v1"

# Prompt-sesgo para Whisper. Mejora reconocimiento de:
# - argentinismos comunes ("che", "dale", "posta", "bardo", "copado")
# - dinero en pesos/dolares (sin signo $, con palabra)
# El prompt no se transcribe, solo orienta al modelo.
_BIAS_PROMPT = (
    "Conversacion casual en espanol argentino, voseo. Palabras frecuentes: "
    "che, dale, mira, escucha, onda, posta, bardo, copado, joya. "
    "Pesos pesos pesos, dolares dolares dolares. "
    "Ejemplo: che dale escuchame una cosa, posta, te paso el dato."
)

_MIME_MAP = {
    "ogg": "audio/ogg", "oga": "audio/ogg", "opus": "audio/ogg",
    "mp3": "audio/mpeg", "m4a": "audio/mp4",
    "wav": "audio/wav", "webm": "audio/webm",
}


async def _download_audio(url: str) -> Optional[Tuple[bytes, str]]:
    """Descarga el audio desde la URL (Cloudinary) y devuelve (bytes, filename)."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            ext = url.rsplit(".", 1)[-1].split("?")[0].lower() if "." in url else "ogg"
            if ext not in _MIME_MAP:
                ext = "ogg"
            return r.content, f"audio.{ext}"
    except Exception as e:  # noqa: BLE001
        print(f"[transcribe] download error (audio del cliente no llega a Whisper): {type(e).__name__}: {e}", flush=True)
        return None


async def _call_groq(audio_bytes: bytes, filename: str) -> Optional[str]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"
    mime = _MIME_MAP.get(ext, "audio/ogg")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (filename, audio_bytes, mime)}
            data = {
                "model": settings.GROQ_WHISPER_MODEL,
                "language": "es",
                "prompt": _BIAS_PROMPT,
                "response_format": "json",
                "temperature": "0",
            }
            r = await client.post(
                f"{GROQ_BASE}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files=files,
                data=data,
            )
            r.raise_for_status()
            text = (r.json().get("text") or "").strip()
            return text or None
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:200]
        except Exception:
            pass
        sc = e.response.status_code
        if sc == 401:
            print(f"[transcribe] GROQ KEY INVALIDA -> audio NO transcripto. detalle: {body}", flush=True)
        elif sc == 429:
            print(f"[transcribe] GROQ RATE LIMIT -> audio NO transcripto. detalle: {body}", flush=True)
        else:
            print(f"[transcribe] GROQ HTTP {sc} -> audio NO transcripto. detalle: {body}", flush=True)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"[transcribe] GROQ error {type(e).__name__}: {e} -> audio NO transcripto", flush=True)
        return None


async def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[str]:
    """Transcribe bytes de audio directamente via Groq Whisper (sin descarga previa)."""
    if not settings.GROQ_API_KEY:
        print("[transcribe] GROQ_API_KEY no configurada, skip", flush=True)
        return None
    return await _call_groq(audio_bytes, filename)


async def transcribe_audio_from_url(url: str) -> Optional[str]:
    """Transcribe una nota de voz de WhatsApp via Groq Whisper.

    Devuelve None si:
    - No esta configurado GROQ_API_KEY
    - Falla la descarga del audio
    - Falla la llamada a Groq

    En cualquier caso, no rompe el flujo del webhook: el bot recibira el
    placeholder "[audio]" en vez de la transcripcion.
    """
    if not settings.GROQ_API_KEY:
        print("[transcribe] GROQ_API_KEY no configurada, skip", flush=True)
        return None

    media = await _download_audio(url)
    if media is None:
        return None
    audio_bytes, filename = media
    return await _call_groq(audio_bytes, filename)
