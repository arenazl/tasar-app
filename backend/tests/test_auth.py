"""Tests de humo de /api/auth (WO F3-06): register, login, /me."""
import pytest

from tests.conftest import register_workspace, unique_stamp


async def test_register_creates_workspace_and_broker_user(client):
    # El que registra la inmobiliaria es el titular: broker (WO F6-06).
    data = await register_workspace(client)

    assert data["user"]["role"] == "broker"
    assert data["access_token"]


async def test_login_with_correct_credentials_returns_token(client):
    stamp = unique_stamp()
    email = f"login-{stamp}@example.com"
    await register_workspace(client, email=email, password="correcta123")

    r = await client.post("/api/auth/login", json={"email": email, "password": "correcta123"})

    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_login_with_wrong_password_returns_401(client):
    stamp = unique_stamp()
    email = f"wrongpw-{stamp}@example.com"
    await register_workspace(client, email=email, password="correcta123")

    r = await client.post("/api/auth/login", json={"email": email, "password": "incorrecta"})

    assert r.status_code == 401


async def test_me_without_token_returns_401(client):
    r = await client.get("/api/auth/me")

    assert r.status_code == 401


async def test_me_with_valid_token_returns_current_user(client):
    data = await register_workspace(client)

    r = await client.get("/api/auth/me", headers=data["headers"])

    assert r.status_code == 200
    assert r.json()["email"] == data["user"]["email"]
