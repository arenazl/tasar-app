from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from core.database import Base


class Collaboration(Base):
    __tablename__ = "collaborations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_study_id = Column(Integer, ForeignKey("market_studies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(30), default="contributor")  # owner | contributor | reviewer
    opinion_value = Column(Float, nullable=True)
    opinion_note = Column(Text, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class CollaborationComment(Base):
    __tablename__ = "collaboration_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_study_id = Column(Integer, ForeignKey("market_studies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("collaboration_comments.id"), nullable=True)
    body = Column(Text, nullable=False)
    anchor = Column(String(80), nullable=True)  # ej "comparable:12", "adjustment:area"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
