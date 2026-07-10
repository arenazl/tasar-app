"""Tests de humo de /api/properties (WO F3-06): CRUD scoped por workspace
+ aislamiento multi-tenant (absorbe el vector de propiedades del invariante
[1] de scripts/smoke_core.py, pero corriendo in-process contra SQLite en
vez de requerir MySQL local + servidor levantado)."""
from tests.conftest import register_workspace, unique_stamp

PROPERTY_PAYLOAD = {
    "title": "[TEST] Depto Palermo",
    "property_type": "departamento",
    "operation": "venta",
    "province": "CABA",
    "city": "Palermo",
    "address": "Calle Test 123",
    "total_area_m2": 55,
    "rooms": 3,
    "asking_price": 150000,
    "currency": "USD",
}


async def test_create_list_and_get_property(client):
    ws = await register_workspace(client)

    created = await client.post("/api/properties", json=PROPERTY_PAYLOAD, headers=ws["headers"])
    assert created.status_code == 200
    prop = created.json()
    assert prop["workspace_id"] == ws["user"]["workspace_id"]
    assert prop["title"] == PROPERTY_PAYLOAD["title"]

    listed = await client.get("/api/properties", headers=ws["headers"])
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()] == [prop["id"]]

    fetched = await client.get(f"/api/properties/{prop['id']}", headers=ws["headers"])
    assert fetched.status_code == 200
    assert fetched.json()["id"] == prop["id"]


async def test_properties_are_scoped_by_workspace(client):
    ws_a = await register_workspace(client, workspace_name=f"[TEST] WS-A {unique_stamp()}")
    ws_b = await register_workspace(client, workspace_name=f"[TEST] WS-B {unique_stamp()}")

    created = await client.post("/api/properties", json=PROPERTY_PAYLOAD, headers=ws_a["headers"])
    assert created.status_code == 200
    prop_a_id = created.json()["id"]

    # Workspace B no debe ver la propiedad de A en su listado...
    listed_b = await client.get("/api/properties", headers=ws_b["headers"])
    assert listed_b.status_code == 200
    assert prop_a_id not in [p["id"] for p in listed_b.json()]

    # ...ni acceder a ella por id directo (404, no 403 -- anti-IDOR, mismo
    # criterio que ensure_study_in_workspace en core/security.py).
    fetched_b = await client.get(f"/api/properties/{prop_a_id}", headers=ws_b["headers"])
    assert fetched_b.status_code == 404


async def test_get_nonexistent_property_returns_404(client):
    ws = await register_workspace(client)

    r = await client.get("/api/properties/999999", headers=ws["headers"])

    assert r.status_code == 404


async def test_delete_property_removes_it_from_list(client):
    ws = await register_workspace(client)
    created = await client.post("/api/properties", json=PROPERTY_PAYLOAD, headers=ws["headers"])
    prop_id = created.json()["id"]

    deleted = await client.delete(f"/api/properties/{prop_id}", headers=ws["headers"])
    assert deleted.status_code == 200

    listed = await client.get("/api/properties", headers=ws["headers"])
    assert listed.json() == []
