"""Pydantic v2 schemas para el modulo DMO (WO F2-01).

`workspace_id` NO va en los Create/Update: lo deriva el endpoint del contexto
de auth del tenant. Solo aparece en los Out.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import time, date, datetime


# ---------- Coach (catalogo global) ----------

class CoachBase(BaseModel):
    name: str
    description: Optional[str] = None
    photo_url: Optional[str] = None
    source_url: Optional[str] = None
    is_official: bool = False


class CoachCreate(CoachBase):
    pass


class CoachUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    source_url: Optional[str] = None
    is_official: Optional[bool] = None


class CoachOut(CoachBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    templates_count: Optional[int] = 0


# ---------- DMO Block ----------

class DmoBlockBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: time
    end_time: time
    color: str = "#3b82f6"
    sort_order: int = 0
    is_money_block: bool = False
    metric_type: str = "checkbox"  # checkbox | quantity
    metric_label: Optional[str] = None
    metric_goal: int = 0


class DmoBlockCreate(DmoBlockBase):
    pass


class DmoBlockOut(DmoBlockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int


# ---------- DMO Template ----------

class DmoTemplateBase(BaseModel):
    coach_id: int
    name: str
    description: Optional[str] = None
    market: Optional[str] = None
    is_active: bool = True
    is_office_default: bool = False


class DmoTemplateCreate(DmoTemplateBase):
    blocks: List[DmoBlockCreate] = Field(default_factory=list)


class DmoTemplateUpdate(BaseModel):
    coach_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    market: Optional[str] = None
    is_active: Optional[bool] = None
    is_office_default: Optional[bool] = None
    blocks: Optional[List[DmoBlockCreate]] = None


class DmoTemplateOut(DmoTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: Optional[int] = None  # NULL = catalogo oficial global
    coach_name: Optional[str] = None
    is_official: bool = False  # True si es del catalogo global (workspace_id NULL)
    blocks: List[DmoBlockOut] = Field(default_factory=list)
    assignments_count: Optional[int] = 0
    created_at: datetime


# ---------- Vendor (para la pantalla de asignaciones) ----------

class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    daily_conversations_goal: int = 0


# ---------- Asignacion vendedor -> template ----------

class DmoAssignmentCreate(BaseModel):
    vendor_id: int
    template_id: int


class DmoAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    template_id: int
    template_name: Optional[str] = None
    coach_name: Optional[str] = None
    assigned_at: datetime


# ---------- Log diario ----------

class DmoLogCreate(BaseModel):
    block_id: int
    date: date
    completed: bool = False
    metric_value: int = 0
    notes: Optional[str] = None


class DmoLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    block_id: int
    date: date
    completed: bool
    metric_value: int
    notes: Optional[str] = None
    created_at: datetime


# ---------- Dia (lo que renderiza la pantalla del vendedor) ----------

class DmoDayOut(BaseModel):
    date: date
    template: Optional[DmoTemplateOut] = None
    blocks: List[DmoBlockOut]
    logs: List[DmoLogOut]
    conversations_goal: int
    conversations_done: int
    completion_pct: int
