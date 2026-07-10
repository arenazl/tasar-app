"""Pydantic v2 schemas para Visit (CRM unificado, WO F1-01).

`workspace_id` NO va en Create/Update: lo deriva el endpoint (F2) del contexto
de auth del tenant. Solo aparece en el Out.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class VisitBase(BaseModel):
    client_id: int
    property_id: int
    vendor_id: int
    scheduled_at: datetime
    status: str = "agendada"  # agendada | concretada | cancelada | ausente
    result: Optional[str] = None  # interesado | no_interesado | hizo_oferta | indeciso | sin_resultado
    voice_notes: Optional[str] = None


class VisitCreate(VisitBase):
    pass


class VisitUpdate(BaseModel):
    client_id: Optional[int] = None
    property_id: Optional[int] = None
    vendor_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    result: Optional[str] = None
    voice_notes: Optional[str] = None


class VisitOut(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_at: datetime
