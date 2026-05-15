from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import re

from core.database import get_db
from core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from models.user import User
from models.workspace import Workspace
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "workspace"


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Email único
    q = await db.execute(select(User).where(User.email == body.email))
    if q.scalar_one_or_none():
        raise HTTPException(400, "Email ya registrado")

    # Workspace
    slug = _slugify(body.workspace_name)
    counter = 0
    base_slug = slug
    while True:
        q = await db.execute(select(Workspace).where(Workspace.slug == slug))
        if q.scalar_one_or_none() is None:
            break
        counter += 1
        slug = f"{base_slug}-{counter}"

    ws = Workspace(name=body.workspace_name, slug=slug, plan="free")
    db.add(ws)
    await db.flush()

    user = User(
        workspace_id=ws.id,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
        license_number=body.license_number,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == body.email))
    user = q.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(403, "Usuario deshabilitado")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Contraseña actual incorrecta")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}
