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

# Cache del provider activo KEYED por workspace_id: el switch de un tenant no puede
# afectar a otro (app_settings tiene unique (workspace_id, key)).
_PROVIDER_CACHE: dict[int, tuple[str, float]] = {}  # workspace_id -> (provider, expires_at)
_PROVIDER_TTL = 15


def invalidate_provider_cache(workspace_id: int | None = None) -> None:
    """Con workspace_id: invalida solo ese tenant. Sin argumento: limpia todo."""
    if workspace_id is None:
        _PROVIDER_CACHE.clear()
    else:
        _PROVIDER_CACHE.pop(workspace_id, None)


async def _get_provider(workspace_id: int | None = None) -> str:
    # Sin workspace NO leemos el setting de otro tenant: usamos el default.
    if workspace_id is None:
        provider = _DEFAULT_PROVIDER
    else:
        now = time.time()
        cached = _PROVIDER_CACHE.get(workspace_id)
        if cached and cached[1] > now:
            provider = cached[0]
        else:
            provider = _DEFAULT_PROVIDER
            try:
                from sqlalchemy import select
                from core.database import AsyncSessionLocal
                from models.app_setting import AppSetting
                async with AsyncSessionLocal() as db:
                    row = (await db.execute(
                        select(AppSetting).where(
                            AppSetting.workspace_id == workspace_id,
                            AppSetting.key == "ai_provider",
                        )
                    )).scalar_one_or_none()
                    if row and row.value in _VALID_PROVIDERS:
                        provider = row.value
            except Exception:
                provider = _DEFAULT_PROVIDER
            _PROVIDER_CACHE[workspace_id] = (provider, now + _PROVIDER_TTL)
    # Safety net: si el setting dice 'claude' pero el CLI no está disponible,
    # forzamos Gemini para que la app no falle silenciosamente.
    if provider == "claude" and not _CLAUDE_AVAILABLE:
        log.warning("Setting says 'claude' but CLI not available - using Gemini")
        provider = "gemini"
    return provider


def _module_for(provider: str):
    return _gemini if provider == "gemini" else _claude


# ============ API pública (igual que claude_service) ============

# Re-export para que callers existentes sigan funcionando
SYSTEM_TASADOR = _claude.SYSTEM_TASADOR
SYSTEM_ANALYZER = _claude.SYSTEM_ANALYZER


async def chat_complete(prompt: str, system: str = SYSTEM_TASADOR, workspace_id: int | None = None) -> str:
    provider = await _get_provider(workspace_id)
    mod = _module_for(provider)
    log.info("AI chat_complete via %s", provider)
    return await mod.chat_complete(prompt, system, workspace_id=workspace_id)


async def chat_stream(prompt: str, system: str = SYSTEM_TASADOR, session_id=None, workspace_id: int | None = None) -> AsyncIterator[str]:
    provider = await _get_provider(workspace_id)
    mod = _module_for(provider)
    log.info("AI chat_stream via %s", provider)
    async for chunk in mod.chat_stream(prompt, system, session_id, workspace_id=workspace_id):
        yield chunk


async def analyze_property(property_data: dict, workspace_id: int | None = None) -> dict:
    provider = await _get_provider(workspace_id)
    mod = _module_for(provider)
    log.info("AI analyze_property via %s", provider)
    return await mod.analyze_property(property_data, workspace_id=workspace_id)
