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
    role = Column(String(30), default="tasador")
    # Vocabulario de roles UNIFICADO (WO F1-01): admin | supervisor | vendedor.
    # Mapeo desde AgentFlow: gerente -> supervisor, coordinador -> supervisor,
    # vendedor -> vendedor, admin -> admin.
    # Roles legacy de TasAR (tasador | cliente) SIGUEN siendo validos y el
    # default se deja en "tasador" para NO romper el alta de usuarios existente.
    license_number = Column(String(80), nullable=True)  # matrícula tasador
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
