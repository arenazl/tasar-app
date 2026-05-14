from sqlalchemy import Column, Integer, String, DateTime, func
from core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    plan = Column(String(20), default="free")  # free | pro | enterprise
    created_at = Column(DateTime(timezone=True), server_default=func.now())
