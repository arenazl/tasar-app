"""Tools nativas del bot WhatsApp (WO F2-03) — TODAS scoped al workspace.

Cada tool opera EXCLUSIVAMENTE sobre datos del workspace de la conversacion
(`ctx.workspace_id`). No hay forma de que un bot de un workspace lea/escriba datos
de otro: los filtros `workspace_id ==` estan en cada query/insert.

Gemini con function calling decide cuando invocar cada tool (formato
`function_declarations`). El bot NUNCA inventa propiedades, precios ni
disponibilidad: eso siempre sale de estas tools.

Las 7 tools:
  buscar_propiedades   - stock publicado del workspace (filtros zona/tipo/amb/precio)
  consultar_propiedad  - detalle + fotos de una propiedad del workspace
  agendar_visita       - crea client (origin='whatsapp') si no existe + Visit pendiente
  registrar_lead       - interes/presupuesto/temperatura -> client (lead)
  tasacion_express     - rango de valor anclado (anchor_service, F1-03) para captacion
  derivar_a_humano     - round-robin por is_available/last_assigned_at + notifica + pausa
  cerrar_conversacion  - marca la conversacion como cerrada
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.property import Property, PropertyPhoto
from models.client import Client
from models.visit import Visit
from models.user import User
from models.conversation import WaConversation, STATUS_ABIERTA, STATUS_CERRADA
from models.express_valuation import ExpressValuation
from services.anchor_service import AnchorQuery, get_market_anchor


log = logging.getLogger("tasar.bot_tools")

# Pausa del bot al derivar a un humano: se apaga en esta conversacion hasta que un
# asesor la maneje (belt-and-suspenders; el webhook ya no llama al bot si hay
# assignee). Larga a proposito.
DERIVATION_PAUSE = timedelta(days=7)

# Fallback deterministico de la tasacion express (mismo criterio que api/valuations.py).
_COND_FACTOR = {
    "a_estrenar": 1.12, "excelente": 1.06, "muy_bueno": 1.02,
    "bueno": 1.00, "regular": 0.90, "a_reciclar": 0.80,
}
_CLOSING_FACTOR = 0.88
_BAND_WIDTH = {"alta": 0.07, "media": 0.10, "baja": 0.15}


@dataclass
class BotContext:
    """Contexto de ejecucion de las tools. `send` (opcional) es el UNICO camino de
    salida a WhatsApp, inyectado por el webhook para no duplicar la ruta de envio.
    En tests se pasa sin `send` (las notificaciones se saltean)."""
    db: AsyncSession
    workspace_id: int
    workspace_slug: str
    workspace_name: str
    conversation: WaConversation
    # WorkspaceBotConfig del workspace (tipado Any para evitar import circular).
    bot_config: Optional[Any] = None
    # send(phone_or_jid, text) -> None. None => no se envia (tests / sin gateway).
    send: Optional[Callable[[str, str], Awaitable[None]]] = None


# ── Declaraciones de tools (formato Gemini function_declarations) ──────────

TOOL_DECLARATIONS: List[Dict[str, Any]] = [
    {
        "name": "buscar_propiedades",
        "description": (
            "Busca propiedades del stock real de la inmobiliaria que cumplan los "
            "filtros. Usar cuando el cliente pregunte por propiedades, opciones, "
            "precios en una zona, etc. NUNCA inventes propiedades — usá siempre esta tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "zona": {"type": "string", "description": "Barrio o ciudad (ej 'Palermo', 'La Plata')"},
                "tipo": {
                    "type": "string",
                    "enum": ["casa", "departamento", "ph", "terreno", "local", "oficina"],
                    "description": "Tipo de propiedad",
                },
                "ambientes": {"type": "integer", "description": "Cantidad de ambientes"},
                "presupuesto_min_usd": {"type": "integer", "description": "Piso de precio en USD"},
                "presupuesto_max_usd": {"type": "integer", "description": "Tope de precio en USD"},
                "limit": {"type": "integer", "description": "Cuántos resultados (default 5, máx 10)"},
            },
            "required": [],
        },
    },
    {
        "name": "consultar_propiedad",
        "description": (
            "Trae el detalle completo + fotos de UNA propiedad por su ID. Usar cuando "
            "el cliente pregunta por una propiedad que ya se le mostró."
        ),
        "parameters": {
            "type": "object",
            "properties": {"propiedad_id": {"type": "integer", "description": "ID interno de la propiedad"}},
            "required": ["propiedad_id"],
        },
    },
    {
        "name": "agendar_visita",
        "description": (
            "Agenda una visita a una propiedad. Queda pendiente de confirmación del "
            "asesor. Usar cuando el cliente acepta ver una propiedad en una fecha/hora "
            "concreta. El teléfono del cliente se toma de la conversación (no lo pidas)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "propiedad_id": {"type": "integer"},
                "fecha_propuesta": {
                    "type": "string",
                    "description": "Fecha y hora ISO 8601 ya resuelta (ej '2026-07-14T17:00:00-03:00')",
                },
                "nombre_cliente": {"type": "string", "description": "Nombre del cliente si se conoce"},
            },
            "required": ["propiedad_id", "fecha_propuesta"],
        },
    },
    {
        "name": "registrar_lead",
        "description": (
            "Registra/actualiza al cliente como lead con su interés. Usar cuando el "
            "cliente da datos de búsqueda (zona, presupuesto) aunque todavía no agende. "
            "El teléfono se toma de la conversación."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"},
                "interes": {"type": "string", "description": "Qué busca (ej 'depto 2 amb para comprar')"},
                "zona": {"type": "string"},
                "presupuesto_max_usd": {"type": "integer"},
                "temperatura": {"type": "string", "enum": ["caliente", "tibio", "frio"]},
            },
            "required": [],
        },
    },
    {
        "name": "tasacion_express",
        "description": (
            "Estima un RANGO de valor de mercado (USD) para una propiedad que describe "
            "un propietario, anclado a comparables reales del mercado. Gancho de "
            "captación: usar cuando un dueño pregunta cuánto vale/puede pedir por su "
            "propiedad. Devuelve un rango, no un precio único."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tipo_propiedad": {
                    "type": "string",
                    "enum": ["casa", "departamento", "ph", "terreno", "local", "oficina"],
                },
                "superficie_m2": {"type": "number", "description": "Superficie total en m2"},
                "provincia": {"type": "string"},
                "ciudad": {"type": "string"},
                "barrio": {"type": "string"},
                "dormitorios": {"type": "integer"},
                "estado": {
                    "type": "string",
                    "enum": ["a_estrenar", "excelente", "muy_bueno", "bueno", "regular", "a_reciclar"],
                },
            },
            "required": ["tipo_propiedad", "superficie_m2"],
        },
    },
    {
        "name": "derivar_a_humano",
        "description": (
            "Deriva la conversación a un asesor humano (round-robin del equipo). Usar "
            "cuando el cliente pide hablar con una persona, tiene un reclamo, o ya hay "
            "interés real para avanzar con una visita/propuesta."
        ),
        "parameters": {
            "type": "object",
            "properties": {"motivo": {"type": "string", "description": "Motivo breve de la derivación"}},
            "required": [],
        },
    },
    {
        "name": "cerrar_conversacion",
        "description": (
            "Marca la conversación como cerrada. Usar solo cuando el cliente se despide "
            "y no hay nada pendiente."
        ),
        "parameters": {
            "type": "object",
            "properties": {"motivo": {"type": "string"}},
            "required": [],
        },
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _phone_from_jid(jid: Optional[str]) -> Optional[str]:
    """E.164 sin '+' a partir de un JID de WhatsApp ('549...@s.whatsapp.net')."""
    if not jid:
        return None
    digits = jid.split("@", 1)[0].split(":", 1)[0].replace("+", "").strip()
    return digits or None


async def asignar_round_robin(db: AsyncSession, workspace_id: int) -> Optional[User]:
    """Proximo asesor disponible del WORKSPACE (menos recientemente asignado primero).

    Scoping duro por workspace_id: nunca asigna un usuario de otro tenant. Elegibles
    (WO F6-06): asesor/coordinador activos y disponibles (los que reciben leads).
    Orden: last_assigned_at ASC (NULL primero).
    """
    r = await db.execute(
        select(User)
        .where(
            and_(
                User.workspace_id == workspace_id,
                User.is_active == True,       # noqa: E712
                User.is_available == True,    # noqa: E712
                User.role.in_(["asesor", "coordinador"]),
            )
        )
        .order_by(User.last_assigned_at.is_(None).desc(), User.last_assigned_at.asc())
        .limit(1)
    )
    return r.scalar_one_or_none()


async def _get_or_create_client(ctx: BotContext, nombre: Optional[str]) -> tuple[Optional[Client], bool]:
    """Busca (o crea) el Client del workspace por el telefono de la conversacion.

    Devuelve (client, created): `created=True` solo cuando se dio de ALTA un lead
    nuevo (lo usa el producer de Bandeja para no notificar en cada actualizacion).

    origin='whatsapp' (valido en el enum de la suite desde F1-01; el bug de AgentFlow
    de crear con un origen inexistente NO se porta). Vincula la conversacion al client.
    """
    conv = ctx.conversation
    phone = _phone_from_jid(conv.phone_jid)

    # Si la conversacion ya esta vinculada a un client del workspace, usarlo.
    if conv.client_id:
        existing = (await ctx.db.execute(
            select(Client).where(Client.id == conv.client_id, Client.workspace_id == ctx.workspace_id)
        )).scalar_one_or_none()
        if existing:
            return existing, False

    # Buscar por telefono dentro del workspace.
    client = None
    if phone:
        client = (await ctx.db.execute(
            select(Client).where(Client.workspace_id == ctx.workspace_id, Client.phone == phone)
        )).scalar_one_or_none()

    created = False
    if client is None:
        vendor = await asignar_round_robin(ctx.db, ctx.workspace_id)
        client = Client(
            workspace_id=ctx.workspace_id,
            name=(nombre or conv.contact_name or "Contacto WhatsApp").strip(),
            phone=phone,
            origin="whatsapp",
            lead_status="nuevo",
            assigned_to=conv.assignee_id or (vendor.id if vendor else None),
        )
        ctx.db.add(client)
        await ctx.db.flush()
        created = True

    conv.client_id = client.id
    return client, created


# ── Implementaciones ─────────────────────────────────────────────────────

async def buscar_propiedades(
    ctx: BotContext,
    zona: Optional[str] = None,
    tipo: Optional[str] = None,
    ambientes: Optional[int] = None,
    presupuesto_min_usd: Optional[int] = None,
    presupuesto_max_usd: Optional[int] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    limit = min(max(int(limit or 5), 1), 10)
    # Property no tiene flag de "publicada" (ver HALLAZGO en el reporte): tomamos
    # como stock ofrecible las propiedades del workspace con precio de venta cargado.
    filters = [Property.workspace_id == ctx.workspace_id, Property.asking_price > 0]
    if zona:
        filters.append(or_(Property.city.ilike(f"%{zona}%"), Property.neighborhood.ilike(f"%{zona}%")))
    if tipo:
        filters.append(Property.property_type == tipo.lower())
    if ambientes:
        filters.append(Property.rooms == int(ambientes))
    if presupuesto_min_usd:
        filters.append(Property.asking_price >= presupuesto_min_usd)
    if presupuesto_max_usd:
        filters.append(Property.asking_price <= presupuesto_max_usd)

    rows = (await ctx.db.execute(
        select(Property).where(and_(*filters)).order_by(Property.created_at.desc()).limit(limit)
    )).scalars().all()

    return {
        "count": len(rows),
        "propiedades": [
            {
                "id": p.id,
                "titulo": p.title,
                "tipo": p.property_type,
                "operacion": p.operation,
                "direccion": p.address,
                "barrio": p.neighborhood,
                "ciudad": p.city,
                "ambientes": p.rooms,
                "dormitorios": p.bedrooms,
                "banos": p.bathrooms,
                "m2_totales": p.total_area_m2,
                "precio_usd": p.asking_price,
                "moneda": p.currency,
            }
            for p in rows
        ],
    }


async def consultar_propiedad(ctx: BotContext, propiedad_id: int) -> Dict[str, Any]:
    p = (await ctx.db.execute(
        select(Property).where(Property.id == int(propiedad_id), Property.workspace_id == ctx.workspace_id)
    )).scalar_one_or_none()
    if not p:
        return {"ok": False, "error": "Propiedad no encontrada en este workspace"}
    fotos = (await ctx.db.execute(
        select(PropertyPhoto).where(PropertyPhoto.property_id == p.id).order_by(PropertyPhoto.order).limit(4)
    )).scalars().all()
    return {
        "ok": True,
        "id": p.id,
        "titulo": p.title,
        "descripcion": p.description,
        "tipo": p.property_type,
        "operacion": p.operation,
        "direccion": p.address,
        "barrio": p.neighborhood,
        "ciudad": p.city,
        "provincia": p.province,
        "ambientes": p.rooms,
        "dormitorios": p.bedrooms,
        "banos": p.bathrooms,
        "cocheras": p.parking_spots,
        "m2_totales": p.total_area_m2,
        "m2_cubiertos": p.covered_area_m2,
        "antiguedad": p.age_years,
        "estado": p.condition,
        "precio_usd": p.asking_price,
        "moneda": p.currency,
        "fotos": [f.url for f in fotos],
    }


async def agendar_visita(
    ctx: BotContext,
    propiedad_id: int,
    fecha_propuesta: str,
    nombre_cliente: Optional[str] = None,
) -> Dict[str, Any]:
    p = (await ctx.db.execute(
        select(Property).where(Property.id == int(propiedad_id), Property.workspace_id == ctx.workspace_id)
    )).scalar_one_or_none()
    if not p:
        return {"ok": False, "error": "Propiedad no encontrada en este workspace"}

    try:
        scheduled_at = datetime.fromisoformat(fecha_propuesta.replace("Z", ""))
    except (ValueError, AttributeError):
        return {"ok": False, "error": f"Fecha inválida: {fecha_propuesta}"}

    client, _created = await _get_or_create_client(ctx, nombre_cliente)
    if client is None:
        return {"ok": False, "error": "No se pudo identificar al cliente"}

    # Vendedor: el asignado de la conversacion, o el del cliente, o round-robin.
    vendor_id = ctx.conversation.assignee_id or client.assigned_to
    if not vendor_id:
        vendor = await asignar_round_robin(ctx.db, ctx.workspace_id)
        if not vendor:
            return {"ok": False, "error": "No hay asesores disponibles para asignar la visita"}
        vendor_id = vendor.id

    visit = Visit(
        workspace_id=ctx.workspace_id,
        client_id=client.id,
        property_id=p.id,
        vendor_id=vendor_id,
        scheduled_at=scheduled_at,
        status="agendada",
        result="sin_resultado",
        voice_notes="Agendada por el bot de WhatsApp, pendiente de confirmación del asesor.",
    )
    ctx.db.add(visit)
    await ctx.db.flush()

    # Evento de Bandeja: visita agendada por el bot (dirigida al vendedor asignado).
    await _emit_inbox_event(
        ctx, "visit_scheduled",
        conversation_id=ctx.conversation.id, user_id=vendor_id,
        property_title=p.title or f"Propiedad #{p.id}",
        when_label=scheduled_at.strftime("%d/%m %H:%M") + " hs",
        client_name=client.name,
    )

    # Notificar al vendedor (best-effort, via el unico camino de salida).
    await _notify_vendor(
        ctx, vendor_id,
        f"Nueva visita agendada por el bot.\n"
        f"Propiedad: {p.title} ({p.address}).\n"
        f"Fecha: {scheduled_at.strftime('%d/%m %H:%M')} hs.\n"
        f"Cliente: {client.name}.",
    )
    return {
        "ok": True,
        "visita_id": visit.id,
        "cliente_id": client.id,
        "propiedad": p.title,
        "fecha": scheduled_at.isoformat(),
    }


async def registrar_lead(
    ctx: BotContext,
    nombre: Optional[str] = None,
    interes: Optional[str] = None,
    zona: Optional[str] = None,
    presupuesto_max_usd: Optional[int] = None,
    temperatura: Optional[str] = None,
) -> Dict[str, Any]:
    client, created = await _get_or_create_client(ctx, nombre)
    if client is None:
        return {"ok": False, "error": "No se pudo identificar al cliente"}

    if nombre and (not client.name or client.name in ("Contacto WhatsApp",)):
        client.name = nombre.strip()
    if interes:
        note = f"[bot] Interés: {interes}"
        client.notes = f"{client.notes}\n{note}" if client.notes else note
    if zona:
        client.pref_zona = zona
    if presupuesto_max_usd:
        client.pref_budget_max = float(presupuesto_max_usd)
    if temperatura in ("caliente", "tibio", "frio"):
        client.temperature = temperatura
    if client.lead_status in (None, "nuevo"):
        client.lead_status = "contactado"
    client.last_contact_at = datetime.now(timezone.utc)
    await ctx.db.flush()

    # Evento de Bandeja: SOLO en el alta real de un lead nuevo (no en cada update).
    if created:
        await _emit_inbox_event(
            ctx, "lead_created",
            conversation_id=ctx.conversation.id,
            contact_name=client.name, phone=client.phone,
            user_id=client.assigned_to, interes=interes,
        )
    return {"ok": True, "cliente_id": client.id, "lead_status": client.lead_status}


async def tasacion_express(
    ctx: BotContext,
    tipo_propiedad: str,
    superficie_m2: float,
    provincia: Optional[str] = None,
    ciudad: Optional[str] = None,
    barrio: Optional[str] = None,
    dormitorios: Optional[int] = None,
    estado: Optional[str] = None,
) -> Dict[str, Any]:
    """Rango de valor anclado al catálogo real de mercado (anchor_service, F1-03).

    El catálogo `market_listings` es data de mercado COMPARTIDA (no por workspace):
    el ancla es correcta a nivel mercado. La valuación se persiste en
    express_valuations del workspace (created_by=None = bot) para trazabilidad.
    Devuelve un RANGO deterministico anclado a la mediana del segmento similar;
    nunca un precio inventado.
    """
    try:
        area = float(superficie_m2)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Superficie inválida"}
    if area <= 0:
        return {"ok": False, "error": "La superficie debe ser mayor a 0"}

    q = AnchorQuery(
        property_type=tipo_propiedad,
        total_area_m2=area,
        province=provincia,
        city=ciudad,
        neighborhood=barrio,
        condition=estado,
        bedrooms=dormitorios,
        features=[],
    )
    anchor = await get_market_anchor(ctx.db, q)
    if not anchor:
        return {
            "ok": True,
            "sin_datos": True,
            "mensaje": (
                "No tengo comparables suficientes del mercado para estimar esta "
                "propiedad. Un asesor puede hacer una tasación completa."
            ),
        }

    median = anchor["price_per_m2"]["median"]
    count = anchor["count"]
    confidence = "alta" if count >= 30 else ("media" if count >= 10 else "baja")
    width = _BAND_WIDTH[confidence]
    cond_factor = _COND_FACTOR.get(estado or "", 1.0)
    typical_ppm2 = median * _CLOSING_FACTOR * cond_factor
    low_total = round(typical_ppm2 * (1 - width) * area)
    high_total = round(typical_ppm2 * (1 + width) * area)
    typical_total = round(typical_ppm2 * area)

    # Persistir para trazabilidad (best-effort, no rompe el flujo del bot).
    try:
        ev = ExpressValuation(
            workspace_id=ctx.workspace_id,
            created_by=None,
            property_type=tipo_propiedad,
            province=provincia, city=ciudad, neighborhood=barrio,
            total_area_m2=area, bedrooms=dormitorios, condition=estado,
            anchor_scope=anchor["scope"], anchor_count=count,
            anchor_median_ppm2=median,
            price_per_m2_typical=round(typical_ppm2),
            total_price_usd=typical_total, currency="USD",
            confidence=confidence, ai_used=False,
            input_json=json.dumps({
                "tipo_propiedad": tipo_propiedad, "superficie_m2": area,
                "provincia": provincia, "ciudad": ciudad, "barrio": barrio,
                "dormitorios": dormitorios, "estado": estado, "source": "whatsapp_bot",
            }, ensure_ascii=False),
            output_json=json.dumps({
                "totalPriceUSD": {"low": low_total, "typical": typical_total, "high": high_total},
                "confidence": confidence, "scope": anchor["scope"],
            }, ensure_ascii=False),
        )
        ctx.db.add(ev)
        await ctx.db.flush()
    except Exception as e:  # noqa: BLE001
        log.warning("tasacion_express: no se pudo persistir (ignorado): %s", type(e).__name__)

    return {
        "ok": True,
        "rango_usd": {"min": low_total, "tipico": typical_total, "max": high_total},
        "confianza": confidence,
        "comparables": count,
        "alcance": anchor["scope"],
        "nota": "Valor orientativo de mercado. Una tasación completa con un asesor lo precisa.",
    }


async def derivar_a_humano(ctx: BotContext, motivo: Optional[str] = None) -> Dict[str, Any]:
    conv = ctx.conversation
    vendor = await asignar_round_robin(ctx.db, ctx.workspace_id)
    if not vendor:
        return {"ok": True, "derivado": False, "error": "No hay asesores disponibles ahora"}

    conv.assignee_id = vendor.id
    conv.status = STATUS_ABIERTA
    conv.bot_paused_until = datetime.now(timezone.utc) + DERIVATION_PAUSE
    vendor.last_assigned_at = datetime.now(timezone.utc)

    # Vincular/crear el cliente para que el vendedor tenga la ficha.
    client, _created = await _get_or_create_client(ctx, None)
    await ctx.db.flush()

    # Evento de Bandeja: conversacion DERIVADA a un humano, todavia sin tomar.
    await _emit_inbox_event(
        ctx, "conversation_handoff",
        conversation_id=conv.id, user_id=vendor.id,
        contact_name=conv.contact_name, motivo=motivo,
    )

    # Notificar al vendedor con resumen + tarjeta wa.me del cliente.
    phone = _phone_from_jid(conv.phone_jid)
    wa_link = f"https://wa.me/{phone}" if phone else "(sin número)"
    resumen = await _resumen_ultimos_mensajes(ctx)
    await _notify_vendor(
        ctx, vendor.id,
        f"Nuevo lead derivado por el bot ({motivo or 'sin motivo'}).\n"
        f"Contacto: {conv.contact_name or phone or 'desconocido'}.\n"
        f"Escribile directo: {wa_link}\n"
        f"Últimos mensajes:\n{resumen}",
    )
    return {
        "ok": True,
        "derivado": True,
        "vendor_id": vendor.id,
        "vendor_name": vendor.full_name,
        "cliente_id": client.id if client else None,
    }


async def cerrar_conversacion(ctx: BotContext, motivo: Optional[str] = None) -> Dict[str, Any]:
    ctx.conversation.status = STATUS_CERRADA
    await ctx.db.flush()
    return {"ok": True, "estado": STATUS_CERRADA}


# ── Notificacion / resumen (usan el unico camino de salida) ────────────────

async def _emit_inbox_event(ctx: BotContext, kind: str, **kwargs: Any) -> None:
    """Dispara un evento de Bandeja (producer inbox_service) — best-effort.

    Un fallo del producer NUNCA rompe el flujo del bot (patron de la casa: como los
    bloques de notificacion por email). Import diferido para evitar ciclo con la capa
    de servicios/API.

    WO F3-03: este es el UNICO punto donde los 3 eventos de Bandeja originados
    por el bot (lead_created, visit_scheduled, conversation_handoff) se
    disparan -- por eso es tambien el unico punto donde se cablea el push:
    si el evento tiene un `user_id` destinatario (el vendedor asignado), se le
    manda una notificacion push ademas de la fila de Bandeja. Un fallo del
    push (VAPID no configurada, sub vencida, etc.) tampoco rompe el flujo del
    bot -- mismo try/except que el resto.
    """
    try:
        from services import inbox_service
        fn = getattr(inbox_service, kind)
        msg = await fn(ctx.db, workspace_id=ctx.workspace_id, **kwargs)
        if msg.user_id:
            from services.push_notif import notify_user
            await notify_user(
                ctx.db, msg.user_id,
                title=msg.subject, body=msg.preview or "",
                url=msg.related_url or "/bandeja",
            )
    except Exception as e:  # noqa: BLE001
        log.warning("inbox event %s fallo (ignorado): %s", kind, type(e).__name__)


async def _notify_vendor(ctx: BotContext, vendor_id: int, text: str) -> None:
    if ctx.send is None:
        return
    vendor = (await ctx.db.execute(select(User).where(User.id == vendor_id))).scalar_one_or_none()
    if not vendor or not vendor.personal_phone:
        return
    try:
        await ctx.send(vendor.personal_phone, text)
    except Exception as e:  # noqa: BLE001
        log.warning("notify_vendor fallo (ignorado): %s", type(e).__name__)


async def _resumen_ultimos_mensajes(ctx: BotContext) -> str:
    from models.message import WaMessage, DIRECTION_INBOUND
    rows = (await ctx.db.execute(
        select(WaMessage)
        .where(WaMessage.conversation_id == ctx.conversation.id, WaMessage.direction == DIRECTION_INBOUND)
        .order_by(WaMessage.created_at.desc())
        .limit(4)
    )).scalars().all()
    if not rows:
        return "(sin mensajes previos)"
    return "\n".join(f"> {(m.content or '')[:100]}" for m in reversed(rows))


# ── Dispatcher ─────────────────────────────────────────────────────────────

_DISPATCH: Dict[str, Callable[..., Awaitable[Any]]] = {
    "buscar_propiedades": buscar_propiedades,
    "consultar_propiedad": consultar_propiedad,
    "agendar_visita": agendar_visita,
    "registrar_lead": registrar_lead,
    "tasacion_express": tasacion_express,
    "derivar_a_humano": derivar_a_humano,
    "cerrar_conversacion": cerrar_conversacion,
}


async def execute_tool(ctx: BotContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta una tool por nombre con args. Todas operan sobre ctx.workspace_id."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"ok": False, "error": f"Tool desconocida: {name}"}
    try:
        return await fn(ctx, **(args or {}))
    except TypeError as e:
        return {"ok": False, "error": f"Argumentos inválidos para {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        log.exception("execute_tool %s fallo", name)
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
