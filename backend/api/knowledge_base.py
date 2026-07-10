"""Knowledge Share Protocol (KSP v1.2, WO F5-01) — productor del KB de TasAR.

Contrato completo: `base-compartida/3-PROTOCOLO-COMPLETO.md`. TasAR expone UN
documento (`GET /api/knowledge-base`) que consumen dos apps del ecosistema:
SalesBot (material de venta para captar inmobiliarias/tasadores como clientes
de TasAR) y Media Studio (campanas de video). El `business` de este KB
describe a **TasAR el producto SaaS** (no a un tenant/inmobiliaria puntual):
eso es contenido curado (nombre, propuesta de valor, modulos reales, marca).

Lo que SI sale EN VIVO de la base, sin inventar nada (regla dura #11):
  - `entities[].sample`: una propiedad y una tasacion express REALES del
    workspace demo (`settings.KB_DEMO_WORKSPACE_SLUG`, sembrado por
    `scripts/seed_demo.py`). Si el workspace o la fila no existen, el sample
    se omite (nunca se fabrica un dato).
  - `/api/tools/*`: 3 endpoints REALES (no una promesa) que corren la misma
    logica de negocio que usa el bot de WhatsApp (`services/bot_tools.py`),
    para que SalesBot pueda demostrar el producto llamando datos de verdad.

Auth: header `X-KB-Key` contra las DOS claves fijas de los generadores
(`KB_CLAVE_SALESBOT` / `KB_CLAVE_MEDIASTUDIO`, protocolo 5.1-5.2). Sin
header -> 401. Header que no matchea ninguna -> 403. Ninguna clave
configurada en el servidor -> 503 (fail-closed, nunca se sirve el KB "por
las dudas"). Los endpoints `/api/tools/*` reusan la MISMA auth (protocolo
5.6): mismo header, mismas claves, mismo host ya registrado en
`2-APPS-ENTRADAS.json` (por eso no hay SSRF: el destino lo fija el registro,
no el modelo que llama a la tool).
"""
from __future__ import annotations

import hmac
import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.workspace import Workspace
from models.property import Property
from models.express_valuation import ExpressValuation
from models.client import Client
from models.visit import Visit
from services.bot_tools import (
    buscar_propiedades as _bot_buscar_propiedades,
    tasacion_express as _bot_tasacion_express,
    asignar_round_robin,
)
from api import kb_content

log = logging.getLogger("tasar.knowledge_base")

router = APIRouter(prefix="/api", tags=["knowledge-base"])

CONTRACT_VERSION = "1.2"
# Fuente UNICA del timestamp: KB (`last_updated`) y health (`kb_last_updated`)
# tienen que salir de la MISMA constante (protocolo 6.2) para que un
# consumidor que solo mira el health se entere de cambios en el contenido
# curado de abajo. Bump manual cuando cambie el contenido estatico de
# `kb_content.py`.
_KB_LAST_UPDATED = "2026-07-10T00:00:00Z"


# ── Auth (protocolo 5.1) ─────────────────────────────────────────────────

def _check_kb_key(x_kb_key: Optional[str]) -> None:
    secrets = [
        (settings.KB_CLAVE_SALESBOT or "").strip(),
        (settings.KB_CLAVE_MEDIASTUDIO or "").strip(),
    ]
    if not any(secrets):
        raise HTTPException(503, "KB secrets no configurados (KB_CLAVE_SALESBOT / KB_CLAVE_MEDIASTUDIO)")
    if not x_kb_key:
        raise HTTPException(401, "falta X-KB-Key")
    key = x_kb_key.encode()
    ok = False
    for s in secrets:
        if s and hmac.compare_digest(key, s.encode()):
            ok = True
    if not ok:
        raise HTTPException(403, "X-KB-Key invalida")


async def _resolve_workspace(db: AsyncSession, x_kb_workspace: Optional[str]) -> Optional[Workspace]:
    """Header `X-KB-Workspace: <slug>` pisa el default; si no viene, usa el
    workspace demo configurado. Nunca inventa un workspace: si el slug
    resuelto no existe en la base, devuelve None y el caller degrada."""
    slug = (x_kb_workspace or settings.KB_DEMO_WORKSPACE_SLUG or "").strip()
    if not slug:
        return None
    return (await db.execute(select(Workspace).where(Workspace.slug == slug))).scalar_one_or_none()


def _clean_phone(raw: str) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())

# ── Entities EN VIVO (sample real del workspace demo, o se omite) ──────────

async def _property_entity(db: AsyncSession, workspace: Optional[Workspace]) -> Dict[str, Any]:
    entity: Dict[str, Any] = {
        "name": "propiedad", "identifica_por": "id",
        "campos": ["id", "titulo", "tipo", "operacion", "barrio", "ciudad", "ambientes", "dormitorios", "precio_usd", "moneda"],
    }
    if workspace is None:
        return entity
    try:
        p = (await db.execute(
            select(Property).where(Property.workspace_id == workspace.id).order_by(Property.created_at.desc()).limit(1)
        )).scalar_one_or_none()
    except Exception as e:  # noqa: BLE001 — el sample es "nice to have": nunca tira abajo el KB
        log.warning("KB: no se pudo traer sample de propiedad (se omite): %s", type(e).__name__)
        return entity
    if p:
        entity["sample"] = {
            "id": p.id, "titulo": p.title, "tipo": p.property_type, "operacion": p.operation,
            "barrio": p.neighborhood, "ciudad": p.city, "ambientes": p.rooms, "dormitorios": p.bedrooms,
            "precio_usd": p.asking_price, "moneda": p.currency,
        }
    return entity


async def _valuation_entity(db: AsyncSession, workspace: Optional[Workspace]) -> Dict[str, Any]:
    entity: Dict[str, Any] = {
        "name": "tasacion_express", "identifica_por": "id",
        "campos": ["id", "tipo_propiedad", "ciudad", "barrio", "superficie_m2", "precio_m2_tipico_usd", "precio_total_tipico_usd", "confianza"],
    }
    if workspace is None:
        return entity
    try:
        v = (await db.execute(
            select(ExpressValuation).where(ExpressValuation.workspace_id == workspace.id).order_by(ExpressValuation.created_at.desc()).limit(1)
        )).scalar_one_or_none()
    except Exception as e:  # noqa: BLE001 — el sample es "nice to have": nunca tira abajo el KB
        log.warning("KB: no se pudo traer sample de tasacion express (se omite): %s", type(e).__name__)
        return entity
    if v:
        entity["sample"] = {
            "id": v.id, "tipo_propiedad": v.property_type, "ciudad": v.city, "barrio": v.neighborhood,
            "superficie_m2": v.total_area_m2, "precio_m2_tipico_usd": v.price_per_m2_typical,
            "precio_total_tipico_usd": v.total_price_usd, "confianza": v.confidence,
        }
    return entity


async def _build_kb(db: AsyncSession, workspace: Optional[Workspace]) -> Dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "last_updated": _KB_LAST_UPDATED,
        "business": kb_content.BUSINESS,
        "key_messages": kb_content.KEY_MESSAGES,
        "offerings": kb_content.OFFERINGS,
        "pricing": kb_content.PRICING,
        "differentiators": kb_content.DIFFERENTIATORS,
        "objections": kb_content.OBJECTIONS,
        "faq": kb_content.FAQ,
        "contact": kb_content.CONTACT,
        "do_not_say": kb_content.DO_NOT_SAY,
        "capabilities": kb_content.CAPABILITIES,
        "entities": [
            await _property_entity(db, workspace),
            await _valuation_entity(db, workspace),
        ],
        "tools": kb_content.TOOLS,
        "screens": kb_content.SCREENS,
        "brand": kb_content.BRAND,
        "extra": {},
    }


# ── Endpoints KSP ────────────────────────────────────────────────────────

@router.get("/knowledge-base/health")
async def kb_health() -> Dict[str, Any]:
    """Sin auth (protocolo 2.2: info no sensible, solo version/timestamp)."""
    return {"status": "ok", "contract_version": CONTRACT_VERSION, "kb_last_updated": _KB_LAST_UPDATED}


@router.get("/knowledge-base")
async def get_knowledge_base(
    x_kb_key: Optional[str] = Header(default=None, alias="X-KB-Key"),
    x_kb_workspace: Optional[str] = Header(default=None, alias="X-KB-Workspace"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    _check_kb_key(x_kb_key)
    workspace = await _resolve_workspace(db, x_kb_workspace)
    return await _build_kb(db, workspace)


# ── /api/tools/* — tools REALES declaradas arriba (protocolo 4.14 + 5.6) ───
# Mismo header/claves que /knowledge-base. buscar_propiedades y
# tasacion_express corren la MISMA logica que usa el bot de WhatsApp
# (services/bot_tools.py); esas 2 funciones solo tocan `ctx.db` y
# `ctx.workspace_id` (nunca `ctx.conversation`), asi que se les pasa un
# contexto liviano en vez de duplicar el motor de busqueda/anclaje.

class _ToolBuscarPropiedadesBody(BaseModel):
    zona: Optional[str] = None
    tipo: Optional[str] = None
    ambientes: Optional[int] = None
    presupuesto_min_usd: Optional[int] = None
    presupuesto_max_usd: Optional[int] = None
    limit: int = 5


class _ToolTasacionExpressBody(BaseModel):
    tipo_propiedad: str
    superficie_m2: float
    provincia: Optional[str] = None
    ciudad: Optional[str] = None
    barrio: Optional[str] = None
    dormitorios: Optional[int] = None
    estado: Optional[str] = None


class _ToolAgendarVisitaBody(BaseModel):
    propiedad_id: int
    fecha_propuesta: str
    telefono_cliente: str
    nombre_cliente: Optional[str] = None


async def _kb_tool_workspace(db: AsyncSession, x_kb_key: Optional[str], x_kb_workspace: Optional[str]) -> Workspace:
    _check_kb_key(x_kb_key)
    ws = await _resolve_workspace(db, x_kb_workspace)
    if ws is None:
        raise HTTPException(404, "workspace no encontrado (X-KB-Workspace o KB_DEMO_WORKSPACE_SLUG mal configurado)")
    return ws


@router.post("/tools/buscar_propiedades")
async def tool_buscar_propiedades(
    body: _ToolBuscarPropiedadesBody,
    x_kb_key: Optional[str] = Header(default=None, alias="X-KB-Key"),
    x_kb_workspace: Optional[str] = Header(default=None, alias="X-KB-Workspace"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    ws = await _kb_tool_workspace(db, x_kb_key, x_kb_workspace)
    ctx = SimpleNamespace(db=db, workspace_id=ws.id)
    return await _bot_buscar_propiedades(ctx, **body.model_dump())  # type: ignore[arg-type]


@router.post("/tools/tasacion_express")
async def tool_tasacion_express(
    body: _ToolTasacionExpressBody,
    x_kb_key: Optional[str] = Header(default=None, alias="X-KB-Key"),
    x_kb_workspace: Optional[str] = Header(default=None, alias="X-KB-Workspace"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    ws = await _kb_tool_workspace(db, x_kb_key, x_kb_workspace)
    ctx = SimpleNamespace(db=db, workspace_id=ws.id)
    result = await _bot_tasacion_express(ctx, **body.model_dump())  # type: ignore[arg-type]
    await db.commit()
    return result


@router.post("/tools/agendar_visita")
async def tool_agendar_visita(
    body: _ToolAgendarVisitaBody,
    x_kb_key: Optional[str] = Header(default=None, alias="X-KB-Key"),
    x_kb_workspace: Optional[str] = Header(default=None, alias="X-KB-Workspace"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Variante SIN conversacion de WhatsApp de `bot_tools.agendar_visita`: el
    telefono lo manda el llamador (no hay JID de donde inferirlo). Misma
    logica de fondo (busca/crea Client por telefono, asigna vendedor por
    round-robin, crea Visit) escrita directo aca para no forzar un
    WaConversation ficticio en `services/bot_tools.py`."""
    ws = await _kb_tool_workspace(db, x_kb_key, x_kb_workspace)

    p = (await db.execute(
        select(Property).where(Property.id == body.propiedad_id, Property.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not p:
        return {"ok": False, "error": "Propiedad no encontrada en este workspace"}

    try:
        scheduled_at = datetime.fromisoformat(body.fecha_propuesta.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return {"ok": False, "error": f"Fecha invalida: {body.fecha_propuesta}"}

    phone = _clean_phone(body.telefono_cliente)
    if not phone:
        return {"ok": False, "error": "telefono_cliente invalido"}

    client = (await db.execute(
        select(Client).where(Client.workspace_id == ws.id, Client.phone == phone)
    )).scalar_one_or_none()

    vendor = await asignar_round_robin(db, ws.id)
    if client is None:
        client = Client(
            workspace_id=ws.id,
            name=(body.nombre_cliente or "Contacto KSP").strip(),
            phone=phone,
            origin="otro",
            lead_status="nuevo",
            assigned_to=vendor.id if vendor else None,
        )
        db.add(client)
        await db.flush()

    vendor_id = client.assigned_to
    if not vendor_id:
        if not vendor:
            return {"ok": False, "error": "No hay asesores disponibles para asignar la visita"}
        vendor_id = vendor.id

    visit = Visit(
        workspace_id=ws.id, client_id=client.id, property_id=p.id, vendor_id=vendor_id,
        scheduled_at=scheduled_at, status="agendada", result="sin_resultado",
        voice_notes="Agendada via /api/tools/agendar_visita (KSP), pendiente de confirmacion del asesor.",
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)

    return {
        "ok": True, "visita_id": visit.id, "cliente_id": client.id,
        "propiedad": p.title, "fecha": scheduled_at.isoformat(),
    }
