"""AI Router — adapter transparente entre Claude y Gemini.

El service expone la misma API que claude_service.py original. Los endpoints
no saben qué provider están usando.

Provider activo se lee de `app_settings.ai_provider` (claude | gemini), con
cache de 15s. Si Claude CLI no está instalado (ej. en Heroku), automáticamente
hace fallback a Gemini.
"""
import os
import shutil
import time
import logging
from typing import AsyncIterator

import services.claude_service as _claude
import services.gemini_service as _gemini


log = logging.getLogger("tasar.ai_router")


_VALID_PROVIDERS = ("claude", "gemini")

# Si Claude CLI no está en PATH (típico en Heroku), forzamos default a Gemini
_CLAUDE_AVAILABLE = bool(shutil.which("claude") or shutil.which("claude.cmd"))
_DEFAULT_PROVIDER = "claude" if _CLAUDE_AVAILABLE else "gemini"
if not _CLAUDE_AVAILABLE:
    log.warning("Claude CLI not found in PATH - defaulting to Gemini provider")

_PROVIDER_CACHE: tuple[str, float] | None = None
_PROVIDER_TTL = 15


def invalidate_provider_cache() -> None:
    global _PROVIDER_CACHE
    _PROVIDER_CACHE = None


async def _get_provider() -> str:
    global _PROVIDER_CACHE
    now = time.time()
    if _PROVIDER_CACHE and _PROVIDER_CACHE[1] > now:
        return _PROVIDER_CACHE[0]
    provider = _DEFAULT_PROVIDER
    try:
        from sqlalchemy import select
        from core.database import AsyncSessionLocal
        from models.app_setting import AppSetting
        async with AsyncSessionLocal() as db:
            row = (await db.execute(
                select(AppSetting).where(AppSetting.key == "ai_provider")
            )).scalar_one_or_none()
            if row and row.value in _VALID_PROVIDERS:
                provider = row.value
    except Exception:
        provider = _DEFAULT_PROVIDER
    # Safety net: si el setting dice 'claude' pero el CLI no está disponible,
    # forzamos Gemini para que la app no falle silenciosamente.
    if provider == "claude" and not _CLAUDE_AVAILABLE:
        log.warning("Setting says 'claude' but CLI not available - using Gemini")
        provider = "gemini"
    _PROVIDER_CACHE = (provider, now + _PROVIDER_TTL)
    return provider


def _module_for(provider: str):
    return _gemini if provider == "gemini" else _claude


# ============ API pública (igual que claude_service) ============

# Re-export para que callers existentes sigan funcionando
SYSTEM_TASADOR = _claude.SYSTEM_TASADOR
SYSTEM_ANALYZER = _claude.SYSTEM_ANALYZER


async def chat_complete(prompt: str, system: str = SYSTEM_TASADOR) -> str:
    provider = await _get_provider()
    mod = _module_for(provider)
    log.info("AI chat_complete via %s", provider)
    return await mod.chat_complete(prompt, system)


async def chat_stream(prompt: str, system: str = SYSTEM_TASADOR, session_id=None) -> AsyncIterator[str]:
    provider = await _get_provider()
    mod = _module_for(provider)
    log.info("AI chat_stream via %s", provider)
    async for chunk in mod.chat_stream(prompt, system, session_id):
        yield chunk


async def analyze_property(property_data: dict) -> dict:
    provider = await _get_provider()
    mod = _module_for(provider)
    log.info("AI analyze_property via %s", provider)
    return await mod.analyze_property(property_data)
