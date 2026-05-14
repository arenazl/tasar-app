"""MarketListing — base de datos en vivo de propiedades del mercado.

Es la fuente que alimenta el módulo "Comparables (live)" del screenshot real.
~500 listings sintéticos (CABA + AMBA) en el seed. Cada workspace ve la misma
base; ahí buscamos comparables para tasaciones.

Diferente de:
- Property: inmuebles del workspace (los que TU inmobiliaria tasa o vende)
- ExternalListing: cache puntual de scraping de un URL específico
- MarketListing: el universo de comparables disponibles, alimentado por seed/scraping batch
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func, Index
from core.database import Base


class MarketListing(Base):
    __tablename__ = "market_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # No tiene workspace_id — es global. Todos los workspaces ven la misma base.
    source = Column(String(40), default="seed", index=True)  # seed | zonaprop | argenprop | mercadolibre
    source_url = Column(String(500), nullable=True)
    external_id = Column(String(80), nullable=True, index=True)  # ID en el portal origen

    # Identificación
    title = Column(String(200), nullable=False)
    property_type = Column(String(40), nullable=False, index=True)
    operation = Column(String(20), default="venta", index=True)

    # Ubicación
    province = Column(String(80), nullable=True, index=True)
    city = Column(String(120), nullable=True, index=True)
    neighborhood = Column(String(120), nullable=True, index=True)
    address = Column(String(250), nullable=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)

    # Características
    total_area_m2 = Column(Float, nullable=True)
    covered_area_m2 = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True, index=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    age_years = Column(Integer, nullable=True)
    condition = Column(String(40), nullable=True, index=True)
    orientation = Column(String(20), nullable=True)
    floor = Column(Integer, nullable=True)
    parking_spots = Column(Integer, nullable=True)

    # Precio
    price = Column(Float, nullable=False)
    currency = Column(String(5), default="USD")
    price_per_m2 = Column(Float, nullable=True, index=True)

    # Estado del listing
    status = Column(String(20), default="active", index=True)  # active | sold | removed | expired
    days_on_market = Column(Integer, default=0)

    # Metadata
    description = Column(Text, nullable=True)
    photos_count = Column(Integer, default=0)
    raw_data = Column(Text, nullable=True)

    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_listing_city_type', 'city', 'property_type'),
        Index('ix_listing_active', 'status', 'city', 'property_type'),
    )
