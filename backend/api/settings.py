"""Endpoints de settings key/value por workspace.

Persiste preferencias que el user edita desde UI:
- claude_model: haiku | sonnet | opus
- (futuras) email_notifications, default_currency, etc.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.app_setting import AppSetting


router = APIRouter(prefix="/api/settings", tags=["settings"])


VALID_CLAUDE_MODELS = {"haiku", "sonnet", "opus"}
VALID_GEMINI_MODELS = {"gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"}
VALID_PROVIDERS = {"claude", "gemini"}


class SettingValue(BaseModel):
    value: Optional[str] = None


async def get_setting(db: AsyncSession, workspace_id: int, key: str, default: str = "") -> str:
    row = (await db.execute(
        select(AppSetting).where(
            AppSetting.workspace_id == workspace_id,
            AppSetting.key == key,
        )
    )).scalar_one_or_none()
    return row.value if row and row.value is not None else default


async def set_setting(db: AsyncSession, workspace_id: int, key: str, value: str) -> AppSetting:
    row = (await db.execute(
        select(AppSetting).where(
            AppSetting.workspace_id == workspace_id,
            AppSetting.key == key,
        )
    )).scalar_one_or_none()
    if row:
        row.value = value
    else:
        row = AppSetting(workspace_id=workspace_id, key=key, value=value)
        db.add(row)
    await db.commit()
    if row.id is None:
        await db.refresh(row)
    return row


@router.get("/{key}")
async def get_setting_endpoint(
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    val = await get_setting(db, user.workspace_id, key)
    return {"key": key, "value": val}


@router.put("/{key}")
async def set_setting_endpoint(
    key: str,
    body: SettingValue,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if key == "claude_model" and body.value not in VALID_CLAUDE_MODELS:
        raise HTTPException(400, f"claude_model invalido: {VALID_CLAUDE_MODELS}")
    if key == "gemini_model" and body.value not in VALID_GEMINI_MODELS:
        raise HTTPException(400, f"gemini_model invalido: {VALID_GEMINI_MODELS}")
    if key == "ai_provider" and body.value not in VALID_PROVIDERS:
        raise HTTPException(400, f"ai_provider invalido: {VALID_PROVIDERS}")

    await set_setting(db, user.workspace_id, key, body.value or "")

    # Invalidar caches relevantes
    if key == "claude_model":
        from services import claude_service; claude_service.invalidate_model_cache()
    if key == "gemini_model":
        from services import gemini_service; gemini_service.invalidate_model_cache()
    if key == "ai_provider":
        from services import ai_router; ai_router.invalidate_provider_cache()

    return {"key": key, "value": body.value}


@router.post("/test-email")
async def test_email(user: User = Depends(get_current_user)):
    """Envia un email de prueba al usuario actual. Sirve para validar
    que Brevo SMTP esta configurado correctamente."""
    if not user.email:
        raise HTTPException(400, "Usuario sin email")
    from services.email_service import send_email, _wrap
    html = _wrap(
        "Email de prueba",
        f"<p>Hola {user.full_name or 'tasador'},</p>"
        "<p>Este email confirma que la configuracion SMTP via Brevo esta funcionando correctamente.</p>"
        "<p>Ya estas listo para recibir notificaciones automaticas de tasaciones, comentarios y resumenes.</p>"
    )
    ok = await send_email(user.email, "Test email TasAR", html)
    return {"ok": ok, "to": user.email}
