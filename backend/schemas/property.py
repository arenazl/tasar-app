from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PropertyBase(BaseModel):
    title: str
    property_type: str
    operation: str = "venta"
    province: str
    city: str
    neighborhood: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_m2: Optional[float] = None
    covered_area_m2: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spots: Optional[int] = None
    age_years: Optional[int] = None
    condition: Optional[str] = None
    orientation: Optional[str] = None
    floor: Optional[int] = None
    asking_price: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(PropertyBase):
    title: Optional[str] = None
    property_type: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None


class PropertyPhotoOut(BaseModel):
    id: int
    url: str
    caption: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class PropertyOut(PropertyBase):
    id: int
    workspace_id: int
    created_by: int
    ai_analysis: Optional[str] = None
    photos: List[PropertyPhotoOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
