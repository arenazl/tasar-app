"""MonthlyReport — reporte macro del mercado.

Lo que se ve en el screenshot real como "Reportes" (Mayo 2026 +14.2% YoY 2.847 USD/m²
con botón Abrir PDF). Generado mensualmente, mismo para todos los workspaces.
Diferente del market_study que es ACM por inmueble.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func, UniqueConstraint
from core.database import Base


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)  # ej "#047"

    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)  # 1-12
    region = Column(String(80), default="CABA", index=True)
    kind = Column(String(20), default="mensual")  # mensual | trimestral | anual

    # KPIs principales
    tasar_index = Column(Float, nullable=True)        # ej 2.847
    median_price_per_m2 = Column(Float, nullable=True)
    yoy_change_pct = Column(Float, nullable=True)     # ej +14.2
    mom_change_pct = Column(Float, nullable=True)     # ej +1.2
    active_listings = Column(Integer, nullable=True)
    avg_days_on_market = Column(Integer, nullable=True)
    new_permits = Column(Integer, nullable=True)

    # Top 12 zonas (JSON)
    top_zones = Column(Text, nullable=True)  # [{zone:'Palermo', usd_m2: 3426}, ...]

    # PDF generado
    pdf_url = Column(String(500), nullable=True)
    pages_count = Column(Integer, default=0)

    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('period_year', 'period_month', 'region', name='uq_monthly_period_region'),
    )
