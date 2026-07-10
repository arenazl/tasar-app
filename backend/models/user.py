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
    role = Column(String(30), default="vendedor")
    # Vocabulario de roles UNIFICADO y UNICO de la suite (WO F1-01, normalizado
    # en fix transversal post F2-01): admin | supervisor | vendedor.
    # Mapeo desde legado: TasAR.tasador -> vendedor (el agente que tasa/vende es
    # el rol operativo base); AgentFlow.gerente / .coordinador -> supervisor;
    # vendedor -> vendedor; admin -> admin. Ver migracion de datos
    # f4a5b6c7d8e9_normalize_user_roles (down_revision=e6f7a8b9c0d1).
    license_number = Column(String(80), nullable=True)  # matrícula (vendedor/tasador)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # === Asignacion de leads / round-robin (portado de AgentFlow.users) ===
    is_available = Column(Boolean, default=False)  # disponible para recibir leads
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)  # ultimo lead asignado (round-robin)
    # AgentFlow.telefono_personal -> personal_phone (WhatsApp para notificar leads)
    personal_phone = Column(String(40), nullable=True)
    # AgentFlow.meta_conversaciones_diaria -> daily_conversations_goal
    daily_conversations_goal = Column(Integer, default=20)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
