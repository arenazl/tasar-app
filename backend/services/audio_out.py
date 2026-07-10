"""UNICO helper de salida de audio saliente por WhatsApp (WO F3-01).

Regla de la casa: "un solo camino de salida de audio". Este es ESE camino —
el bot (webhook entrante, auto/mirror) y cualquier otro flujo futuro que
quiera responder en audio pasan por `synthesize_reply_audio`. El envio fisico
al gateway sigue siendo `api.whatsapp._send_via_gateway` (el camino UNICO ya
existente de F2-03/F2-04, extendido con `audio_url`/`ptt`); este modulo NO
habla con el gateway, solo genera el audio.

Flujo:
  1. `audio_sanitizer.sanitize_for_tts` — corta <<PAUSE>> y URLs (los DOS
     cortes que pide el WO, en la UNICA capa que los aplica).
  2. `tts.synthesize_to_cloudinary` — ElevenLabs (voz GENERICA, sin
     voice-clone) -> mp3/ogg -> Cloudinary -> URL publica.
  3. Devuelve (media_url, texto_urls_aparte) al caller.

Degradacion: CUALQUIER fallo (sin API key, 401/429/timeout, texto vacio tras
sanitizar) devuelve (None, "") — el caller cae a texto plano. Nunca levanta
excepcion: un fallo de TTS no puede romper el flujo de WhatsApp.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from services.audio_sanitizer import sanitize_for_tts
from services.tts import synthesize_to_cloudinary


log = logging.getLogger("tasar.audio_out")


async def synthesize_reply_audio(
    text: str,
    voice_id: Optional[str] = None,
    prefix: str = "wa",
) -> Tuple[Optional[str], str]:
    """Texto de respuesta -> (media_url_o_None, texto_aparte_con_urls).

    Args:
        text: texto crudo de la respuesta (bot o vendedor), SIN sanitizar.
        voice_id: voz del workspace (bot_config.voice_id); None -> default global.
        prefix: prefijo del public_id en Cloudinary (debug/orden en el dashboard).
    """
    if not text or not text.strip():
        return None, ""
    audio_text, urls = sanitize_for_tts(text)
    if not audio_text.strip():
        return None, ""
    try:
        media_url = await synthesize_to_cloudinary(audio_text, voice_id=voice_id, prefix=prefix)
    except Exception as e:  # noqa: BLE001 — un fallo de TTS jamas rompe el flujo de WhatsApp
        log.warning("[audio_out] TTS fallo inesperado (degradando a texto): %s: %s", type(e).__name__, e)
        return None, ""
    if not media_url:
        return None, ""
    return media_url, "\n".join(urls)


def quiere_audio(voice_mode: Optional[str], default_voice_mode: Optional[str], tipo_entrante: str) -> bool:
    """Resuelve si la respuesta debe ir en audio segun el voice_mode efectivo.

    - off (default)  -> nunca.
    - auto           -> siempre.
    - mirror         -> solo si el mensaje entrante del cliente fue audio.
    El override de la conversacion pisa el default del workspace; sin
    override (None), hereda default_voice_mode.
    """
    vm = voice_mode or default_voice_mode or "off"
    if vm == "auto":
        return True
    if vm == "mirror":
        return tipo_entrante == "audio"
    return False
