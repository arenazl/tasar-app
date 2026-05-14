from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AdjustmentIn(BaseModel):
    factor: str
    description: Optional[str] = None
    coefficient: float
    amount: Optional[float] = None


class AdjustmentOut(AdjustmentIn):
    id: int

    class Config:
        from_attributes = True


class ComparableBase(BaseModel):
    source: str = "manual"
    source_url: Optional[str] = None
    title: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_m2: Optional[float] = None
    covered_area_m2: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    age_years: Optional[int] = None
    condition: Optional[str] = None
    price: float
    currency: str = "USD"
    notes: Optional[str] = None


class ComparableCreate(ComparableBase):
    adjustments: List[AdjustmentIn] = []


class ComparableOut(ComparableBase):
    id: int
    price_per_m2: Optional[float] = None
    adjusted_price: Optional[float] = None
    adjusted_price_per_m2: Optional[float] = None
    weight: float
    adjustments: List[AdjustmentOut] = []
    source_type: Optional[str] = "manual"
    ai_reason: Optional[str] = None
    source_property_id: Optional[int] = None
    external_listing_id: Optional[int] = None

    class Config:
        from_attributes = True


class MarketStudyCreate(BaseModel):
    property_id: int
    method: str = "homogenization"
    notes: Optional[str] = None


class MarketStudyOut(BaseModel):
    id: int
    workspace_id: int
    property_id: int
    created_by: int
    status: str
    method: str
    suggested_value_min: Optional[float] = None
    suggested_value_max: Optional[float] = None
    suggested_value_mode: Optional[float] = None
    confidence_score: Optional[float] = None
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[str] = None
    notes: Optional[str] = None
    comparables: List[ComparableOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
