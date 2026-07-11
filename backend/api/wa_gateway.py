"""Proxy JWT -> wa-gateway (gestion de la sesion WhatsApp por workspace).

El frontend NO habla directo con el gateway (expondria WA_GATEWAY_KEY al
browser). Pega a estos endpoints autenticados con JWT y la suite reenvia al
gateway con `X-API-Key`, usando `settings.WA_GATEWAY_URL` + `settings.WA_GATEWAY_KEY`.

El tenant SIEMPRE es el workspace del usuario del JWT (nunca se acepta un slug
arbitrario del cliente -> anti-IDOR). Restringido a administrador+ (config del
canal WhatsApp del workspace, WO F6-06) via require_min_role.

Patron portado de AgentFlow/backend/api/baileys_gateway.py, adaptado a
multi-tenant (slug = workspace del JWT en vez de un tenant fijo).
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from core.security import require_min_role
from models.user import User
from models.workspace import Workspace

router = APIRouter(prefix="/api/wa", tags=["wa-gateway"])


def _gateway_url() -> str:
    url = (settings.WA_GATEWAY_URL or "").rstrip("/")
    if not url:
        raise HTTPException(503, "WA_GATEWAY_URL no configurada")
    return url


def _gateway_key() -> str:
    if not settings.WA_GATEWAY_KEY:
        raise HTTPException(503, "WA_GATEWAY_KEY no configurada")
    return settings.WA_GATEWAY_KEY


async def _workspace_slug(user: User, db: AsyncSession) -> str:
    ws = (await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )).scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace no encontrado")
    return ws.slug


@router.get("/status")
async def wa_status(
    user: User = Depends(require_min_role("administrador")),
    db: AsyncSession = Depends(get_db),
):
    """Estado de la sesion WhatsApp del workspace del usuario."""
    slug = await _workspace_slug(user, db)
    url = f"{_gateway_url()}/tenants/{slug}/status"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers={"X-API-Key": _gateway_key()})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Error conectando al gateway: {e}")


@router.post("/start")
async def wa_start(
    user: User = Depends(require_min_role("administrador")),
    db: AsyncSession = Depends(get_db),
):
    """Arranca/asegura la sesion del workspace (idempotente)."""
    slug = await _workspace_slug(user, db)
    url = f"{_gateway_url()}/tenants/{slug}/start"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, headers={"X-API-Key": _gateway_key()})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Error arrancando sesion: {e}")


@router.post("/stop")
async def wa_stop(
    user: User = Depends(require_min_role("administrador")),
    db: AsyncSession = Depends(get_db),
):
    """Detiene la sesion (conserva credenciales). Reconecta con /start."""
    slug = await _workspace_slug(user, db)
    url = f"{_gateway_url()}/tenants/{slug}/stop"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers={"X-API-Key": _gateway_key()})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Error deteniendo sesion: {e}")


@router.get("/qr.html")
async def wa_qr_page(
    user: User = Depends(require_min_role("administrador")),
    db: AsyncSession = Depends(get_db),
):
    """HTML del QR del gateway. El frontend lo muestra en un iframe."""
    slug = await _workspace_slug(user, db)
    url = f"{_gateway_url()}/tenants/{slug}/qr?key={_gateway_key()}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return Response(
                    content=(
                        "<html><body style='font-family:sans-serif;padding:2rem;"
                        f"text-align:center;color:#888'><h3>{r.status_code}</h3>"
                        "<p>El gateway no devolvio QR ahora</p></body></html>"
                    ),
                    media_type="text/html",
                    status_code=200,
                )
            return Response(
                content=r.content,
                media_type=r.headers.get("content-type", "text/html"),
            )
    except httpx.HTTPError as e:
        return Response(
            content=(
                "<html><body style='font-family:sans-serif;padding:2rem;"
                f"text-align:center;color:crimson'><h3>Error</h3><p>{e}</p></body></html>"
            ),
            media_type="text/html",
            status_code=200,
        )
