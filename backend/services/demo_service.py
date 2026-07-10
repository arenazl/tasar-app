"""Generador de datos de ejemplo por workspace + borrado seguro (WO F5-03).

Generaliza a "por workspace, on-demand" el generador de seed de calidad que
antes vivia como script suelto y fijo a un unico workspace demo
(`scripts/seed_v2.py` / `scripts/seed_demo.py`, coords reales de barrio + USD/m2
base reales, sin `random.uniform()` inventando ubicaciones fuera de zona real).

Regla #11 CLAUDE.md global (no negociable): TODO lo que genera este modulo
queda marcado `is_demo=True` y con etiqueta "[DEMO]" visible en el campo que
se lista en la UI (titulo de propiedad, nombre de vendedor, nombre de
contacto de conversacion). El borrado (`purge_demo_data`) SOLO toca filas
`is_demo=True` del workspace del que lo pide -- nunca cruza tenant, nunca
toca una fila real aunque este mezclada con demo.

Idempotencia: `generate_demo_data` primero purga cualquier demo previo del
workspace (mismo camino que el purge explicito) y genera un set fresco. Asi
"Cargar datos de ejemplo" se puede apretar mas de una vez sin acumular filas
ni chocar contra el UNIQUE de email/phone_jid.
"""
from __future__ import annotations

import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.security import hash_password
from models.appraisal import Appraisal
from models.authorization import Authorization
from models.deal import Deal
from models.dmo import DmoAssignment, DmoLog, DmoTemplate
from models.market_study import Comparable, MarketStudy
from models.message import WaMessage
from models.conversation import WaConversation, STATUS_NUEVA, STATUS_ABIERTA, STATUS_CERRADA
from models.property import Property
from models.user import User
from models.visit import Visit
from models.workspace import Workspace


# ============ Zonas REALES con USD/m² base (mismos valores que seed_v2.py) ============
# (nombre, ciudad, provincia, lat, lng, usd/m2 base)
REAL_ZONES: list[tuple[str, str, str, float, float, int]] = [
    ("Palermo",       "CABA", "CABA", -34.5800, -58.4300, 3420),
    ("Recoleta",      "CABA", "CABA", -34.5900, -58.3950, 3180),
    ("Belgrano",      "CABA", "CABA", -34.5600, -58.4500, 2890),
    ("Núñez",         "CABA", "CABA", -34.5450, -58.4600, 2750),
    ("Caballito",     "CABA", "CABA", -34.6200, -58.4400, 2410),
    ("Villa Crespo",  "CABA", "CABA", -34.5980, -58.4400, 2380),
    ("Vicente López", "Buenos Aires", "Vicente López", -34.5300, -58.4750, 3150),
    ("La Plata",      "Buenos Aires", "La Plata",      -34.9200, -57.9500, 1450),
]
_PROPERTY_TYPES = ["departamento", "casa", "ph"]
_TYPE_WEIGHTS = [0.65, 0.20, 0.15]
_CONDITIONS = ["a_estrenar", "excelente", "muy_bueno", "bueno", "regular"]
_COND_FACTOR = {"a_estrenar": 1.10, "excelente": 1.05, "muy_bueno": 1.00, "bueno": 0.95, "regular": 0.85}

DEMO_VENDOR_NAMES = ["Vendedor Demo 1", "Vendedor Demo 2", "Vendedor Demo 3"]

_CONVO_SCRIPTS = [
    (STATUS_NUEVA, [
        ("inbound", "Hola, vi el depto de Palermo publicado. ¿Sigue disponible?"),
    ]),
    (STATUS_ABIERTA, [
        ("inbound", "Buenas, quería consultar por el 3 ambientes de Belgrano."),
        ("outbound", "Hola! Sí, sigue disponible. ¿Querés coordinar una visita?"),
        ("inbound", "Dale, este finde si puede ser."),
    ]),
    (STATUS_ABIERTA, [
        ("inbound", "¿Hacen tasaciones para sucesión también?"),
        ("outbound", "Sí, hacemos tasación express y ACM completo. ¿Me pasás la zona?"),
    ]),
    (STATUS_CERRADA, [
        ("inbound", "Gracias por la visita de ayer, quedamos en pensarlo."),
        ("outbound", "Perfecto, quedo atento. Cualquier cosa me escribís."),
    ]),
    (STATUS_NUEVA, [
        ("inbound", "Hola, ¿cuánto sale tasar una casa en Vicente López?"),
    ]),
]


def _n(x: float) -> float:
    return round(x, 6)


def gen_demo_properties(workspace_id: int, admin_id: int, vendor_ids: list[int], n: int) -> list[Property]:
    """Genera N propiedades [DEMO] coherentes: coords reales de zona + jitter
    chico DENTRO del barrio (mismo patron que `scripts/seed_v2.gen_market_listings`,
    ya aceptado en el repo: no inventa ubicaciones fuera de una zona real)."""
    props: list[Property] = []
    for i in range(n):
        zname, city, prov, lat0, lng0, base_ppm2 = REAL_ZONES[i % len(REAL_ZONES)]
        ptype = random.choices(_PROPERTY_TYPES, weights=_TYPE_WEIGHTS)[0]
        lat = lat0 + random.uniform(-0.006, 0.006)
        lng = lng0 + random.uniform(-0.006, 0.006)

        if ptype == "departamento":
            total = random.choice([45, 55, 65, 75, 90, 105])
            rooms = max(1, total // 30)
        elif ptype == "casa":
            total = random.choice([150, 200, 260, 320])
            rooms = max(3, total // 60)
        else:
            total = random.choice([65, 85, 110])
            rooms = max(2, total // 40)
        covered = round(total * random.uniform(0.75, 0.95))
        cond = random.choice(_CONDITIONS)
        price = round(base_ppm2 * _COND_FACTOR[cond] * total, -3)

        props.append(Property(
            workspace_id=workspace_id,
            created_by=admin_id,
            captador_id=vendor_ids[i % len(vendor_ids)] if vendor_ids else None,
            title=f"[DEMO] {ptype.title()} {rooms} amb. {zname}",
            property_type=ptype,
            operation="venta",
            province=prov,
            city=city,
            neighborhood=zname,
            address=f"Av. {zname} {random.randint(100, 4900)}",
            latitude=_n(lat), longitude=_n(lng),
            total_area_m2=float(total), covered_area_m2=float(covered),
            rooms=rooms, bedrooms=max(1, rooms - 1), bathrooms=max(1, rooms // 2),
            age_years=random.randint(0, 40), condition=cond,
            asking_price=float(price), currency="USD",
            description=f"Propiedad de ejemplo generada por el onboarding — {zname}, {city}.",
            is_demo=True,
        ))
    return props


def gen_demo_vendors(workspace_id: int, suffix: str) -> list[User]:
    """3 vendedores [DEMO] con email unico por workspace (User.email es UNIQUE
    global). Password aleatoria y no comunicada — no estan pensados para login,
    solo para poblar equipo/DMO/asignaciones de la demo."""
    vendors = []
    for i, name in enumerate(DEMO_VENDOR_NAMES, start=1):
        vendors.append(User(
            workspace_id=workspace_id,
            email=f"demo.vendedor{i}.{suffix}@tasar-demo.local",
            password_hash=hash_password(secrets.token_urlsafe(24)),
            full_name=f"[DEMO] {name}",
            role="vendedor",
            is_active=True,
            is_available=True,
            daily_conversations_goal=20,
            is_demo=True,
        ))
    return vendors


async def _ensure_demo_dmo_template(db: AsyncSession, workspace_id: int) -> Optional[DmoTemplate]:
    """Resuelve el template DMO a asignar a los vendedores demo: el office
    default del workspace si ya existe, o clona el primer template OFICIAL del
    catalogo global (workspace_id IS NULL). Si no hay catalogo oficial sembrado
    en este entorno, devuelve None (la demo sigue sin asignacion DMO — no
    rompe el resto de la generacion)."""
    existing = (await db.execute(
        select(DmoTemplate).where(
            DmoTemplate.workspace_id == workspace_id,
            DmoTemplate.is_office_default.is_(True),
        ).options(selectinload(DmoTemplate.blocks))
    )).scalar_one_or_none()
    if existing:
        return existing

    official = (await db.execute(
        select(DmoTemplate)
        .where(DmoTemplate.workspace_id.is_(None))
        .options(selectinload(DmoTemplate.blocks))
        .order_by(DmoTemplate.id.asc())
        .limit(1)
    )).scalar_one_or_none()
    if not official:
        return None

    from models.dmo import DmoBlock  # import local: evita ciclo con api/dmo.py

    clone = DmoTemplate(
        workspace_id=workspace_id,
        coach_id=official.coach_id,
        name=official.name,
        description=official.description,
        market=official.market,
        is_active=True,
        is_office_default=True,
    )
    db.add(clone)
    await db.flush()
    for b in official.blocks:
        db.add(DmoBlock(
            template_id=clone.id,
            name=b.name, description=b.description,
            start_time=b.start_time, end_time=b.end_time,
            color=b.color, sort_order=b.sort_order,
            is_money_block=b.is_money_block,
            metric_type=b.metric_type, metric_label=b.metric_label, metric_goal=b.metric_goal,
        ))
    return clone


def gen_demo_conversations(workspace_id: int, vendor_ids: list[int]) -> tuple[list[WaConversation], list[list[tuple[str, str]]]]:
    """5 conversaciones [DEMO] con guion realista (2-3 mensajes c/u)."""
    convos = []
    scripts = []
    now = datetime.now(timezone.utc)
    for i, (status, turns) in enumerate(_CONVO_SCRIPTS, start=1):
        assignee = vendor_ids[(i - 1) % len(vendor_ids)] if vendor_ids and status != STATUS_NUEVA else None
        convos.append(WaConversation(
            workspace_id=workspace_id,
            phone_jid=f"54911000{workspace_id:04d}{i}@s.whatsapp.net",
            phone_public=None,
            contact_name=f"[DEMO] Cliente {i}",
            assignee_id=assignee,
            status=status,
            unread_count=1 if status == STATUS_NUEVA else 0,
            last_activity_at=now - timedelta(hours=i),
            is_demo=True,
        ))
        scripts.append(turns)
    return convos, scripts


async def generate_demo_data(
    db: AsyncSession, workspace: Workspace, admin: User, n_properties: int = 12,
) -> dict:
    """Genera un set fresco de datos de ejemplo para `workspace`. Idempotente:
    purga cualquier demo previo del mismo workspace antes de generar (mismo
    camino que `purge_demo_data`, sin duplicar logica de borrado)."""
    n_properties = max(3, min(n_properties, 60))
    await purge_demo_data(db, workspace.id)

    suffix = f"{workspace.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    vendors = gen_demo_vendors(workspace.id, suffix)
    for v in vendors:
        db.add(v)
    await db.flush()
    vendor_ids = [v.id for v in vendors]

    template = await _ensure_demo_dmo_template(db, workspace.id)
    dmo_assignments_created = 0
    if template:
        for vid in vendor_ids:
            db.add(DmoAssignment(workspace_id=workspace.id, vendor_id=vid, template_id=template.id))
            dmo_assignments_created += 1

    props = gen_demo_properties(workspace.id, admin.id, vendor_ids, n_properties)
    for p in props:
        db.add(p)

    convos, scripts = gen_demo_conversations(workspace.id, vendor_ids)
    for c in convos:
        db.add(c)
    await db.flush()

    n_messages = 0
    for convo, turns in zip(convos, scripts):
        base = convo.last_activity_at or datetime.now(timezone.utc)
        for j, (direction, text) in enumerate(turns):
            db.add(WaMessage(
                conversation_id=convo.id,
                direction=direction,
                type="text",
                content=text,
                sender_id=(convo.assignee_id if direction == "outbound" else None),
                is_read=(direction == "outbound" or convo.status != STATUS_NUEVA),
                created_at=base - timedelta(minutes=(len(turns) - j) * 5),
            ))
            n_messages += 1

    await db.commit()

    return {
        "workspace_id": workspace.id,
        "properties_created": len(props),
        "vendors_created": len(vendors),
        "dmo_assignments_created": dmo_assignments_created,
        "dmo_skipped": template is None,
        "conversations_created": len(convos),
        "messages_created": n_messages,
    }


# ============================ PURGE (dry-run + confirm) ============================

async def _referenced_property_ids(db: AsyncSession, property_ids: list[int]) -> set[int]:
    """Propiedades demo que NO se pueden borrar porque un dato REAL (visita,
    operacion, autorizacion, tasacion o ACM/comparable) ya las referencia por
    FK. Cubre las tablas que tienen `property_id`/`source_property_id`
    NOT NULL/nullable hacia `properties` -- evita un IntegrityError de MySQL a
    mitad de purge."""
    if not property_ids:
        return set()
    referenced: set[int] = set()
    for col in (
        Visit.property_id, Deal.property_id, Authorization.property_id,
        Appraisal.property_id, MarketStudy.property_id, Comparable.source_property_id,
    ):
        rows = (await db.execute(
            select(col).where(col.in_(property_ids)).distinct()
        )).scalars().all()
        referenced.update(r for r in rows if r is not None)
    return referenced


async def _demo_scope(db: AsyncSession, workspace_id: int) -> dict:
    """Resuelve los ids demo del workspace + que tanto de eso es borrable."""
    vendor_ids = (await db.execute(
        select(User.id).where(User.workspace_id == workspace_id, User.is_demo.is_(True))
    )).scalars().all()
    conv_ids = (await db.execute(
        select(WaConversation.id).where(
            WaConversation.workspace_id == workspace_id, WaConversation.is_demo.is_(True),
        )
    )).scalars().all()
    property_ids = (await db.execute(
        select(Property.id).where(Property.workspace_id == workspace_id, Property.is_demo.is_(True))
    )).scalars().all()

    kept_property_ids = await _referenced_property_ids(db, list(property_ids))
    deletable_property_ids = [pid for pid in property_ids if pid not in kept_property_ids]

    n_messages = 0
    if conv_ids:
        n_messages = (await db.execute(
            select(func.count(WaMessage.id)).where(WaMessage.conversation_id.in_(conv_ids))
        )).scalar_one()

    n_dmo_assignments = n_dmo_logs = 0
    if vendor_ids:
        n_dmo_assignments = (await db.execute(
            select(func.count(DmoAssignment.id)).where(DmoAssignment.vendor_id.in_(vendor_ids))
        )).scalar_one()
        n_dmo_logs = (await db.execute(
            select(func.count(DmoLog.id)).where(DmoLog.vendor_id.in_(vendor_ids))
        )).scalar_one()

    return dict(
        vendor_ids=list(vendor_ids), conv_ids=list(conv_ids),
        property_ids=list(property_ids), deletable_property_ids=deletable_property_ids,
        kept_property_ids=list(kept_property_ids),
        n_messages=n_messages, n_dmo_assignments=n_dmo_assignments, n_dmo_logs=n_dmo_logs,
    )


async def preview_demo_purge(db: AsyncSession, workspace_id: int) -> dict:
    """Dry-run: cuenta lo que se borraria, SIN borrar nada."""
    scope = await _demo_scope(db, workspace_id)
    return {
        "properties_to_delete": len(scope["deletable_property_ids"]),
        "properties_kept_in_use": len(scope["kept_property_ids"]),
        "vendors_to_delete": len(scope["vendor_ids"]),
        "conversations_to_delete": len(scope["conv_ids"]),
        "messages_to_delete": scope["n_messages"],
        "dmo_assignments_to_delete": scope["n_dmo_assignments"],
        "dmo_logs_to_delete": scope["n_dmo_logs"],
    }


async def purge_demo_data(db: AsyncSession, workspace_id: int) -> dict:
    """Borra SOLO lo `is_demo=True` de este workspace, en orden FK-safe.
    Propiedades demo referenciadas por un dato real (visita/operacion/
    autorizacion/tasacion/ACM) se DEJAN (no se pueden borrar sin romper ese
    dato real) y se informan en `properties_kept_in_use`."""
    scope = await _demo_scope(db, workspace_id)

    if scope["vendor_ids"]:
        await db.execute(delete(DmoLog).where(DmoLog.vendor_id.in_(scope["vendor_ids"])))
        await db.execute(delete(DmoAssignment).where(DmoAssignment.vendor_id.in_(scope["vendor_ids"])))

    if scope["conv_ids"]:
        await db.execute(delete(WaMessage).where(WaMessage.conversation_id.in_(scope["conv_ids"])))
        await db.execute(delete(WaConversation).where(WaConversation.id.in_(scope["conv_ids"])))

    if scope["deletable_property_ids"]:
        await db.execute(delete(Property).where(Property.id.in_(scope["deletable_property_ids"])))

    if scope["vendor_ids"]:
        await db.execute(delete(User).where(User.id.in_(scope["vendor_ids"])))

    await db.commit()

    return {
        "properties_deleted": len(scope["deletable_property_ids"]),
        "properties_kept_in_use": len(scope["kept_property_ids"]),
        "vendors_deleted": len(scope["vendor_ids"]),
        "conversations_deleted": len(scope["conv_ids"]),
        "messages_deleted": scope["n_messages"],
        "dmo_assignments_deleted": scope["n_dmo_assignments"],
        "dmo_logs_deleted": scope["n_dmo_logs"],
    }
