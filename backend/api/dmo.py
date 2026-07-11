"""DMO — templates, asignaciones y dia del vendedor (WO F2-01).

Consolida en un router (prefix `/api/dmo`) los tres routers que en AgentFlow
vivian separados (`dmo-templates`, `dmo-assignments`, `dmo`), mas el catalogo de
coaches que va aparte en `api/coaches.py`.

Multi-tenant:
  - Templates VISIBLES para un tenant = catalogo oficial global (workspace_id
    NULL) + los custom de su propio workspace. Un tenant NO puede editar/borrar
    los oficiales: solo clonarlos a su workspace.
  - Assignments, logs y el "office default" son siempre por workspace.

Roles (WO F6-06): coordinador+ gestiona templates/asignaciones/coaches (es la
herramienta comercial de manager). El asesor ve y registra SU dia.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.orm import selectinload
from datetime import date as date_cls

from core.database import get_db
from core.security import get_current_user, has_min_role
from models.user import User
from models.dmo import (
    Coach, DmoTemplate, DmoBlock, DmoAssignment, DmoLog,
    METRIC_TYPE_QUANTITY,
)
from schemas.dmo import (
    DmoTemplateCreate, DmoTemplateUpdate, DmoTemplateOut, DmoBlockOut,
    DmoAssignmentCreate, DmoAssignmentOut, VendorOut,
    DmoLogCreate, DmoLogOut, DmoDayOut,
)

router = APIRouter(prefix="/api/dmo", tags=["dmo"])


def _require_manager(user: User) -> None:
    if not has_min_role(user, "coordinador"):
        raise HTTPException(status_code=403, detail="Solo coordinador o superior puede gestionar el DMO")


def _visible_templates_filter(workspace_id: int):
    """Templates que ve un tenant: catalogo oficial global (workspace_id NULL)
    + los custom de su propio workspace."""
    return or_(DmoTemplate.workspace_id.is_(None), DmoTemplate.workspace_id == workspace_id)


def _with_relations(stmt):
    return stmt.options(selectinload(DmoTemplate.blocks), selectinload(DmoTemplate.coach))


def _template_out(t: DmoTemplate, assignments_count: int = 0) -> DmoTemplateOut:
    return DmoTemplateOut(
        id=t.id,
        workspace_id=t.workspace_id,
        coach_id=t.coach_id,
        name=t.name,
        description=t.description,
        market=t.market,
        is_active=t.is_active,
        is_office_default=t.is_office_default,
        coach_name=t.coach.name if t.coach else None,
        is_official=t.workspace_id is None,
        blocks=[DmoBlockOut.model_validate(b) for b in sorted(t.blocks, key=lambda b: b.sort_order)],
        assignments_count=assignments_count,
        created_at=t.created_at,
    )


# ============================ TEMPLATES ============================

@router.get("/templates", response_model=list[DmoTemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(
        _with_relations(
            select(DmoTemplate)
            .where(_visible_templates_filter(user.workspace_id))
            .order_by(DmoTemplate.is_office_default.desc(), DmoTemplate.name)
        )
    )
    templates = r.scalars().unique().all()
    # Conteo de asignaciones POR WORKSPACE (no filtra los de otros tenants).
    asig = await db.execute(
        select(DmoAssignment.template_id, func.count(DmoAssignment.id))
        .where(DmoAssignment.workspace_id == user.workspace_id)
        .group_by(DmoAssignment.template_id)
    )
    counts = {tid: cnt for tid, cnt in asig.all()}
    return [_template_out(t, counts.get(t.id, 0)) for t in templates]


@router.get("/templates/{template_id}", response_model=DmoTemplateOut)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = (await db.execute(
        _with_relations(select(DmoTemplate).where(
            DmoTemplate.id == template_id,
            _visible_templates_filter(user.workspace_id),
        ))
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template no encontrado")
    cnt = (await db.execute(
        select(func.count(DmoAssignment.id)).where(
            DmoAssignment.template_id == template_id,
            DmoAssignment.workspace_id == user.workspace_id,
        )
    )).scalar_one() or 0
    return _template_out(t, cnt)


async def _clear_office_default(db: AsyncSession, workspace_id: int, keep_id: int | None = None) -> None:
    """Desmarca el office default de OTROS templates del workspace."""
    stmt = select(DmoTemplate).where(
        DmoTemplate.workspace_id == workspace_id,
        DmoTemplate.is_office_default.is_(True),
    )
    if keep_id is not None:
        stmt = stmt.where(DmoTemplate.id != keep_id)
    for t in (await db.execute(stmt)).scalars().all():
        t.is_office_default = False


@router.post("/templates", response_model=DmoTemplateOut)
async def create_template(
    payload: DmoTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    # El coach es del catalogo global.
    if not (await db.execute(select(Coach).where(Coach.id == payload.coach_id))).scalar_one_or_none():
        raise HTTPException(400, "Coach no existe")

    if payload.is_office_default:
        await _clear_office_default(db, user.workspace_id)

    t = DmoTemplate(
        workspace_id=user.workspace_id,
        coach_id=payload.coach_id,
        name=payload.name,
        description=payload.description,
        market=payload.market,
        is_active=payload.is_active,
        is_office_default=payload.is_office_default,
    )
    db.add(t)
    await db.flush()
    for idx, b in enumerate(payload.blocks):
        db.add(DmoBlock(
            template_id=t.id,
            name=b.name,
            description=b.description,
            start_time=b.start_time,
            end_time=b.end_time,
            color=b.color,
            sort_order=b.sort_order if b.sort_order else idx,
            is_money_block=b.is_money_block,
            metric_type=b.metric_type,
            metric_label=b.metric_label,
            metric_goal=b.metric_goal,
        ))
    await db.commit()
    # Recargar con relaciones para el Out.
    t = (await db.execute(_with_relations(select(DmoTemplate).where(DmoTemplate.id == t.id)))).scalar_one()
    return _template_out(t)


@router.patch("/templates/{template_id}", response_model=DmoTemplateOut)
async def update_template(
    template_id: int,
    payload: DmoTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    # Solo templates PROPIOS del workspace (los oficiales globales no se editan).
    t = (await db.execute(
        select(DmoTemplate).where(
            DmoTemplate.id == template_id,
            DmoTemplate.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template no encontrado (o es del catalogo oficial: cloná primero)")

    data = payload.model_dump(exclude_unset=True)
    new_blocks = data.pop("blocks", None)

    if data.get("is_office_default"):
        await _clear_office_default(db, user.workspace_id, keep_id=template_id)

    for k, v in data.items():
        setattr(t, k, v)

    if new_blocks is not None:
        await db.execute(delete(DmoBlock).where(DmoBlock.template_id == template_id))
        for idx, b in enumerate(new_blocks):
            db.add(DmoBlock(
                template_id=template_id,
                name=b["name"],
                description=b.get("description"),
                start_time=b["start_time"],
                end_time=b["end_time"],
                color=b.get("color", "#3b82f6"),
                sort_order=b.get("sort_order", idx),
                is_money_block=b.get("is_money_block", False),
                metric_type=b.get("metric_type", "checkbox"),
                metric_label=b.get("metric_label"),
                metric_goal=b.get("metric_goal", 0),
            ))

    await db.commit()
    t = (await db.execute(_with_relations(select(DmoTemplate).where(DmoTemplate.id == template_id)))).scalar_one()
    return _template_out(t)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    t = (await db.execute(
        select(DmoTemplate).where(
            DmoTemplate.id == template_id,
            DmoTemplate.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template no encontrado (o es del catalogo oficial: no se borra)")
    n = (await db.execute(
        select(func.count(DmoAssignment.id)).where(
            DmoAssignment.template_id == template_id,
            DmoAssignment.workspace_id == user.workspace_id,
        )
    )).scalar_one()
    if n:
        raise HTTPException(400, "Hay vendedores asignados a este template. Reasignalos primero.")
    await db.delete(t)
    await db.commit()
    return {"ok": True}


@router.post("/templates/{template_id}/clone", response_model=DmoTemplateOut)
async def clone_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clona un template VISIBLE (oficial global o propio) al workspace del tenant."""
    _require_manager(user)
    orig = (await db.execute(
        _with_relations(select(DmoTemplate).where(
            DmoTemplate.id == template_id,
            _visible_templates_filter(user.workspace_id),
        ))
    )).scalar_one_or_none()
    if not orig:
        raise HTTPException(404, "Template no encontrado")

    nuevo = DmoTemplate(
        workspace_id=user.workspace_id,
        coach_id=orig.coach_id,
        name=f"{orig.name} (copia)",
        description=orig.description,
        market=orig.market,
        is_active=True,
        is_office_default=False,
    )
    db.add(nuevo)
    await db.flush()
    for b in orig.blocks:
        db.add(DmoBlock(
            template_id=nuevo.id,
            name=b.name,
            description=b.description,
            start_time=b.start_time,
            end_time=b.end_time,
            color=b.color,
            sort_order=b.sort_order,
            is_money_block=b.is_money_block,
            metric_type=b.metric_type,
            metric_label=b.metric_label,
            metric_goal=b.metric_goal,
        ))
    await db.commit()
    nuevo = (await db.execute(_with_relations(select(DmoTemplate).where(DmoTemplate.id == nuevo.id)))).scalar_one()
    return _template_out(nuevo)


# ============================ VENDORS ============================

@router.get("/vendors", response_model=list[VendorOut])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Vendedores del workspace (para la pantalla de asignaciones)."""
    _require_manager(user)
    rows = (await db.execute(
        select(User).where(
            User.workspace_id == user.workspace_id,
            User.role == "asesor",
        ).order_by(User.full_name)
    )).scalars().all()
    return [VendorOut.model_validate(v) for v in rows]


# ============================ ASSIGNMENTS ============================

def _assignment_out(a: DmoAssignment) -> DmoAssignmentOut:
    return DmoAssignmentOut(
        id=a.id,
        vendor_id=a.vendor_id,
        vendor_name=a.vendor.full_name if a.vendor else None,
        template_id=a.template_id,
        template_name=a.template.name if a.template else None,
        coach_name=(a.template.coach.name if a.template and a.template.coach else None),
        assigned_at=a.assigned_at,
    )


@router.get("/assignments", response_model=list[DmoAssignmentOut])
async def list_assignments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(
        select(DmoAssignment)
        .where(DmoAssignment.workspace_id == user.workspace_id)
        .options(
            selectinload(DmoAssignment.vendor),
            selectinload(DmoAssignment.template).selectinload(DmoTemplate.coach),
        )
    )
    return [_assignment_out(a) for a in r.scalars().all()]


@router.post("/assignments", response_model=DmoAssignmentOut)
async def upsert_assignment(
    payload: DmoAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    # Vendor debe pertenecer al mismo workspace y ser vendedor.
    v = (await db.execute(
        select(User).where(User.id == payload.vendor_id, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Vendedor no encontrado")
    if v.role != "asesor":
        raise HTTPException(400, "El usuario no es asesor")
    # Template debe ser visible al workspace.
    if not (await db.execute(
        select(DmoTemplate).where(
            DmoTemplate.id == payload.template_id,
            _visible_templates_filter(user.workspace_id),
        )
    )).scalar_one_or_none():
        raise HTTPException(400, "Template no existe o no es visible para tu workspace")

    a = (await db.execute(
        select(DmoAssignment).where(
            DmoAssignment.workspace_id == user.workspace_id,
            DmoAssignment.vendor_id == payload.vendor_id,
        )
    )).scalar_one_or_none()
    if a:
        a.template_id = payload.template_id
    else:
        a = DmoAssignment(
            workspace_id=user.workspace_id,
            vendor_id=payload.vendor_id,
            template_id=payload.template_id,
        )
        db.add(a)
    await db.commit()
    a = (await db.execute(
        select(DmoAssignment).where(DmoAssignment.id == a.id).options(
            selectinload(DmoAssignment.vendor),
            selectinload(DmoAssignment.template).selectinload(DmoTemplate.coach),
        )
    )).scalar_one()
    return _assignment_out(a)


@router.delete("/assignments/{vendor_id}")
async def remove_assignment(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    a = (await db.execute(
        select(DmoAssignment).where(
            DmoAssignment.workspace_id == user.workspace_id,
            DmoAssignment.vendor_id == vendor_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Asignacion no encontrada")
    await db.delete(a)
    await db.commit()
    return {"ok": True}


# ============================ DIA / LOG ============================

async def _resolve_template_for_vendor(db: AsyncSession, workspace_id: int, vendor_id: int) -> DmoTemplate | None:
    """Resuelve el template del vendedor: asignacion explicita -> default de la
    oficina (por workspace). Devuelve None si no hay ninguno."""
    a = (await db.execute(
        select(DmoAssignment).where(
            DmoAssignment.workspace_id == workspace_id,
            DmoAssignment.vendor_id == vendor_id,
        )
    )).scalar_one_or_none()
    if a:
        t = (await db.execute(
            _with_relations(select(DmoTemplate).where(DmoTemplate.id == a.template_id))
        )).scalar_one_or_none()
        if t:
            return t
    # Fallback: default de la oficina (workspace-scoped).
    return (await db.execute(
        _with_relations(select(DmoTemplate).where(
            DmoTemplate.workspace_id == workspace_id,
            DmoTemplate.is_office_default.is_(True),
        ).limit(1))
    )).scalar_one_or_none()


@router.get("/dia", response_model=DmoDayOut)
async def get_day(
    fecha: date_cls | None = None,
    vendor_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    day = fecha or date_cls.today()
    vid = vendor_id or user.id
    if user.role == "asesor":
        vid = user.id  # el asesor solo ve su propio dia

    # El target vendor debe estar en el mismo workspace (anti cross-tenant).
    target = (await db.execute(
        select(User).where(User.id == vid, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Vendedor no encontrado")

    template = await _resolve_template_for_vendor(db, user.workspace_id, vid)
    if not template:
        return DmoDayOut(
            date=day, template=None, blocks=[], logs=[],
            conversations_goal=target.daily_conversations_goal or 0,
            conversations_done=0, completion_pct=0,
        )

    blocks = sorted(template.blocks, key=lambda b: b.sort_order)
    block_ids = [b.id for b in blocks]

    logs = (await db.execute(
        select(DmoLog).where(and_(
            DmoLog.workspace_id == user.workspace_id,
            DmoLog.vendor_id == vid,
            DmoLog.date == day,
            DmoLog.block_id.in_(block_ids),
        ))
    )).scalars().all()

    log_by_block = {l.block_id: l for l in logs}
    conv_done = 0
    for b in blocks:
        log = log_by_block.get(b.id)
        if not log:
            continue
        is_conv = b.is_money_block or (b.metric_label and "conversa" in b.metric_label.lower())
        if is_conv and b.metric_type == METRIC_TYPE_QUANTITY:
            conv_done += log.metric_value

    completed = sum(1 for l in logs if l.completed)
    pct = int(round((completed / max(len(blocks), 1)) * 100))

    return DmoDayOut(
        date=day,
        template=_template_out(template),
        blocks=[DmoBlockOut.model_validate(b) for b in blocks],
        logs=[DmoLogOut.model_validate(l) for l in logs],
        conversations_goal=target.daily_conversations_goal or 0,
        conversations_done=conv_done,
        completion_pct=pct,
    )


@router.post("/log", response_model=DmoLogOut)
async def upsert_log(
    payload: DmoLogCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # El bloque tiene que pertenecer a un template VISIBLE para el workspace.
    block = (await db.execute(
        select(DmoBlock).join(DmoTemplate, DmoTemplate.id == DmoBlock.template_id).where(
            DmoBlock.id == payload.block_id,
            _visible_templates_filter(user.workspace_id),
        )
    )).scalar_one_or_none()
    if not block:
        raise HTTPException(404, "Bloque no existe")

    # Upsert por (workspace, vendor, block, date). El UNIQUE del schema protege
    # contra duplicados; ademas limpiamos cualquier duplicado historico previo.
    rows = (await db.execute(
        select(DmoLog).where(and_(
            DmoLog.workspace_id == user.workspace_id,
            DmoLog.vendor_id == user.id,
            DmoLog.block_id == payload.block_id,
            DmoLog.date == payload.date,
        )).order_by(DmoLog.id.asc())
    )).scalars().all()
    log = rows[0] if rows else None
    for dup in rows[1:]:
        await db.delete(dup)

    if log:
        log.completed = payload.completed
        log.metric_value = payload.metric_value
        log.notes = payload.notes
    else:
        log = DmoLog(
            workspace_id=user.workspace_id,
            vendor_id=user.id,
            block_id=payload.block_id,
            date=payload.date,
            completed=payload.completed,
            metric_value=payload.metric_value,
            notes=payload.notes,
        )
        db.add(log)
    await db.commit()
    await db.refresh(log)
    return DmoLogOut.model_validate(log)
