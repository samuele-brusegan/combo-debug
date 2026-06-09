"""Endpoint REST per l'autenticazione della dashboard (login/stato).

L'autenticazione e' opt-in (vedi `Settings.auth_enabled`). Questi endpoint sono
pubblici (non protetti da `require_auth`): servono proprio ad ottenere un token
o a sapere se l'auth e' richiesta.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_auth_service
from app.models.schemas import AuthStatus, LoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse, summary="Login e rilascio token")
def login(
    credentials: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Verifica le credenziali e rilascia un token bearer firmato.

    Args:
        credentials: Nome utente e password da verificare.
        auth: Servizio di autenticazione iniettato.

    Returns:
        Il token da usare nelle richieste successive.

    Raises:
        HTTPException: 403 se l'auth e' disabilitata; 401 se le credenziali
            non sono valide.
    """
    if not auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autenticazione disabilitata sul backend.",
        )
    if not auth.verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )
    return LoginResponse(token=auth.issue_token(credentials.username))


@router.get("/status", response_model=AuthStatus, summary="Stato autenticazione")
def auth_status(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> AuthStatus:
    """Indica se l'auth e' abilitata e se la richiesta corrente e' autenticata.

    Usato dal frontend all'avvio per decidere se mostrare la schermata di login.

    Args:
        credentials: Credenziali Bearer estratte dall'header (se presenti).
        auth: Servizio di autenticazione iniettato.

    Returns:
        Lo stato dell'autenticazione.
    """
    if not auth.enabled:
        return AuthStatus(enabled=False, authenticated=True)
    token = credentials.credentials if credentials else ""
    authenticated = bool(token) and auth.verify_token(token)
    return AuthStatus(enabled=True, authenticated=authenticated)
