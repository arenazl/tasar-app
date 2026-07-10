"""Schemas de gestion de equipo e invitaciones (WO F4-05)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Vocabulario de roles UNICO de la suite (WO F1-01). Se valida contra este set
# tanto al invitar como al editar el rol de un miembro.
VALID_ROLES = {"admin", "supervisor", "vendedor"}


class TeamMemberOut(BaseModel):
    """Un miembro del equipo del workspace (para la pantalla Equipo)."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_available: bool
    license_number: Optional[str] = None
    personal_phone: Optional[str] = None
    daily_conversations_goal: Optional[int] = None
    last_assigned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberUpdate(BaseModel):
    """Edicion de un miembro por el admin: cambiar rol y/o (des)activar."""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class InviteCreate(BaseModel):
    email: EmailStr
    role: str
    full_name: Optional[str] = None


class InvitationOut(BaseModel):
    id: int
    email: str
    role: str
    full_name: Optional[str] = None
    status: str
    invited_by: int
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Alta via token (flujo publico, sin auth) ---

class InvitationInfo(BaseModel):
    """Datos publicos de una invitacion para la pantalla de aceptacion."""
    email: str
    role: str
    workspace_name: str
    full_name: Optional[str] = None
    valid: bool
    reason: Optional[str] = None  # motivo si valid=False (expirada|usada|revocada)


class AcceptInvite(BaseModel):
    token: str
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


# --- Perfil propio (self-service, cualquier rol) ---

class MeProfileUpdate(BaseModel):
    """Campos que el propio usuario puede editar de su perfil. `is_available`
    alimenta el round-robin de asignacion de leads (services/bot_tools.py)."""
    is_available: Optional[bool] = None
    personal_phone: Optional[str] = None
    daily_conversations_goal: Optional[int] = None
