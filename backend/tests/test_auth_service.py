"""Test del servizio di autenticazione."""

from __future__ import annotations

from app.core.config import Settings
from app.services.auth_service import AuthService


def _service(secret: str = "test-secret") -> AuthService:
    """Crea un AuthService con impostazioni di test."""
    settings = Settings(
        auth_enabled=True,
        auth_username="admin",
        auth_password="secret",
        auth_secret=secret,
    )
    return AuthService(settings=settings)


def test_disabled_by_default() -> None:
    """Di default l'autenticazione e' disabilitata."""
    assert AuthService(settings=Settings()).enabled is False


def test_verify_credentials() -> None:
    """Solo le credenziali corrette devono essere accettate."""
    service = _service()
    assert service.verify_credentials("admin", "secret") is True
    assert service.verify_credentials("admin", "wrong") is False
    assert service.verify_credentials("root", "secret") is False


def test_issue_and_verify_token() -> None:
    """Un token rilasciato deve risultare valido alla verifica."""
    service = _service()
    token = service.issue_token("admin")
    assert service.verify_token(token) is True


def test_reject_invalid_token() -> None:
    """Un token manomesso o firmato con altro segreto deve essere rifiutato."""
    service = _service()
    assert service.verify_token("non-un-token") is False
    other = _service(secret="altro-segreto")
    foreign_token = other.issue_token("admin")
    assert service.verify_token(foreign_token) is False
