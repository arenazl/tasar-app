"""ExpressValuation — tasacion express anclada (WO F1-03).

El gancho comercial de la suite: valuacion instantanea anclada a comparables
reales de `market_listings` (motor `anchor_service`) + ajuste LLM anclado, con
informe brandeado. Cada valuacion se persiste completa (input + output + ancla
usada) para trazabilidad y para poder regenerar el PDF sin recalcular.

Multi-tenant: `workspace_id` (FK workspaces + indice), como toda tabla nueva.
`input_json` / `output_json` guardan el contrato completo; las columnas
denormalizadas (anchor_scope, price_per_m2_typical, etc.) son para listar/filtrar
sin parsear el JSON.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, func
from core.database import Base


class ExpressValuation(Base):
    __tablename__ = "express_valuations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # === Datos de la propiedad evaluada (denormalizados del input) ===
    property_type = Column(String(40), nullable=False, index=True)
    province = Column(String(80), nullable=True)
    city = Column(String(120), nullable=True)
    neighborhood = Column(String(120), nullable=True)
    address = Column(String(250), nullable=True)
    total_area_m2 = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    condition = Column(String(40), nullable=True)

    # === Ancla usada (resumen; el detalle va en output_json) ===
    anchor_scope = Column(String(20), nullable=True, index=True)   # zona | provincia | nacional | sin_datos
    anchor_count = Column(Integer, nullable=True)
    anchor_median_ppm2 = Column(Float, nullable=True)

    # === Resultado (denormalizado del output) ===
    price_per_m2_typical = Column(Float, nullable=True)
    total_price_usd = Column(Float, nullable=True)
    currency = Column(String(5), default="USD")
    confidence = Column(String(10), nullable=True)                 # alta | media | baja
    ai_used = Column(Boolean, default=False)                       # False => fallback deterministico

    # === Contratos completos ===
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
