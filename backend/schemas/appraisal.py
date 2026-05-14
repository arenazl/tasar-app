from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AppraisalCreate(BaseModel):
    property_id: int
    market_study_id: Optional[int] = None
    purpose: str
    final_value: Optional[float] = None  # nullable hasta firmar
    currency: str = "USD"
    methodology: Optional[str] = None
    observations: Optional[str] = None
    legal_remarks: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    client_email: Optional[str] = None


class AppraisalSignatureOut(BaseModel):
    id: int
    user_id: int
    signed_at: datetime

    class Config:
        from_attributes = True


class AppraisalOut(BaseModel):
    id: int
    code: Optional[str] = None
    workspace_id: int
    property_id: int
    market_study_id: Optional[int] = None
    created_by: int
    assigned_to: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    purpose: str
    status: str
    # Análisis embebido
    suggested_value_min: Optional[float] = None
    suggested_value_max: Optional[float] = None
    suggested_value_mode: Optional[float] = None
    suggested_value_per_m2: Optional[float] = None
    confidence_score: Optional[float] = None
    cap_rate: Optional[float] = None
    rental_estimate: Optional[float] = None
    comparables_count: Optional[int] = 0
    method: Optional[str] = "hybrid"
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    # Valor final (nullable hasta firma)
    final_value: Optional[float] = None
    currency: str = "USD"
    methodology: Optional[str] = None
    observations: Optional[str] = None
    legal_remarks: Optional[str] = None
    pdf_url: Optional[str] = None
    delivered_at: Optional[datetime] = None
    signatures: List[AppraisalSignatureOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
