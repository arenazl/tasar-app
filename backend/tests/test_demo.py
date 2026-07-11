"""Tests de /api/demo — onboarding self-service (WO F5-03).

Cubre la aceptacion del WO:
  - generar demo marca TODO `is_demo=True` (propiedades, vendedores,
    conversaciones) y en cantidades correctas;
  - borrar demo con `confirm=false` es dry-run (no borra nada);
  - borrar demo con datos REALES mezclados NO toca los reales (el caso que
    pide explicitamente el WO: "probar con datos mezclados");
  - una propiedad demo referenciada por un dato real (ej. una Visit) no se
    borra -- se informa como "kept_in_use" en vez de romper la FK;
  - solo admin puede generar/borrar demo (403 para vendedor).
"""
from datetime import datetime, timezone

from sqlalchemy import select

from core.security import hash_password
from models.client import Client
from models.property import Property
from models.user import User
from models.visit import Visit
from tests.conftest import register_workspace, unique_stamp


PROPERTY_PAYLOAD = {
    "title": "[TEST] Depto real del cliente",
    "property_type": "departamento",
    "operation": "venta",
    "province": "CABA",
    "city": "Palermo",
    "address": "Calle Real 456",
    "total_area_m2": 60,
    "rooms": 2,
    "asking_price": 160000,
    "currency": "USD",
}


async def test_generate_demo_marks_everything_is_demo(client, db_session):
    ws = await register_workspace(client)

    r = await client.post("/api/demo/generate", json={"n_properties": 6}, headers=ws["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["properties_created"] == 6
    assert body["vendors_created"] == 3
    assert body["conversations_created"] == 5
    assert body["messages_created"] > 0

    ws_id = ws["user"]["workspace_id"]
    props = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id)
    )).scalars().all()
    assert len(props) == 6
    assert all(p.is_demo for p in props)
    assert all(p.title.startswith("[DEMO]") for p in props)

    vendors = (await db_session.execute(
        select(User).where(User.workspace_id == ws_id, User.role == "asesor")
    )).scalars().all()
    assert len(vendors) == 3
    assert all(v.is_demo for v in vendors)
    assert all(v.full_name.startswith("[DEMO]") for v in vendors)


async def test_generate_demo_is_idempotent_no_duplicates(client, db_session):
    """Apretar "cargar datos de ejemplo" dos veces no acumula filas (purge
    interno antes de generar) ni choca contra el UNIQUE de email/phone_jid."""
    ws = await register_workspace(client)

    r1 = await client.post("/api/demo/generate", json={"n_properties": 4}, headers=ws["headers"])
    assert r1.status_code == 200, r1.text
    r2 = await client.post("/api/demo/generate", json={"n_properties": 4}, headers=ws["headers"])
    assert r2.status_code == 200, r2.text

    ws_id = ws["user"]["workspace_id"]
    props = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id, Property.is_demo.is_(True))
    )).scalars().all()
    assert len(props) == 4  # no 8

    vendors = (await db_session.execute(
        select(User).where(User.workspace_id == ws_id, User.is_demo.is_(True))
    )).scalars().all()
    assert len(vendors) == 3  # no 6


async def test_purge_dry_run_does_not_delete(client, db_session):
    ws = await register_workspace(client)
    await client.post("/api/demo/generate", json={"n_properties": 5}, headers=ws["headers"])

    r = await client.post("/api/demo/purge", json={"confirm": False}, headers=ws["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True
    assert body["properties_to_delete"] == 5
    assert body["vendors_to_delete"] == 3
    assert body["conversations_to_delete"] == 5

    ws_id = ws["user"]["workspace_id"]
    still_there = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id, Property.is_demo.is_(True))
    )).scalars().all()
    assert len(still_there) == 5  # dry-run: nada se borro


async def test_purge_confirm_deletes_demo_but_not_real_mixed_data(client, db_session):
    """El caso central del WO: datos reales y demo MEZCLADOS en el mismo
    workspace -- purgar demo no puede tocar lo real."""
    ws = await register_workspace(client)
    ws_id = ws["user"]["workspace_id"]

    # Dato REAL cargado a mano por el admin (no demo).
    real_prop = await client.post("/api/properties", json=PROPERTY_PAYLOAD, headers=ws["headers"])
    assert real_prop.status_code == 200
    real_prop_id = real_prop.json()["id"]

    real_vendor = User(
        workspace_id=ws_id, email=f"real-vendor-{unique_stamp()}@example.com",
        password_hash=hash_password("vendedor123"), full_name="Vendedor Real",
        role="asesor", is_active=True, is_demo=False,
    )
    db_session.add(real_vendor)
    await db_session.commit()

    # Datos DEMO.
    gen = await client.post("/api/demo/generate", json={"n_properties": 4}, headers=ws["headers"])
    assert gen.status_code == 200, gen.text

    # Purga con confirm=true.
    r = await client.post("/api/demo/purge", json={"confirm": True}, headers=ws["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is False
    assert body["properties_deleted"] == 4
    assert body["vendors_deleted"] == 3
    assert body["conversations_deleted"] == 5

    # Lo REAL sigue intacto.
    props_left = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id)
    )).scalars().all()
    assert [p.id for p in props_left] == [real_prop_id]

    users_left = (await db_session.execute(
        select(User).where(User.workspace_id == ws_id, User.role == "asesor")
    )).scalars().all()
    assert len(users_left) == 1
    assert users_left[0].id == real_vendor.id

    # Lo demo ya no esta.
    demo_left = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id, Property.is_demo.is_(True))
    )).scalars().all()
    assert demo_left == []


async def test_purge_keeps_demo_property_referenced_by_real_data(client, db_session):
    """Una propiedad demo usada en una Visit REAL no se borra (evita romper la
    FK) -- se informa como kept_in_use en vez de crashear."""
    ws = await register_workspace(client)
    ws_id = ws["user"]["workspace_id"]

    gen = await client.post("/api/demo/generate", json={"n_properties": 3}, headers=ws["headers"])
    assert gen.status_code == 200, gen.text

    demo_prop = (await db_session.execute(
        select(Property).where(Property.workspace_id == ws_id, Property.is_demo.is_(True))
    )).scalars().first()

    # Visita REAL contra una propiedad demo (caso de uso legitimo: el admin
    # prueba el flujo real sobre datos de ejemplo antes de cargar los suyos).
    client_row = Client(workspace_id=ws_id, name="Cliente real de prueba")
    db_session.add(client_row)
    await db_session.flush()
    visit = Visit(
        workspace_id=ws_id, client_id=client_row.id, property_id=demo_prop.id,
        vendor_id=ws["user"]["id"], scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(visit)
    await db_session.commit()

    r = await client.post("/api/demo/purge", json={"confirm": True}, headers=ws["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["properties_kept_in_use"] == 1
    assert body["properties_deleted"] == 2  # las otras 2 si se borraron

    kept = (await db_session.execute(
        select(Property).where(Property.id == demo_prop.id)
    )).scalar_one_or_none()
    assert kept is not None  # sigue viva porque la Visit la referencia


async def test_vendedor_cannot_generate_or_purge_demo(client, db_session):
    ws = await register_workspace(client)
    vendor = User(
        workspace_id=ws["user"]["workspace_id"],
        email=f"vendor-{unique_stamp()}@example.com",
        password_hash=hash_password("vendedor123"), full_name="Vendedor",
        role="asesor", is_active=True,
    )
    db_session.add(vendor)
    await db_session.commit()

    from core.security import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(vendor.id)})}"}

    r1 = await client.post("/api/demo/generate", json={"n_properties": 3}, headers=headers)
    assert r1.status_code == 403

    r2 = await client.post("/api/demo/purge", json={"confirm": True}, headers=headers)
    assert r2.status_code == 403
