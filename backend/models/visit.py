"""Visit — visita de un cliente a una propiedad (portado de AgentFlow.visitas).

Nueva entidad del CRM unificado (WO F1-01). Multi-tenant: lleva workspace_id.
Mapeo de campos AgentFlow (castellano) -> suite (ingles) documentado en cada
columna. Convencion de la casa: los campos "enum" son String con comentario
de valores validos (no SAEnum).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from core.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    # AgentFlow.vendedor_id -> vendor_id
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # AgentFlow.fecha_hora -> scheduled_at
    scheduled_at = Column(DateTime(timezone=True), nullable=False)

    # AgentFlow.estado -> status
    status = Column(String(20), default="agendada", index=True)
    # agendada | concretada | cancelada | ausente

    # AgentFlow.resultado -> result
    result = Column(String(20), nullable=True)
    # interesado | no_interesado | hizo_oferta | indeciso | sin_resultado

    # AgentFlow.notas_voz -> voice_notes
    voice_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
