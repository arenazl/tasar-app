"""Appraisal — entidad principal del workflow TasAR (la TR-XXXX del screenshot real).

Diseño post-refactor:
- Análisis embebido (suggested_value, confidence, methodology — antes era market_study aparte)
- Asignación a tasador
- Workflow: solicitada → en_analisis → en_revision → entregada
- Comparables linkeados via tabla AppraisalComparable (link a market_listings)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from core.database import Base


class Appraisal(Base):
    __tablename__ = "appraisals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=True, index=True)  # TR-2451

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Cliente que pide la tasación (puede ser un banco / fondo / particular)
    client_name = Column(String(200), nullable=True)        # ej "Banco Río Plata"
    client_contact = Column(String(200), nullable=True)     # ej "Mariana Sosa"
    client_email = Column(String(200), nullable=True)

    purpose = Column(String(60), nullable=False)            # venta | sucesion | judicial | hipoteca | seguro | otro
    status = Column(String(30), default="solicitada", index=True)
    # solicitada | en_analisis | en_revision | aprobada | entregada | rechazada

    # === ANÁLISIS EMBEBIDO (antes era market_study) ===
    suggested_value_min = Column(Float, nullable=True)
    suggested_value_max = Column(Float, nullable=True)
    suggested_value_mode = Column(Float, nullable=True)     # estimación principal (TASAR USD 248.300)
    suggested_value_per_m2 = Column(Float, nullable=True)   # USD 3.028
    confidence_score = Column(Float, nullable=True)         # 0.87
    cap_rate = Column(Float, nullable=True)                 # 4.8 (porcentaje)
    rental_estimate = Column(Float, nullable=True)          # 1.244 USD mensuales
    comparables_count = Column(Integer, default=0)          # 34 comparables analizados
    method = Column(String(40), default="hybrid")           # homogenization | ai_score | hybrid

    ai_summary = Column(Text, nullable=True)
    ai_recommendations = Column(Text, nullable=True)
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    # === VALOR FINAL (firmado por el tasador, lo que va al PDF) ===
    final_value = Column(Float, nullable=True)              # nullable hasta que esté firmada
    currency = Column(String(5), default="USD")

    methodology = Column(Text, nullable=True)
    observations = Column(Text, nullable=True)
    legal_remarks = Column(Text, nullable=True)

    pdf_url = Column(String(500), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AppraisalSignature(Base):
    __tablename__ = "appraisal_signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    appraisal_id = Column(Integer, ForeignKey("appraisals.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    signed_at = Column(DateTime(timezone=True), server_default=func.now())
    signature_hash = Column(String(255), nullable=False)


class AppraisalComparable(Base):
    """Link entre Appraisal ↔ MarketListing (los 34 comparables del screenshot).

    Cada comparable trae su match score (precalculado) + ajustes aplicados +
    si el tasador lo confirmó o lo está descartando. Reemplaza el viejo `Comparable`
    que estaba dentro de market_study.
    """
    __tablename__ = "appraisal_comparables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    appraisal_id = Column(Integer, ForeignKey("appraisals.id"), nullable=False, index=True)
    market_listing_id = Column(Integer, ForeignKey("market_listings.id"), nullable=False, index=True)

    match_score = Column(Float, nullable=True)              # 0.0 - 1.0
    distance_m = Column(Integer, nullable=True)             # metros desde el target
    weight = Column(Float, default=1.0)

    # Override del precio si el tasador lo ajustó
    adjusted_price = Column(Float, nullable=True)
    adjusted_price_per_m2 = Column(Float, nullable=True)
    adjustments_json = Column(Text, nullable=True)          # [{factor, coefficient, description}]

    # Estado: included (default) | excluded | manual
    status = Column(String(20), default="included")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
