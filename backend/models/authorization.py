"""Authorization — autorización de venta firmada (portado de AgentFlow.autorizaciones).

Nueva entidad del CRM unificado (WO F1-01). Multi-tenant: lleva workspace_id.
Representa el contrato de autorización que el propietario firma con la agencia
para comercializar una propiedad (con o sin exclusividad).

`currency` y `notes` se portan de AgentFlow (moneda / observaciones): un
min_price sin moneda es ambiguo, por eso se conserva la moneda.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, func
from core.database import Base


class Authorization(Base):
    __tablename__ = "authorizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    # AgentFlow.captador_id -> captador_id (agente que firmó la autorización)
    captador_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # AgentFlow.fecha_firma -> signed_date
    signed_date = Column(Date, nullable=False)
    # AgentFlow.fecha_vencimiento -> expiry_date
    expiry_date = Column(Date, nullable=False)

    # AgentFlow.precio_minimo -> min_price
    min_price = Column(Float, nullable=False)
    # AgentFlow.moneda -> currency
    currency = Column(String(5), default="USD")
    # AgentFlow.comision_pct -> commission_pct
    commission_pct = Column(Float, default=4.0)
    # AgentFlow.exclusividad -> exclusivity
    exclusivity = Column(Boolean, default=False)

    pdf_url = Column(String(500), nullable=True)
    # AgentFlow.observaciones -> notes
    notes = Column(Text, nullable=True)

    # AgentFlow.estado -> status
    status = Column(String(20), default="activa", index=True)
    # activa | vencida | ejecutada | cancelada

    created_at = Column(DateTime(timezone=True), server_default=func.now())
