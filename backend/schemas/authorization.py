"""Pydantic v2 schemas para Authorization (autorización de venta, WO F1-01).

`workspace_id` NO va en Create/Update: lo deriva el endpoint (F2) del contexto
de auth del tenant. Solo aparece en el Out.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class AuthorizationBase(BaseModel):
    property_id: int
    captador_id: int
    signed_date: date
    expiry_date: date
    min_price: float
    currency: str = "USD"
    commission_pct: float = 4.0
    exclusivity: bool = False
    pdf_url: Optional[str] = None
    notes: Optional[str] = None
    status: str = "activa"  # activa | vencida | ejecutada | cancelada


class AuthorizationCreate(AuthorizationBase):
    pass


class AuthorizationUpdate(BaseModel):
    property_id: Optional[int] = None
    captador_id: Optional[int] = None
    signed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    min_price: Optional[float] = None
    currency: Optional[str] = None
    commission_pct: Optional[float] = None
    exclusivity: Optional[bool] = None
    pdf_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class AuthorizationOut(AuthorizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_at: datetime
