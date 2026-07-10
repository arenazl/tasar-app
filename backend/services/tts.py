"""Text-to-Speech via ElevenLabs + subida a Cloudinary (WO F3-01).

Voz GENERICA configurable por workspace (`bot_config.voice_id`, con default
global `settings.ELEVENLABS_DEFAULT_VOICE_ID`) — gate del dueno RESUELTO:
NADA de voice-clone (sin subida de sample, sin creacion de voces en
ElevenLabs, sin "voz del vendedor"). Portado y simplificado de
SalesBot/backend/services/tts.py: se conserva el manejo de errores por
status code (401/429/timeout) y el formato opus/ogg (el que espera WhatsApp
para notas de voz PTT); se DESCARTA todo lo especifico de voice_kit /
categoria / fallback a Gemini TTS / sanitizado de risas — no aplica aca.

El corte de `<<PAUSE>>` y de URLs pasa ANTES, en `services.audio_sanitizer`
(llamado desde el UNICO helper `services.audio_out`). Este modulo NO sanitiza
texto: solo sintetiza lo que le pasan y sube el resultado a Cloudinary.

Si falla cualquier paso devolvemos None — el caller (audio_out) decide caer
a texto.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
import cloudinary
import cloudinary.uploader

from core.config import settings


ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


def _ensure_cloudinary_config() -> None:
    """Idempotente: configura Cloudinary la primera vez."""
    if cloudinary.config().cloud_name:
        return
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


async def synthesize_mp3(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """Genera audio (opus/ogg) desde texto via ElevenLabs y devuelve los bytes.

    Devuelve None si:
    - No esta configurada la API key
    - No hay voice_id (ni parametro ni default de workspace/global)
    - Falla la llamada a ElevenLabs (401/429/timeout/etc.)

    Args:
        text: contenido a sintetizar, YA sanitizado (sin <<PAUSE>>/URLs).
        voice_id: voz del workspace; si es None usa ELEVENLABS_DEFAULT_VOICE_ID.
    """
    if not settings.ELEVENLABS_API_KEY:
        print("[tts] ELEVENLABS_API_KEY no configurada", flush=True)
        return None
    vid = voice_id or settings.ELEVENLABS_DEFAULT_VOICE_ID
    if not vid:
        print("[tts] no hay voice_id (ni de workspace ni default global)", flush=True)
        return None

    clean = (text or "").strip()
    if not clean:
        return None
    if len(clean) > 4500:
        clean = clean[:4500]

    payload = {
        "text": clean,
        "model_id": settings.ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
        # language_code lo aceptan flash/turbo v2.5 y v3 (no multilingual_v2).
        "language_code": "es",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # opus 48kHz/64kbps: formato PTT que espera WhatsApp (wa-gateway
            # manda mimetype 'audio/ogg; codecs=opus' en /send).
            r = await client.post(
                f"{ELEVENLABS_BASE}/text-to-speech/{vid}?output_format=opus_48000_64",
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/ogg",
                },
                json=payload,
            )
            r.raise_for_status()
            return r.content
    except httpx.HTTPStatusError as e:
        body_preview = ""
        try:
            body_preview = e.response.text[:200]
        except Exception:
            pass
        sc = e.response.status_code
        if sc == 401:
            print(f"[tts] API KEY INVALIDA O SIN CREDITOS -> respuesta cae a texto. detalle: {body_preview}", flush=True)
        elif sc == 429:
            print(f"[tts] RATE LIMIT -> respuesta cae a texto. detalle: {body_preview}", flush=True)
        else:
            print(f"[tts] HTTP {sc} -> respuesta cae a texto. detalle: {body_preview}", flush=True)
        return None
    except httpx.TimeoutException as e:
        print(f"[tts] TIMEOUT (>60s) -> respuesta cae a texto. {e}", flush=True)
        return None
    except Exception as e:  # noqa: BLE001 — nunca romper el flujo de WhatsApp por un fallo de TTS
        print(f"[tts] error inesperado {type(e).__name__}: {e} -> respuesta cae a texto", flush=True)
        return None


def _upload_to_cloudinary(audio_bytes: bytes, public_id_prefix: str = "tts") -> Optional[str]:
    """Sube bytes opus/ogg a Cloudinary y devuelve la URL https.

    Cloudinary maneja audio bajo resource_type='video'. Subimos format=ogg
    porque es lo que WhatsApp espera para notas de voz (PTT).
    """
    _ensure_cloudinary_config()
    try:
        result = cloudinary.uploader.upload(
            audio_bytes,
            resource_type="video",
            folder="tasar/wa-tts",
            public_id=f"{public_id_prefix}_{int(time.time() * 1000)}",
            format="ogg",
        )
        return result.get("secure_url")
    except Exception as e:  # noqa: BLE001
        print(f"[tts] cloudinary upload error: {e}", flush=True)
        return None


async def synthesize_to_cloudinary(
    text: str,
    voice_id: Optional[str] = None,
    prefix: str = "tts",
) -> Optional[str]:
    """High-level helper: texto (ya sanitizado) -> audio -> Cloudinary -> URL publica.

    Devuelve la URL secure_url o None si falla cualquier paso (el caller cae
    a texto plano sin romper el flujo).
    """
    audio = await synthesize_mp3(text, voice_id=voice_id)
    if not audio:
        return None
    # to_thread: el upload de Cloudinary es BLOQUEANTE (SDK sync). Sin esto
    # bloquea el event loop del worker uvicorn durante el upload y congela
    # todo lo demas que ese worker atiende mientras el bot responde.
    return await asyncio.to_thread(_upload_to_cloudinary, audio, prefix)
