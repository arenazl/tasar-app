from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from core.database import Base


# Estados del ciclo de vida de una invitacion de equipo (WO F4-05).
STATUS_PENDIENTE = "pendiente"
STATUS_ACEPTADA = "aceptada"
STATUS_EXPIRADA = "expirada"
STATUS_CANCELADA = "cancelada"


class Invitation(Base):
    """Invitacion de un miembro al equipo de un workspace (WO F4-05).

    El admin invita por email con un rol pre-asignado. El `token` (opaco,
    secrets.token_urlsafe) es la CLAVE de registro: mapea a esta fila que
    guarda `workspace_id` + `role`. Asi el workspace y el rol NO viajan en el
    JWT ni en la URL en claro -- viajan como esta fila server-side, que es
    revocable (status=cancelada), expirable (expires_at) y de un solo uso
    (status=aceptada al alta). Multi-tenant: siempre scoped por workspace_id.
    """

    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    email = Column(String(150), nullable=False, index=True)
    role = Column(String(30), nullable=False)  # admin | supervisor | vendedor
    full_name = Column(String(150), nullable=True)  # pre-carga opcional del alta
    token = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), default=STATUS_PENDIENTE, index=True)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
