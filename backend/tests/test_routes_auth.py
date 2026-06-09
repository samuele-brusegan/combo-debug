"""Test di integrazione su autenticazione e protezione delle route."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.core.config import Settings
from app.main import create_app
from app.services.auth_service import AuthService


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Client con auth disabilitata (configurazione di default)."""
    app = create_app(Settings())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
    """Client con autenticazione abilitata (via override del servizio auth)."""
    app = create_app(Settings())
    auth = AuthService(
        Settings(auth_enabled=True, auth_username="admin", auth_password="pw")
    )
    app.dependency_overrides[get_auth_service] = lambda: auth
    with TestClient(app) as test_client:
        yield test_client


def test_set_param_without_confirm_is_409(client: TestClient) -> None:
    """La modifica di un parametro senza conferma deve dare 409."""
    response = client.post(
        "/api/params/value",
        params={"node": "/talker", "name": "count"},
        json={"value": "7", "confirm": False},
    )
    assert response.status_code == 409


def test_routes_open_when_auth_disabled(client: TestClient) -> None:
    """Con auth disabilitata le route protette restano accessibili."""
    assert client.get("/api/nodes").status_code == 200
    status = client.get("/api/auth/status").json()
    assert status["enabled"] is False


def test_protected_route_requires_token(auth_client: TestClient) -> None:
    """Con auth abilitata una route protetta senza token deve dare 401."""
    assert auth_client.get("/api/nodes").status_code == 401


def test_login_then_access(auth_client: TestClient) -> None:
    """Login valido -> token -> accesso consentito alla route protetta."""
    bad = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert bad.status_code == 401

    ok = auth_client.post(
        "/api/auth/login", json={"username": "admin", "password": "pw"}
    )
    assert ok.status_code == 200
    token = ok.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/api/nodes", headers=headers).status_code == 200
