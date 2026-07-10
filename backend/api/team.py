"""Gestion de equipo del workspace (WO F4-05).

Todo scoped al workspace del JWT (anti-cross-tenant). Autorizacion por rol real
(core.security.require_role):
  - VER equipo/invitaciones: admin | supervisor
  - INVITAR / reenviar / cancelar / editar rol / (des)activar: admin

El alta via token (aceptar invitacion) es PUBLICA y vive en api/auth.py (reusa
el flujo de registro). Aca solo se emiten/gestionan las invitaciones.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import get_current_user, require_role
from models.user import User
from models.invitation import (
    Invitation, STATUS_PENDIENTE, STATUS_ACEPTADA, STATUS_CANCELADA,
)
from schemas.team import (
    TeamMemberOut, MemberUpdate, InviteCreate, InvitationOut, VALID_ROLES,
)
from services.email_service import send_team_invitation


router = APIRouter(prefix="/api/team", tags=["team"])

INVITE_TTL = timedelta(days=7)


# ── Miembros ────────────────────────────────────────────────────────────────

@router.get("/members", response_model=list[TeamMemberOut])
async def list_members(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    rows = (await db.execute(
        select(User).where(User.workspace_id == user.workspace_id).order_by(User.full_name)
    )).scalars().all()
    return [TeamMemberOut.model_validate(u) for u in rows]


@router.patch("/members/{user_id}", response_model=TeamMemberOut)
async def update_member(
    user_id: int,
    body: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """Cambia rol y/o (des)activa un miembro. Solo admin. Scoped al workspace."""
    target = (await db.execute(
        select(User).where(User.id == user_id, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Miembro no encontrado")

    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        if data["role"] not in VALID_ROLES:
            raise HTTPException(400, f"Rol invalido (debe ser uno de {sorted(VALID_ROLES)})")
        # No permitir que el admin se quite el ultimo admin activo del workspace.
        if target.id == user.id and data["role"] != "admin":
            others = (await db.execute(
                select(User).where(
                    User.workspace_id == user.workspace_id,
                    User.role == "admin",
                    User.is_active == True,   # noqa: E712
                    User.id != user.id,
                )
            )).scalars().first()
            if not others:
                raise HTTPException(400, "No podes quitarte el rol admin: sos el unico admin activo del workspace")
        target.role = data["role"]

    if "is_active" in data and data["is_active"] is not None:
        if target.id == user.id and not data["is_active"]:
            raise HTTPException(400, "No podes desactivar tu propia cuenta")
        target.is_active = data["is_active"]

    await db.commit()
    await db.refresh(target)
    return TeamMemberOut.model_validate(target)


# ── Invitaciones ──────────────────────────────────────────────────────────────

async def _emit_invitation(db: AsyncSession, inv: Invitation, inviter: User) -> None:
    """Setea token + expiry, marca pendiente y despacha el email (best-effort:
    un fallo del mail NO tira la operacion -- el admin puede reenviar)."""
    inv.token = secrets.token_urlsafe(32)
    inv.status = STATUS_PENDIENTE
    inv.expires_at = datetime.now(timezone.utc) + INVITE_TTL
    inv.accepted_at = None
    await db.flush()

    from models.workspace import Workspace
    ws = (await db.execute(select(Workspace).where(Workspace.id == inv.workspace_id))).scalar_one_or_none()
    accept_url = f"{settings.FRONTEND_URL.rstrip('/')}/invitacion/{inv.token}"
    await send_team_invitation(
        to=inv.email,
        workspace_name=ws.name if ws else "tu inmobiliaria",
        role=inv.role,
        inviter_name=inviter.full_name,
        accept_url=accept_url,
    )


@router.get("/invitations", response_model=list[InvitationOut])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    rows = (await db.execute(
        select(Invitation)
        .where(Invitation.workspace_id == user.workspace_id)
        .order_by(Invitation.created_at.desc())
    )).scalars().all()
    return [InvitationOut.model_validate(i) for i in rows]


@router.post("/invitations", response_model=InvitationOut)
async def create_invitation(
    body: InviteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    email = body.email.lower().strip()
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"Rol invalido (debe ser uno de {sorted(VALID_ROLES)})")

    # Ya es miembro del workspace?
    existing_user = (await db.execute(
        select(User).where(User.workspace_id == user.workspace_id, User.email == email)
    )).scalar_one_or_none()
    if existing_user:
        raise HTTPException(409, "Ese email ya pertenece a un miembro del workspace")

    # Invitacion pendiente para ese email en este workspace -> se reusa la fila
    # (re-emite token + expiry) en vez de acumular duplicados.
    inv = (await db.execute(
        select(Invitation).where(
            Invitation.workspace_id == user.workspace_id,
            Invitation.email == email,
            Invitation.status == STATUS_PENDIENTE,
        )
    )).scalar_one_or_none()
    if inv:
        inv.role = body.role
        inv.full_name = body.full_name
    else:
        inv = Invitation(
            workspace_id=user.workspace_id,
            email=email,
            role=body.role,
            full_name=body.full_name,
            invited_by=user.id,
        )
        db.add(inv)

    await _emit_invitation(db, inv, user)
    await db.commit()
    await db.refresh(inv)
    return InvitationOut.model_validate(inv)


async def _get_invitation_scoped(db: AsyncSession, inv_id: int, user: User) -> Invitation:
    inv = (await db.execute(
        select(Invitation).where(
            Invitation.id == inv_id, Invitation.workspace_id == user.workspace_id
        )
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invitacion no encontrada")
    return inv


@router.post("/invitations/{inv_id}/resend", response_model=InvitationOut)
async def resend_invitation(
    inv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    inv = await _get_invitation_scoped(db, inv_id, user)
    if inv.status == STATUS_ACEPTADA:
        raise HTTPException(400, "Esa invitacion ya fue aceptada")
    await _emit_invitation(db, inv, user)  # nuevo token + expiry + reenvio
    await db.commit()
    await db.refresh(inv)
    return InvitationOut.model_validate(inv)


@router.delete("/invitations/{inv_id}")
async def cancel_invitation(
    inv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    inv = await _get_invitation_scoped(db, inv_id, user)
    if inv.status == STATUS_ACEPTADA:
        raise HTTPException(400, "Esa invitacion ya fue aceptada; no se puede cancelar")
    inv.status = STATUS_CANCELADA
    await db.commit()
    return {"ok": True}
