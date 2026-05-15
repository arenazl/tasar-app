"""Client — CRM mínimo del workspace."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    type = Column(String(40), default="particular")
    # banco | fondo | estudio | inmobiliaria | particular

    contact_name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(300), nullable=True)
    tax_id = Column(String(40), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
