from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property, PropertyPhoto
from schemas.property import PropertyCreate, PropertyUpdate, PropertyOut, PropertyPhotoOut
from services.cloudinary_service import upload_image, delete_image
from services.ai_router import analyze_property
import json


router = APIRouter(prefix="/api/properties", tags=["properties"])


async def _serialize(db: AsyncSession, p: Property) -> PropertyOut:
    q = await db.execute(
        select(PropertyPhoto).where(PropertyPhoto.property_id == p.id).order_by(PropertyPhoto.order)
    )
    photos = [PropertyPhotoOut.model_validate(ph) for ph in q.scalars().all()]
    out = PropertyOut.model_validate(p)
    out.photos = photos
    return out


@router.get("", response_model=List[PropertyOut])
async def list_properties(
    q: Optional[str] = None,
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Property).where(Property.workspace_id == user.workspace_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Property.title.like(like)) | (Property.address.like(like)))
    if city:
        stmt = stmt.where(Property.city == city)
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    stmt = stmt.order_by(Property.created_at.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [await _serialize(db, p) for p in items]


@router.get("/{property_id}", response_model=PropertyOut)
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    return await _serialize(db, p)


@router.post("", response_model=PropertyOut)
async def create_property(
    body: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = Property(
        **body.model_dump(),
        workspace_id=user.workspace_id,
        created_by=user.id,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return await _serialize(db, p)


@router.put("/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: int,
    body: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    return await _serialize(db, p)


@router.delete("/{property_id}")
async def delete_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    # Borrar fotos en Cloudinary
    photos = (await db.execute(
        select(PropertyPhoto).where(PropertyPhoto.property_id == p.id)
    )).scalars().all()
    for ph in photos:
        if ph.public_id:
            try:
                delete_image(ph.public_id)
            except Exception:
                pass
    await db.execute(delete(PropertyPhoto).where(PropertyPhoto.property_id == p.id))
    await db.delete(p)
    await db.commit()
    return {"ok": True}


@router.post("/{property_id}/photos", response_model=PropertyPhotoOut)
async def upload_photo(
    property_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")

    content = await file.read()
    up = await upload_image(content, folder=f"properties/{p.id}")
    ph = PropertyPhoto(
        property_id=p.id,
        url=up["url"],
        public_id=up["public_id"],
        caption=caption,
        order=0,
    )
    db.add(ph)
    await db.commit()
    await db.refresh(ph)
    return PropertyPhotoOut.model_validate(ph)


@router.post("/{property_id}/analyze")
async def ai_analyze_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Disparar análisis IA de la propiedad con Claude headless."""
    res = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")

    payload = {
        "title": p.title,
        "type": p.property_type,
        "city": p.city,
        "province": p.province,
        "address": p.address,
        "total_area_m2": p.total_area_m2,
        "covered_area_m2": p.covered_area_m2,
        "rooms": p.rooms,
        "bedrooms": p.bedrooms,
        "bathrooms": p.bathrooms,
        "age_years": p.age_years,
        "condition": p.condition,
        "description": p.description,
    }
    analysis = await analyze_property(payload)
    p.ai_analysis = json.dumps(analysis, ensure_ascii=False)
    await db.commit()
    return analysis
