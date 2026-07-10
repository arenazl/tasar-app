"""Client — CRM unificado del workspace (TasAR + CRM de AgentFlow).

Ampliado en el WO F1-01: se portan las capacidades de lead/CRM que vivian en
`clientes` de AgentFlow sobre el `clients` multi-tenant de TasAR. El `type`
existente (banco|fondo|estudio|inmobiliaria|particular) QUEDA: un mismo cliente
puede ser un particular Y un lead comercial a la vez. Los campos de lead/CRM
(lead_status, temperature, origin, preferencias, assigned_to) se agregan como
nullable con default Python-side, para no romper filas existentes.

Convencion de la casa (TasAR): los campos "enum" se guardan como String con un
comentario que lista los valores validos (no se usa SAEnum como en AgentFlow),
para mantener el DDL portable a MySQL sin tipos ENUM nativos.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
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

    # === CRM / lead (portado de AgentFlow.clientes) ===
    # AgentFlow.estado -> lead_status
    lead_status = Column(String(20), default="nuevo", index=True)
    # nuevo | contactado | calificado | cita | propuesta | cerrado | perdido
    # AgentFlow.temperatura -> temperature
    temperature = Column(String(10), nullable=True)
    # caliente | tibio | frio
    # AgentFlow.origen -> origin (se agrega `whatsapp` respecto del origen de AgentFlow)
    origin = Column(String(20), default="web")
    # web | walk_in | referido | zonaprop | argenprop | redes | whatsapp | otro
    # AgentFlow.vendedor_id -> assigned_to (vendedor asignado al lead)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # === Preferencias del comprador (portado de AgentFlow.clientes.pref_*) ===
    pref_zona = Column(String(150), nullable=True)
    pref_m2_min = Column(Integer, nullable=True)
    pref_m2_max = Column(Integer, nullable=True)
    pref_ambientes = Column(Integer, nullable=True)
    # AgentFlow.pref_presupuesto_min/max -> pref_budget_min/max
    pref_budget_min = Column(Float, nullable=True)
    pref_budget_max = Column(Float, nullable=True)
    # AgentFlow.pref_moneda -> pref_currency
    pref_currency = Column(String(5), default="USD")

    last_contact_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
