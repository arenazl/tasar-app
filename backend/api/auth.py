from datetime import datetime, timezone

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
from models.invitation import (
    Invitation, STATUS_PENDIENTE, STATUS_ACEPTADA, STATUS_EXPIRADA, STATUS_CANCELADA,
)
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from schemas.team import InvitationInfo, AcceptInvite, MeProfileUpdate


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
        # El que registra la inmobiliaria es el titular: broker (nivel maximo,
        # WO F6-06).
        role="broker",
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


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: MeProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """El propio usuario edita su perfil (self-service, cualquier rol).
    `is_available` alimenta el round-robin de leads (WO F4-05)."""
    data = body.model_dump(exclude_unset=True)
    for field in ("is_available", "personal_phone", "daily_conversations_goal"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── Invitaciones: alta via token (PUBLICO, sin auth) — WO F4-05 ──────────────

async def _load_pending_invitation(db: AsyncSession, token: str) -> Invitation | None:
    return (await db.execute(
        select(Invitation).where(Invitation.token == token)
    )).scalar_one_or_none()


def _is_expired(expires_at) -> bool:
    """True si la invitacion vencio. Robusto al hecho de que MySQL/aiomysql y
    SQLite devuelven DateTime SIN tzinfo aunque se haya guardado UTC-aware:
    normalizamos el valor leido a UTC antes de comparar (siempre guardamos UTC)."""
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


@router.get("/invitation/{token}", response_model=InvitationInfo)
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    """Datos publicos de una invitacion para la pantalla de aceptacion.
    No revela nada sensible: email, rol y nombre del workspace al que se invito."""
    inv = await _load_pending_invitation(db, token)
    if not inv:
        raise HTTPException(404, "Invitacion no encontrada")

    ws = (await db.execute(select(Workspace).where(Workspace.id == inv.workspace_id))).scalar_one_or_none()
    workspace_name = ws.name if ws else ""

    valid, reason = True, None
    if inv.status == STATUS_ACEPTADA:
        valid, reason = False, "usada"
    elif inv.status == STATUS_CANCELADA:
        valid, reason = False, "revocada"
    elif _is_expired(inv.expires_at):
        valid, reason = False, "expirada"

    return InvitationInfo(
        email=inv.email, role=inv.role, workspace_name=workspace_name,
        full_name=inv.full_name, valid=valid, reason=reason,
    )


@router.post("/accept-invitation", response_model=TokenResponse)
async def accept_invitation(body: AcceptInvite, db: AsyncSession = Depends(get_db)):
    """Alta de un miembro via token de invitacion. El workspace y el rol vienen
    de la fila `invitations` (no del cliente): imposible auto-asignarse otro
    workspace/rol. Un solo uso (status -> aceptada)."""
    inv = await _load_pending_invitation(db, body.token)
    if not inv:
        raise HTTPException(404, "Invitacion no encontrada")
    if inv.status == STATUS_ACEPTADA:
        raise HTTPException(400, "Esa invitacion ya fue usada")
    if inv.status == STATUS_CANCELADA:
        raise HTTPException(400, "Esa invitacion fue revocada")
    if _is_expired(inv.expires_at):
        inv.status = STATUS_EXPIRADA
        await db.commit()
        raise HTTPException(400, "Esa invitacion expiro; pedile al admin que la reenvie")

    # Email unico global (misma regla que /register).
    if (await db.execute(select(User).where(User.email == inv.email))).scalar_one_or_none():
        raise HTTPException(409, "Ese email ya tiene una cuenta")

    user = User(
        workspace_id=inv.workspace_id,          # <- del token, no del cliente
        email=inv.email,
        password_hash=hash_password(body.password),
        full_name=(body.full_name or inv.full_name or inv.email.split("@")[0]),
        role=inv.role,                          # <- del token, no del cliente
    )
    db.add(user)
    inv.status = STATUS_ACEPTADA
    inv.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


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
