from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(30), default="asesor")
    # Vocabulario de roles CANONICO y UNICO de la suite: jerarquia del rubro
    # inmobiliario, 4 niveles (WO F6-06):
    #   broker > administrador > coordinador > asesor
    # Cada nivel incluye el alcance de los de abajo (ver core.security.ROLE_HIERARCHY,
    # fuente unica). Mapeo desde el vocabulario anterior (admin|supervisor|vendedor):
    # admin->broker, supervisor->coordinador, vendedor->asesor; `administrador` es
    # un nivel NUEVO (se asigna a mano desde Equipo). Migracion de datos:
    # f1e2d3c4b5a6_rework_role_hierarchy.
    license_number = Column(String(80), nullable=True)  # matrícula (broker/asesor)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # === Asignacion de leads / round-robin (portado de AgentFlow.users) ===
    is_available = Column(Boolean, default=False)  # disponible para recibir leads
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)  # ultimo lead asignado (round-robin)
    # AgentFlow.telefono_personal -> personal_phone (WhatsApp para notificar leads)
    personal_phone = Column(String(40), nullable=True)
    # AgentFlow.meta_conversaciones_diaria -> daily_conversations_goal
    daily_conversations_goal = Column(Integer, default=20)

    # Vendedor de ejemplo generado por el onboarding self-service (WO F5-03).
    # Nunca se crea/edita por el registro normal; solo por services/demo_service.
    # Se borra en bloque sin tocar miembros reales del equipo (regla #11).
    is_demo = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
