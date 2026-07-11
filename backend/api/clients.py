"""CRUD de clientes del workspace + ficha eje (timeline unificado, WO F6-02)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, union_all, literal, null
from pydantic import BaseModel
from typing import Optional, List

from core.database import get_db
from core.security import get_current_user, has_min_role
from models.user import User
from models.client import Client
from models.appraisal import Appraisal
from models.property import Property
from models.visit import Visit
from models.deal import Deal
from models.conversation import WaConversation
from models.message import WaMessage


router = APIRouter(prefix="/api/clients", tags=["clients"])

# --- Reglas del "siguiente paso" DERIVADO de los datos (no IA), WO F6-02 ---
CONTACT_STALE_DAYS = 7      # sin contacto hace >= X dias -> recontactar
DEAL_STALE_DAYS = 14        # deal sin movimiento hace >= X dias -> avanzar etapa
ACTIVE_LEAD_STATUSES = {"contactado", "calificado", "cita", "propuesta"}
CLOSED_LEAD_STATUSES = {"cerrado", "perdido"}
FINAL_DEAL_STAGES = {"escrituracion"}
TIMELINE_LIMIT = 120        # tope de eventos devueltos (mensajes pueden ser muchos)


class ClientIn(BaseModel):
    name: str
    type: str = "particular"
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class ClientOut(ClientIn):
    id: int
    appraisals_count: int = 0

    class Config:
        from_attributes = True


def _type_from_name(name: str) -> str:
    n = (name or "").lower()
    if "banco" in n:
        return "banco"
    if "fondo" in n:
        return "fondo"
    if "estudio" in n or "aldao" in n:
        return "estudio"
    if "remax" in n or "argencapital" in n or "atlas" in n or "inmobiliaria" in n:
        return "inmobiliaria"
    return "particular"


async def _autoseed_from_appraisals(db: AsyncSession, workspace_id: int) -> int:
    """Si el workspace tiene appraisals pero la tabla clients esta vacia,
    crea clientes derivados del client_name unico de las appraisals."""
    rows = (await db.execute(
        select(Appraisal.client_name, Appraisal.client_email)
        .where(Appraisal.workspace_id == workspace_id, Appraisal.client_name.isnot(None))
        .distinct()
    )).all()
    created = 0
    for name, email in rows:
        if not name:
            continue
        c = Client(
            workspace_id=workspace_id,
            name=name,
            type=_type_from_name(name),
            email=email,
        )
        db.add(c)
        created += 1
    if created:
        await db.commit()
    return created


@router.get("", response_model=List[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Client).where(Client.workspace_id == user.workspace_id).order_by(Client.name)
    )).scalars().all()

    # Auto-seed: si la tabla esta vacia pero el workspace tiene appraisals con
    # client_name, creamos los clientes derivados. Sucede una sola vez.
    if not rows:
        created = await _autoseed_from_appraisals(db, user.workspace_id)
        if created:
            rows = (await db.execute(
                select(Client).where(Client.workspace_id == user.workspace_id).order_by(Client.name)
            )).scalars().all()

    # Conteo de tasaciones por client_name (legacy: appraisals tienen client_name string)
    name_counts: dict = {}
    counts_q = await db.execute(
        select(Appraisal.client_name, func.count(Appraisal.id))
        .where(Appraisal.workspace_id == user.workspace_id)
        .group_by(Appraisal.client_name)
    )
    for name, cnt in counts_q.all():
        if name:
            name_counts[name] = cnt

    out = []
    for c in rows:
        d = ClientOut.model_validate(c).model_dump()
        d["appraisals_count"] = name_counts.get(c.name, 0)
        out.append(ClientOut(**d))
    return out


# ── Ficha de cliente eje: timeline unificado (WO F6-02) ─────────────────────

class TimelineEvent(BaseModel):
    """Evento normalizado del timeline. `kind` decide como se interpreta cada
    campo en el front (ej. `status` es la etapa en un deal, la direccion en un
    mensaje, el estado en una visita)."""
    kind: str                       # mensaje | visita | deal | tasacion
    ref_id: int
    ts: Optional[datetime] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None


class NextStep(BaseModel):
    """Sugerencia de accion DERIVADA de los datos (no IA)."""
    code: str                       # recontactar|agendar_visita|abrir_deal|avanzar_etapa|al_dia
    label: str
    reason: str
    action_type: str                # navigate | chat | wa | none
    target: Optional[str] = None    # ruta interna o None (wa => el front arma wa.me)


class ClientTimelineOut(BaseModel):
    # Cabecera
    id: int
    name: str
    type: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None
    lead_status: Optional[str] = None
    temperature: Optional[str] = None
    origin: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    # Preferencias de busqueda
    pref_zona: Optional[str] = None
    pref_m2_min: Optional[int] = None
    pref_m2_max: Optional[int] = None
    pref_ambientes: Optional[int] = None
    pref_budget_min: Optional[float] = None
    pref_budget_max: Optional[float] = None
    pref_currency: Optional[str] = None
    last_contact_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # Conteos + acceso rapido al chat
    visits_count: int = 0
    deals_count: int = 0
    conversations_count: int = 0
    appraisals_count: int = 0
    messages_count: int = 0
    primary_conversation_id: Optional[int] = None
    # Agregado
    next_step: NextStep
    timeline: List[TimelineEvent]


def _days_since(dt: Optional[datetime]) -> Optional[int]:
    """Dias transcurridos desde `dt` hasta ahora (UTC), robusto a naive/aware.
    MySQL devuelve DATETIME sin tz -> normalizamos todo a UTC-naive."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return (datetime.utcnow() - dt).days


def _build_next_step(
    *,
    lead_status: Optional[str],
    has_visit: bool,
    has_concretada_visit: bool,
    latest_open_deal: Optional[TimelineEvent],
    days_since_contact: Optional[int],
    primary_conversation_id: Optional[int],
) -> NextStep:
    """Deriva la unica accion mas relevante siguiendo el embudo (avanzar lo mas
    avanzado primero). Reglas del WO F6-02, todas basadas en datos reales."""
    lead = lead_status or "nuevo"

    # 0) Lead cerrado (ganado) o perdido: no hay funnel que empujar.
    if lead in CLOSED_LEAD_STATUSES:
        return NextStep(code="al_dia", label="Seguimiento al día",
                        reason="El lead está cerrado; no hay una acción pendiente",
                        action_type="none", target=None)

    # 1) Deal abierto sin movimiento -> avanzar etapa.
    if latest_open_deal is not None:
        deal_days = _days_since(latest_open_deal.ts)
        if deal_days is None or deal_days >= DEAL_STALE_DAYS:
            reason = (
                "La operación no registra movimiento"
                if deal_days is None
                else f"La operación lleva {deal_days} días sin avanzar de etapa"
            )
            return NextStep(code="avanzar_etapa", label="Avanzar la operación",
                            reason=reason, action_type="navigate", target="/pipeline")

    # 2) Visita concretada y todavia sin deal -> abrir deal.
    if has_concretada_visit and latest_open_deal is None:
        return NextStep(code="abrir_deal", label="Abrir operación",
                        reason="Hizo una visita y todavía no hay una operación abierta",
                        action_type="navigate", target="/pipeline")

    # 3) Lead activo sin ninguna visita -> agendar visita.
    if lead not in CLOSED_LEAD_STATUSES and not has_visit and lead in ACTIVE_LEAD_STATUSES:
        return NextStep(code="agendar_visita", label="Agendar visita",
                        reason="Lead calificado y todavía sin visitas agendadas",
                        action_type="navigate", target="/visitas")

    # 4) Sin contacto hace demasiado -> recontactar (por su chat si lo hay).
    if lead not in CLOSED_LEAD_STATUSES:
        if days_since_contact is None or days_since_contact >= CONTACT_STALE_DAYS:
            reason = ("Sin contacto registrado" if days_since_contact is None
                      else f"Sin contacto hace {days_since_contact} días")
            if primary_conversation_id:
                return NextStep(code="recontactar", label="Recontactar", reason=reason,
                                action_type="chat",
                                target=f"/whatsapp?conv={primary_conversation_id}")
            return NextStep(code="recontactar", label="Recontactar", reason=reason,
                            action_type="wa", target=None)

    return NextStep(code="al_dia", label="Seguimiento al día",
                    reason="No hay una acción urgente pendiente",
                    action_type="none", target=None)


@router.get("/{client_id}/timeline", response_model=ClientTimelineOut)
async def client_timeline(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ficha eje del cliente: cabecera + timeline unificado (mensajes, visitas,
    deals y tasaciones ordenados por fecha desc) + siguiente paso derivado.

    Agregado en 3 queries constantes (sin N+1):
      Q1: cliente + vendedor asignado (scoping + cabecera).
      Q2: conversaciones del cliente (conteo + chat primario + ultima actividad).
      Q3: timeline = UNION ALL de visitas + deals + tasaciones + mensajes.
    """
    # Q1 — cliente + nombre del vendedor asignado. Sirve tambien para el scoping.
    row = (await db.execute(
        select(Client, User.full_name)
        .join(User, User.id == Client.assigned_to, isouter=True)
        .where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).first()
    if not row:
        # 404 (no 403) a proposito: no filtramos la existencia de clientes de
        # otros workspaces (anti-IDOR), mismo criterio que ensure_study_in_workspace.
        raise HTTPException(404, "Cliente no encontrado")
    client, assigned_name = row

    # Scoping por rol (WO F6-06): asesor ve SOLO sus clientes (assigned_to);
    # coordinador+ ve todos los del workspace.
    if not has_min_role(user, "coordinador") and client.assigned_to != user.id:
        raise HTTPException(404, "Cliente no encontrado")

    # Q2 — conversaciones del cliente (para el conteo, el chat primario y la
    # ultima actividad que alimenta el "siguiente paso").
    convs = (await db.execute(
        select(
            WaConversation.id,
            WaConversation.last_activity_at,
        )
        .where(
            WaConversation.workspace_id == user.workspace_id,
            WaConversation.client_id == client_id,
        )
        .order_by(WaConversation.last_activity_at.desc())
    )).all()
    primary_conversation_id = convs[0].id if convs else None
    conv_last_activity = convs[0].last_activity_at if convs else None

    # Q3 — timeline unificado en UNA query via UNION ALL. Cada rama trae sus
    # JOINs a Property/User resueltos in-query (nombres para mostrar), y las
    # columnas que no aplican van como NULL casteado para que MySQL una tipos
    # compatibles entre ramas. Sin N+1: es 1 sola consulta sin importar el volumen.
    ws = user.workspace_id

    visits_sel = (
        select(
            literal("visita").label("kind"),
            Visit.id.label("ref_id"),
            Visit.scheduled_at.label("ts"),
            Property.title.label("title"),
            Visit.result.label("subtitle"),
            Visit.status.label("status"),
            null().label("amount"),
            null().label("currency"),
        )
        .join(Property, Property.id == Visit.property_id, isouter=True)
        .where(Visit.workspace_id == ws, Visit.client_id == client_id)
    )
    deals_sel = (
        select(
            literal("deal"),
            Deal.id,
            Deal.updated_at,
            Property.title,
            Deal.notes,
            Deal.stage,
            Deal.negotiated_price,
            Deal.currency,
        )
        .join(Property, Property.id == Deal.property_id, isouter=True)
        .where(Deal.workspace_id == ws, Deal.client_id == client_id)
    )
    appraisals_sel = (
        select(
            literal("tasacion"),
            Appraisal.id,
            Appraisal.created_at,
            func.coalesce(Appraisal.code, Property.title),
            Property.title,
            Appraisal.status,
            Appraisal.final_value,
            Appraisal.currency,
        )
        .join(Property, Property.id == Appraisal.property_id, isouter=True)
        .where(Appraisal.workspace_id == ws, Appraisal.client_name == client.name)
    )
    messages_sel = (
        select(
            literal("mensaje"),
            WaMessage.id,
            WaMessage.created_at,
            func.substr(func.coalesce(WaMessage.transcription, WaMessage.content, ""), 1, 160),
            WaConversation.contact_name,
            WaMessage.direction,
            null(),
            null(),
        )
        .join(WaConversation, WaConversation.id == WaMessage.conversation_id)
        .where(WaConversation.workspace_id == ws, WaConversation.client_id == client_id)
    )

    u = union_all(visits_sel, deals_sel, appraisals_sel, messages_sel).subquery()
    events_rows = (await db.execute(
        select(u).order_by(u.c.ts.desc()).limit(TIMELINE_LIMIT)
    )).all()
    timeline = [TimelineEvent(**dict(r._mapping)) for r in events_rows]

    # Derivados para el "siguiente paso" (todo desde lo ya traido, sin queries extra).
    visit_events = [e for e in timeline if e.kind == "visita"]
    deal_events = [e for e in timeline if e.kind == "deal"]
    msg_events = [e for e in timeline if e.kind == "mensaje"]
    appraisal_events = [e for e in timeline if e.kind == "tasacion"]

    has_visit = bool(visit_events)
    has_concretada_visit = any(e.status == "concretada" for e in visit_events)
    open_deals = [e for e in deal_events if (e.status or "") not in FINAL_DEAL_STAGES]
    latest_open_deal = open_deals[0] if open_deals else None  # timeline ya viene desc por ts

    contact_candidates = [d for d in (
        client.last_contact_at,
        conv_last_activity,
        (msg_events[0].ts if msg_events else None),
    ) if d is not None]
    days_since_contact = None
    if contact_candidates:
        # el mas reciente
        days_since_contact = min(_days_since(d) for d in contact_candidates)

    next_step = _build_next_step(
        lead_status=client.lead_status,
        has_visit=has_visit,
        has_concretada_visit=has_concretada_visit,
        latest_open_deal=latest_open_deal,
        days_since_contact=days_since_contact,
        primary_conversation_id=primary_conversation_id,
    )

    return ClientTimelineOut(
        id=client.id,
        name=client.name,
        type=client.type,
        contact_name=client.contact_name,
        email=client.email,
        phone=client.phone,
        address=client.address,
        tax_id=client.tax_id,
        notes=client.notes,
        lead_status=client.lead_status,
        temperature=client.temperature,
        origin=client.origin,
        assigned_to=client.assigned_to,
        assigned_to_name=assigned_name,
        pref_zona=client.pref_zona,
        pref_m2_min=client.pref_m2_min,
        pref_m2_max=client.pref_m2_max,
        pref_ambientes=client.pref_ambientes,
        pref_budget_min=client.pref_budget_min,
        pref_budget_max=client.pref_budget_max,
        pref_currency=client.pref_currency,
        last_contact_at=client.last_contact_at,
        created_at=client.created_at,
        visits_count=len(visit_events),
        deals_count=len(deal_events),
        conversations_count=len(convs),
        appraisals_count=len(appraisal_events),
        messages_count=len(msg_events),
        primary_conversation_id=primary_conversation_id,
        next_step=next_step,
        timeline=timeline,
    )


@router.post("", response_model=ClientOut)
async def create_client(
    body: ClientIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = Client(workspace_id=user.workspace_id, **body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ClientOut.model_validate(c)


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: int,
    body: ClientIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = (await db.execute(
        select(Client).where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return ClientOut.model_validate(c)


@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = (await db.execute(
        select(Client).where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    await db.delete(c)
    await db.commit()
    return {"ok": True}
