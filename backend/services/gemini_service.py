"""Gemini service — adapter del Tasador AI usando Google Generative AI.

Misma interfaz que claude_service.py:
- chat_complete(prompt, system) -> str
- chat_stream(prompt, system, session_id) -> AsyncIterator[str]
- analyze_property(data) -> dict

Usa httpx async contra la API REST de Gemini (no requiere SDK extra). Modelo
default: gemini-2.5-flash (rápido + económico). Configurable desde
app_settings.gemini_model.
"""
import asyncio
import json
import logging
import time
from typing import AsyncIterator, Optional

import httpx

from core.config import settings


log = logging.getLogger("tasar.gemini_service")
log.setLevel(logging.INFO)


SYSTEM_TASADOR = """Sos un tasador inmobiliario experto en el mercado argentino.

Tu rol es:
- Analizar propiedades y comparables que te pasa el usuario.
- Sugerir ajustes de homogeneización (área, antigüedad, estado, ubicación, orientación).
- Estimar valor de mercado con rango (min/máx/modo) y nivel de confianza.
- Explicar tu razonamiento de forma clara y profesional.
- NUNCA inventar datos: si te falta info, pedila explícitamente.
- Usar pesos coherentes: comparables más similares pesan más.
- Devolver siempre que sea posible un JSON estructurado al final dentro de un bloque ```json ... ```."""


SYSTEM_ANALYZER = """Sos un analizador de propiedades inmobiliarias del mercado argentino.

REGLA CRITICA: Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE las
keys que indica el schema. Nada de texto antes ni después.

SCHEMA EXACTO (todas las keys obligatorias, flat, sin wrappers):
{
  "summary": "string corto",
  "highlights": ["punto fuerte 1", "..."],
  "concerns": ["riesgo 1", "..."],
  "suggested_condition": "a_estrenar|excelente|muy_bueno|bueno|regular|a_reciclar",
  "estimated_age_bracket": "0-5|5-15|15-30|30-50|50+",
  "market_segment": "premium|alto|medio|estandar|economico",
  "ai_confidence": 0.85
}"""


# Cache del modelo activo (mismo patrón que claude_service)
_MODEL_CACHE: tuple[str, float] | None = None
_MODEL_CACHE_TTL = 15
_DEFAULT_MODEL = "gemini-2.5-flash"
_VALID_MODELS = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro")


def invalidate_model_cache() -> None:
    global _MODEL_CACHE
    _MODEL_CACHE = None


async def _get_active_model() -> str:
    global _MODEL_CACHE
    now = time.time()
    if _MODEL_CACHE and _MODEL_CACHE[1] > now:
        return _MODEL_CACHE[0]
    model = _DEFAULT_MODEL
    try:
        from sqlalchemy import select
        from core.database import AsyncSessionLocal
        from models.app_setting import AppSetting
        async with AsyncSessionLocal() as db:
            row = (await db.execute(
                select(AppSetting).where(AppSetting.key == "gemini_model")
            )).scalar_one_or_none()
            if row and row.value in _VALID_MODELS:
                model = row.value
    except Exception:
        model = _DEFAULT_MODEL
    _MODEL_CACHE = (model, now + _MODEL_CACHE_TTL)
    return model


def _gemini_available() -> bool:
    return bool(settings.GEMINI_API_KEY)


async def _call_gemini(prompt: str, system: str, model: str) -> str:
    """POST a /v1beta/models/{model}:generateContent."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]} if system else None,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096,
        },
    }
    # Limpiar None
    if not payload["systemInstruction"]:
        del payload["systemInstruction"]

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json=payload,
        )
        if r.status_code != 200:
            log.warning("Gemini %s -> %d %s", model, r.status_code, r.text[:400])
            return ""
        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            log.warning("Gemini sin candidates: %s", str(data)[:300])
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        out = " ".join(p.get("text", "") for p in parts if p.get("text"))
        return out.strip()


async def chat_complete(prompt: str, system: str = SYSTEM_TASADOR) -> str:
    if not _gemini_available():
        return "[Gemini no disponible — falta GEMINI_API_KEY]"
    try:
        model = await _get_active_model()
        result = await _call_gemini(prompt, system, model)
        return result or "[Gemini no devolvió respuesta]"
    except Exception as e:
        log.exception("gemini chat_complete failed")
        return f"[Gemini error: {type(e).__name__}]"


async def chat_stream(
    prompt: str, system: str = SYSTEM_TASADOR, session_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Pseudo-streaming: una llamada, chunks al frontend."""
    if not _gemini_available():
        yield "[Gemini no disponible]"
        return
    try:
        model = await _get_active_model()
        full = await _call_gemini(prompt, system, model)
        if not full:
            yield "[Gemini no devolvió respuesta]"
            return
        chunk = 80
        for i in range(0, len(full), chunk):
            yield full[i:i + chunk]
            await asyncio.sleep(0.02)
    except Exception as e:
        yield f"[Gemini error: {type(e).__name__}]"


async def analyze_property(property_data: dict) -> dict:
    prompt = f"""Propiedad a analizar:
```json
{json.dumps(property_data, ensure_ascii=False, indent=2)}
```

Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE este schema flat:
```json
{{
  "summary": "una oración",
  "highlights": ["3-5 puntos"],
  "concerns": ["2-3 riesgos"],
  "suggested_condition": "uno de: a_estrenar, excelente, muy_bueno, bueno, regular, a_reciclar",
  "estimated_age_bracket": "uno de: 0-5, 5-15, 15-30, 30-50, 50+",
  "market_segment": "uno de: premium, alto, medio, estandar, economico",
  "ai_confidence": 0.85
}}
```"""
    raw = await chat_complete(prompt, system=SYSTEM_ANALYZER)
    return _extract_json(raw)


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    s = text.find("{"); e = text.rfind("}")
    if s == -1 or e == -1:
        return {}
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return {}
