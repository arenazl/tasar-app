"""Pydantic v2 schemas para Deal (pipeline del CRM unificado, WO F1-01).

`workspace_id` NO va en Create/Update: lo deriva el endpoint (F2) del contexto
de auth del tenant. Solo aparece en el Out.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class DealBase(BaseModel):
    client_id: int
    property_id: int
    vendor_id: int
    stage: str = "captado"  # captado | publicado | visita | reserva | boleto | escrituracion
    negotiated_price: Optional[float] = None
    currency: str = "USD"
    estimated_commission: Optional[float] = None
    probability_pct: int = 10
    estimated_close_date: Optional[date] = None
    notes: Optional[str] = None


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    client_id: Optional[int] = None
    property_id: Optional[int] = None
    vendor_id: Optional[int] = None
    stage: Optional[str] = None
    negotiated_price: Optional[float] = None
    currency: Optional[str] = None
    estimated_commission: Optional[float] = None
    probability_pct: Optional[int] = None
    estimated_close_date: Optional[date] = None
    notes: Optional[str] = None


class DealOut(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_at: datetime
    updated_at: datetime
