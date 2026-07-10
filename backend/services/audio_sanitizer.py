"""Sanitizador de texto para TTS — UNICO lugar de estos dos cortes (WO F3-01).

Regla de la casa: "UN solo camino de salida de audio" implica UNA sola capa
que decide que NO se lee en voz alta. Ese lugar es este modulo; lo llama
`services.audio_out` (el UNICO helper que genera audio saliente), nadie mas.

Corta DOS cosas antes de mandar texto a ElevenLabs:
  1. `<<PAUSE>>` — marcador de pacing que el motor podria emitir en el futuro
     (hoy `bot_engine.py` no lo genera; se corta preventivamente para que,
     si alguna vez aparece en el texto — prompt, FAQ pegada a mano, etc. —
     jamas se lea literal en el audio).
  2. URLs — ElevenLabs las lee letra por letra ("doble u doble u doble u
     punto..."), inutilizable por voz. Se cortan del texto que va al TTS y
     se devuelven aparte para mandarlas como mensaje de texto normal
     (clickeable) despues del audio.

Portado del patron probado en SalesBot (`api/baileys.py` + `api/gupshup.py`,
repartido por carril ahi) pero UNIFICADO en una sola funcion para esta suite.
"""
from __future__ import annotations

import re
from typing import List, Tuple


PAUSE_MARKER = "<<PAUSE>>"

# Match: protocolo opcional + dominio + path opcional. Sin protocolo tambien
# matchea (Gemini a veces omite "https://"), por eso el TLD whitelist de abajo
# filtra falsos positivos como "no.es" o "y.eso".
_URL_PATTERN = re.compile(
    r"(?:https?://)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+(?:/[^\s,]*)?",
    re.IGNORECASE,
)
_VALID_TLDS = {
    "com", "ar", "com.ar", "org", "net", "io", "app", "co", "me",
    "info", "biz", "tech", "dev", "online", "site", "store",
    "gov", "edu", "mx", "uy", "cl", "br", "es", "us", "pe",
}


def _es_url(m: str) -> bool:
    """Heuristica anti-falso-positivo: exige protocolo, path, o TLD conocido."""
    if m.startswith(("http://", "https://")) or "/" in m:
        return True
    parts = m.lower().split(".")
    if len(parts) >= 2:
        tld = parts[-1]
        if tld in _VALID_TLDS:
            return True
        if len(parts) >= 3 and ".".join(parts[-2:]) in _VALID_TLDS:
            return True
    return False


def _remove_urls(text: str) -> str:
    out = text
    for m in _URL_PATTERN.findall(text):
        if _es_url(m):
            out = out.replace(m, "")
    return out


def sanitize_for_tts(text: str) -> Tuple[str, List[str]]:
    """Prepara un texto para ElevenLabs. Devuelve (texto_para_audio, urls_aparte).

    1. Quita `<<PAUSE>>` (se une el texto sin el marcador; esta suite no tiene
       pacing multi-mensaje — a diferencia de SalesBot — asi que solo importa
       que jamas se lea el token literal).
    2. Si hay URLs, corta el texto justo ANTES de la primera y elimina el
       resto; las URLs quedan en la lista devuelta para reenviarlas como
       texto aparte (normalizadas con esquema https:// si no lo tenian).
    """
    if not text:
        return "", []

    clean = text.replace(PAUSE_MARKER, " ")
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    urls_raw = [m for m in _URL_PATTERN.findall(clean) if _es_url(m)]
    if not urls_raw:
        return clean, []

    first_url = urls_raw[0]
    pre = clean.split(first_url, 1)[0]
    pre = re.sub(r"[\s\-:,;]+$", "", pre).strip()
    pre = _remove_urls(pre).strip()

    if not pre or len(pre) < 4:
        pre = "Dale, ahora te lo paso por mensaje."
    else:
        lowered = pre.lower().rstrip(".!?")
        if lowered.endswith((
            "el link", "los links", "la url", "la direccion", "la dirección",
            "el video", "el instructivo",
        )):
            pre = pre.rstrip(".!? ") + ", te lo paso por mensaje."
        elif not pre.rstrip().endswith((".", "!", "?")):
            pre = pre.rstrip() + "."

    urls_norm = [u if u.startswith(("http://", "https://")) else f"https://{u}" for u in urls_raw]
    return pre, urls_norm
