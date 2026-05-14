from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from core.database import Base


class PriceHistoryPoint(Base):
    """Snapshots de precio por zona/tipo — alimenta el heatmap y la predicción IA."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    province = Column(String(80), nullable=False, index=True)
    city = Column(String(120), nullable=False, index=True)
    neighborhood = Column(String(120), nullable=True, index=True)
    property_type = Column(String(40), nullable=False)
    operation = Column(String(20), default="venta")

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    price_per_m2 = Column(Float, nullable=False)
    currency = Column(String(5), default="USD")

    sample_size = Column(Integer, default=1)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source = Column(String(40), default="manual")
