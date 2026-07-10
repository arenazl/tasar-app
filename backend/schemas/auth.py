from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    workspace_name: str
    license_number: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    workspace_id: int
    license_number: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    # is_available alimenta el round-robin de leads (WO F4-05). Se expone en
    # /me para que el front pueda mostrar/editar el switch de disponibilidad.
    is_available: bool = False
    personal_phone: Optional[str] = None
    daily_conversations_goal: Optional[int] = None
    # Vendedor de ejemplo del onboarding self-service (WO F5-03).
    is_demo: bool = False

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()
