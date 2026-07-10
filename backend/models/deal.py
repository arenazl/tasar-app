"""Deal — operación/negocio del pipeline (portado de AgentFlow.pipeline_deals).

Nueva entidad del CRM unificado (WO F1-01). Multi-tenant: lleva workspace_id.
El `stage` usa las 6 etapas legales del circuito inmobiliario argentino
(captado -> publicado -> visita -> reserva -> boleto -> escrituracion).

`currency` y `notes` se portan de AgentFlow (moneda / notas): un
negotiated_price sin moneda es ambiguo, por eso se conserva la moneda.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from core.database import Base


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    # AgentFlow.vendedor_id -> vendor_id
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # AgentFlow.etapa -> stage
    stage = Column(String(20), default="captado", index=True)
    # captado | publicado | visita | reserva | boleto | escrituracion

    # AgentFlow.precio_negociado -> negotiated_price
    negotiated_price = Column(Float, nullable=True)
    # AgentFlow.moneda -> currency
    currency = Column(String(5), default="USD")
    # AgentFlow.comision_estimada -> estimated_commission
    estimated_commission = Column(Float, nullable=True)
    # AgentFlow.probabilidad_pct -> probability_pct
    probability_pct = Column(Integer, default=10)
    # AgentFlow.fecha_estimada_cierre -> estimated_close_date
    estimated_close_date = Column(Date, nullable=True)
    # AgentFlow.notas -> notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
