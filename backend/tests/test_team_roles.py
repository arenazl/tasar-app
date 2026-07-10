"""Tests de autorizacion por rol + round-robin de disponibilidad (WO F4-05).

Cubre la aceptacion del WO:
  - un vendedor NO puede tocar settings ni equipo (403 real via require_role);
  - el flujo de invitacion end-to-end (invitar -> token -> alta con el rol
    correcto en el workspace correcto);
  - el round-robin saltea a los vendedores con is_available=False.

Corre in-process contra SQLite (mismo patron que el resto de tests/), sin
MySQL ni servidor levantado.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.user import User
from models.invitation import Invitation
from tests.conftest import register_workspace, unique_stamp


async def _make_vendor(db, workspace_id: int, *, email: str | None = None,
                       is_available: bool = True, last_assigned_at=None,
                       role: str = "vendedor") -> User:
    u = User(
        workspace_id=workspace_id,
        email=email or f"vendor-{unique_stamp()}@example.com",
        password_hash=hash_password("vendedor123"),
        full_name="[TEST] Vendedor",
        role=role,
        is_active=True,
        is_available=is_available,
        last_assigned_at=last_assigned_at,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ── 403 del vendedor sobre settings y equipo ─────────────────────────────────

async def test_vendedor_cannot_write_settings(client, db_session):
    admin = await register_workspace(client)
    vendor = await _make_vendor(db_session, admin["user"]["workspace_id"])

    r = await client.put("/api/settings/claude_model", headers=_auth(vendor), json={"value": "opus"})
    assert r.status_code == 403


async def test_vendedor_cannot_list_team(client, db_session):
    admin = await register_workspace(client)
    vendor = await _make_vendor(db_session, admin["user"]["workspace_id"])

    r = await client.get("/api/team/members", headers=_auth(vendor))
    assert r.status_code == 403


async def test_vendedor_cannot_invite(client, db_session):
    admin = await register_workspace(client)
    vendor = await _make_vendor(db_session, admin["user"]["workspace_id"])

    r = await client.post("/api/team/invitations", headers=_auth(vendor),
                          json={"email": "x@example.com", "role": "vendedor"})
    assert r.status_code == 403


async def test_admin_can_list_team(client, db_session):
    admin = await register_workspace(client)
    await _make_vendor(db_session, admin["user"]["workspace_id"])

    r = await client.get("/api/team/members", headers=admin["headers"])
    assert r.status_code == 200
    emails = [m["email"] for m in r.json()]
    assert admin["user"]["email"] in emails
    assert len(r.json()) == 2  # admin + vendedor


# ── Vendedor edita SU PROPIA disponibilidad (self-service) ───────────────────

async def test_vendedor_can_toggle_own_availability(client, db_session):
    admin = await register_workspace(client)
    vendor = await _make_vendor(db_session, admin["user"]["workspace_id"], is_available=False)

    r = await client.patch("/api/auth/me", headers=_auth(vendor), json={"is_available": True})
    assert r.status_code == 200
    assert r.json()["is_available"] is True


# ── Flujo de invitacion end-to-end ───────────────────────────────────────────

async def test_invitation_flow_creates_user_in_right_workspace_and_role(client, db_session):
    admin = await register_workspace(client)
    ws_id = admin["user"]["workspace_id"]

    invited_email = f"invitee-{unique_stamp()}@example.com"
    r = await client.post("/api/team/invitations", headers=admin["headers"],
                          json={"email": invited_email, "role": "supervisor", "full_name": "Pato Nuevo"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pendiente"
    assert r.json()["role"] == "supervisor"

    # El token NO se expone en la API (seguridad): se lee de la fila para el test.
    inv = (await db_session.execute(
        select(Invitation).where(Invitation.email == invited_email)
    )).scalar_one()
    token = inv.token

    # Pantalla de aceptacion (publica): datos correctos y valida.
    info = await client.get(f"/api/auth/invitation/{token}")
    assert info.status_code == 200
    assert info.json()["valid"] is True
    assert info.json()["email"] == invited_email
    assert info.json()["role"] == "supervisor"

    # Alta via token.
    acc = await client.post("/api/auth/accept-invitation",
                            json={"token": token, "password": "nueva12345"})
    assert acc.status_code == 200, acc.text
    new_user = acc.json()["user"]
    assert new_user["role"] == "supervisor"           # rol del token, no del cliente
    assert new_user["workspace_id"] == ws_id          # workspace del token
    assert acc.json()["access_token"]

    # Un solo uso: reintentar el mismo token falla.
    again = await client.post("/api/auth/accept-invitation",
                              json={"token": token, "password": "otra12345"})
    assert again.status_code == 400

    # El nuevo usuario puede loguearse.
    login = await client.post("/api/auth/login", json={"email": invited_email, "password": "nueva12345"})
    assert login.status_code == 200


async def test_expired_invitation_rejected(client, db_session):
    admin = await register_workspace(client)
    r = await client.post("/api/team/invitations", headers=admin["headers"],
                          json={"email": f"exp-{unique_stamp()}@example.com", "role": "vendedor"})
    inv = (await db_session.execute(
        select(Invitation).where(Invitation.id == r.json()["id"])
    )).scalar_one()
    inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    acc = await client.post("/api/auth/accept-invitation",
                            json={"token": inv.token, "password": "nueva12345"})
    assert acc.status_code == 400


# ── Round-robin saltea a los no disponibles ──────────────────────────────────

async def test_round_robin_skips_unavailable(client, db_session):
    from services.bot_tools import asignar_round_robin

    admin = await register_workspace(client)
    ws_id = admin["user"]["workspace_id"]

    # 3 vendedores: v1 disponible (nunca asignado), v2 NO disponible, v3 disponible
    # (asignado hace poco). Orden esperado: last_assigned_at ASC, NULL primero.
    v1 = await _make_vendor(db_session, ws_id, is_available=True, last_assigned_at=None)
    v2 = await _make_vendor(db_session, ws_id, is_available=False, last_assigned_at=None)
    v3 = await _make_vendor(db_session, ws_id, is_available=True,
                            last_assigned_at=datetime.now(timezone.utc))

    # 1ra asignacion -> v1 (disponible, last_assigned_at NULL primero), nunca v2.
    pick1 = await asignar_round_robin(db_session, ws_id)
    assert pick1 is not None
    assert pick1.id == v1.id
    assert pick1.id != v2.id

    # Simular que a v1 se le asigno -> proxima debe ser v3, jamas v2.
    v1.last_assigned_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    await db_session.commit()
    pick2 = await asignar_round_robin(db_session, ws_id)
    assert pick2 is not None
    assert pick2.id == v3.id
    assert pick2.id != v2.id

    # Si nadie esta disponible -> None (el bot informa "no hay asesores").
    v1.is_available = False
    v3.is_available = False
    await db_session.commit()
    assert await asignar_round_robin(db_session, ws_id) is None
