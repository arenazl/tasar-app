from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from core.database import Base


class MarketStudy(Base):
    __tablename__ = "market_studies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String(20), default="draft")  # draft | in_review | published | archived
    method = Column(String(40), default="homogenization")  # homogenization | ai_score | hybrid

    # Resultado calculado
    suggested_value_min = Column(Float, nullable=True)
    suggested_value_max = Column(Float, nullable=True)
    suggested_value_mode = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0-1

    # AI
    ai_summary = Column(Text, nullable=True)
    ai_recommendations = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Comparable(Base):
    __tablename__ = "comparables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_study_id = Column(Integer, ForeignKey("market_studies.id"), nullable=False, index=True)

    source = Column(String(40), default="manual")  # manual | zonaprop | argenprop | mercadolibre
    source_url = Column(String(500), nullable=True)

    # IA-first metadata
    source_type = Column(String(30), default="manual")  # manual | ai_suggested | scraped | workspace
    ai_reason = Column(Text, nullable=True)  # razón que dio Claude para incluirlo
    source_property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)  # ref a propiedad del workspace
    external_listing_id = Column(Integer, ForeignKey("external_listings.id"), nullable=True)  # ref a scraping

    title = Column(String(200), nullable=False)
    address = Column(String(250), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    total_area_m2 = Column(Float, nullable=True)
    covered_area_m2 = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    age_years = Column(Integer, nullable=True)
    condition = Column(String(40), nullable=True)

    price = Column(Float, nullable=False)
    currency = Column(String(5), default="USD")
    price_per_m2 = Column(Float, nullable=True)

    # Homogeneización
    adjusted_price = Column(Float, nullable=True)
    adjusted_price_per_m2 = Column(Float, nullable=True)
    weight = Column(Float, default=1.0)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Adjustment(Base):
    __tablename__ = "adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comparable_id = Column(Integer, ForeignKey("comparables.id"), nullable=False, index=True)

    factor = Column(String(50), nullable=False)  # area | condition | age | location | orientation | other
    description = Column(String(250), nullable=True)
    coefficient = Column(Float, nullable=False)  # 1.05 = +5%
    amount = Column(Float, nullable=True)
