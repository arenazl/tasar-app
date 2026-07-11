from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from models.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# ── Jerarquia de roles del rubro inmobiliario (WO F6-06) ─────────────────────
# Vocabulario canonico y UNICO de la suite, en UN solo lugar. Es una jerarquia:
# cada nivel INCLUYE el alcance de los de abajo (una sola app, un solo login;
# cada nivel hace TODAS las funciones con distinto ALCANCE).
#
#   broker (4)        titular con matricula: acceso TOTAL (config, equipo,
#                     borrados, todo).
#   administrador (3) gestion plena (operativa + administrativa + equipo +
#                     config). En permisos practicos == broker; la diferencia
#                     es de titulo (broker = titular).
#   coordinador (2)   ve TODO el workspace (scope de manager) y gestiona lo
#                     comercial (DMO, ranking, todas las conversaciones/deals),
#                     pero NO config del workspace, NI gestion de equipo, NI
#                     borrados sensibles.
#   asesor (1)        opera lo suyo + lo sin asignar (el "vendedor" de antes).
#
# Mapeo desde el vocabulario anterior (fix 477dcc4): admin->broker,
# supervisor->coordinador, vendedor->asesor. `administrador` es un nivel NUEVO
# (nadie lo tiene tras el mapeo; el broker lo asigna a mano desde Equipo).
ROLE_HIERARCHY: dict[str, int] = {
    "asesor": 1,
    "coordinador": 2,
    "administrador": 3,
    "broker": 4,
}
DEFAULT_ROLE = "asesor"


def role_level(role: str | None) -> int:
    """Nivel jerarquico del rol (0 si es desconocido/None)."""
    return ROLE_HIERARCHY.get(role or "", 0)


def has_min_role(user: User, min_role: str) -> bool:
    """True si el rol del user ALCANZA (>=) el nivel de `min_role`. Uso in-handler
    para el scoping (manager ve todo vs asesor ve lo suyo)."""
    return role_level(user.role) >= role_level(min_role)


def require_role(*roles: str):
    """Autorizacion por roles EXPLICITOS (no jerarquica). Preferir
    `require_min_role` salvo que se necesite un set puntual de roles."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Sin permisos")
        return user
    return _check


def require_min_role(min_role: str):
    """Dependencia FastAPI JERARQUICA: exige que el user tenga AL MENOS el nivel
    de `min_role` (broker pasa donde pasa coordinador, etc.). Es el camino
    preferido: usa el vocabulario canonico de ROLE_HIERARCHY, en un solo lugar."""
    if min_role not in ROLE_HIERARCHY:
        raise ValueError(f"rol invalido: {min_role!r} (esperado uno de {sorted(ROLE_HIERARCHY)})")

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not has_min_role(user, min_role):
            raise HTTPException(status_code=403, detail="Sin permisos suficientes")
        return user
    return _check


async def ensure_study_in_workspace(study_id: int, user: User, db: AsyncSession):
    """Verifica que el market_study pertenezca al workspace del usuario.

    Devuelve el MarketStudy si es del workspace, o 404 si no existe / es de otro
    tenant. Usamos 404 (no 403) a propósito para NO filtrar la existencia de
    estudios de otros workspaces (anti-IDOR).
    """
    from models.market_study import MarketStudy

    study = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if study is None:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")
    return study
