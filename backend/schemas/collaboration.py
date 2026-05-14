from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CollaborationInvite(BaseModel):
    market_study_id: int
    user_id: int
    role: str = "contributor"


class CollaborationOpinion(BaseModel):
    opinion_value: float
    opinion_note: Optional[str] = None


class CollaborationOut(BaseModel):
    id: int
    market_study_id: int
    user_id: int
    role: str
    opinion_value: Optional[float] = None
    opinion_note: Optional[str] = None
    joined_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    body: str
    anchor: Optional[str] = None
    parent_id: Optional[int] = None


class CommentOut(BaseModel):
    id: int
    market_study_id: int
    user_id: int
    parent_id: Optional[int] = None
    body: str
    anchor: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConsensusOut(BaseModel):
    market_study_id: int
    participants: int
    avg_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    std_dev: Optional[float] = None
    agreement_score: Optional[float] = None  # 0-1
    opinions: List[CollaborationOut] = []
