from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, func
from core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    # AgentFlow.propiedades.captador_id -> captador_id (agente que captó la propiedad).
    # Nullable: en TasAR una propiedad puede existir sin captador (flujo de tasación).
    captador_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Identificación
    title = Column(String(200), nullable=False)
    property_type = Column(String(40), nullable=False)  # casa | departamento | ph | terreno | local | oficina
    operation = Column(String(20), default="venta")  # venta | alquiler

    # Ubicación
    province = Column(String(80), nullable=False)
    city = Column(String(120), nullable=False)
    neighborhood = Column(String(120), nullable=True)
    address = Column(String(250), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Características físicas
    total_area_m2 = Column(Float, nullable=True)
    covered_area_m2 = Column(Float, nullable=True)
    rooms = Column(Integer, nullable=True)        # ambientes
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    parking_spots = Column(Integer, nullable=True)
    age_years = Column(Integer, nullable=True)
    condition = Column(String(40), nullable=True)  # a_estrenar | excelente | muy_bueno | bueno | regular | a_reciclar
    orientation = Column(String(20), nullable=True)
    floor = Column(Integer, nullable=True)

    # Económico
    asking_price = Column(Float, nullable=True)
    currency = Column(String(5), default="USD")
    # AgentFlow.propiedades.exclusividad -> exclusivity (autorización en exclusiva)
    exclusivity = Column(Boolean, default=False)

    # Descripción + metadata IA
    description = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)  # JSON con análisis de Claude

    # Dato de ejemplo generado por el onboarding self-service (WO F5-03). SIEMPRE
    # visible como tal (titulo con prefijo "[DEMO]") y borrable en bloque sin
    # tocar propiedades reales (regla #11 CLAUDE.md global).
    is_demo = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PropertyPhoto(Base):
    __tablename__ = "property_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    public_id = Column(String(200), nullable=True)  # Cloudinary
    caption = Column(String(200), nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
