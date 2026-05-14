from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func, UniqueConstraint
from core.database import Base


class ExternalListing(Base):
    """Propiedad scrapeada de un portal externo (ZonaProp, Argenprop, MercadoLibre).

    Diferente de Property (propiedades propias del workspace):
    - No las gestionamos — solo registramos snapshots
    - Sirven como cache para no re-scrapear la misma URL
    - Alimentan price_history y aparecen como sugerencias en estudios futuros
    """
    __tablename__ = "external_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    source = Column(String(40), nullable=False, index=True)  # zonaprop | argenprop | mercadolibre | other
    source_url = Column(String(500), nullable=False, index=True)
    source_id = Column(String(80), nullable=True)  # ID interno del portal si lo extrajimos

    title = Column(String(250), nullable=False)
    property_type = Column(String(40), nullable=False, index=True)
    operation = Column(String(20), default="venta")

    province = Column(String(80), nullable=True, index=True)
    city = Column(String(120), nullable=True, index=True)
    neighborhood = Column(String(120), nullable=True, index=True)
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

    description = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)  # JSON con todo lo que Claude extrajo

    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('workspace_id', 'source_url', name='uq_external_workspace_url'),
    )
