"""Servizio di autenticazione della dashboard (token firmato, opt-in).

L'autenticazione e' **disabilitata di default** (vedi `Settings.auth_enabled`)
cosi' la demo resta senza attriti. Quando abilitata, il login verifica le
credenziali configurate e rilascia un token firmato a tempo (``itsdangerous``)
che il frontend invia nell'header ``Authorization: Bearer <token>``.

Non e' un sistema multi-utente: e' una protezione single-tenant adatta a una
dashboard di debug esposta in rete locale.
"""

from __future__ import annotations

import hmac

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import Settings

# Namespace ("salt") del serializer, per separare questi token da altri usi.
_TOKEN_SALT = "combo-debug-auth"


class AuthService:
    """Verifica le credenziali e gestisce i token firmati della dashboard."""

    def __init__(self, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            settings: Configurazione applicativa (credenziali e segreto).
        """
        self._settings = settings
        self._serializer = URLSafeTimedSerializer(
            settings.auth_secret, salt=_TOKEN_SALT
        )

    @property
    def enabled(self) -> bool:
        """bool: ``True`` se l'autenticazione e' abilitata via configurazione."""
        return self._settings.auth_enabled

    def verify_credentials(self, username: str, password: str) -> bool:
        """Verifica nome utente e password contro la configurazione.

        Usa confronti a tempo costante per non esporre differenze temporali.

        Args:
            username: Nome utente fornito.
            password: Password fornita.

        Returns:
            ``True`` se le credenziali combaciano con quelle configurate.
        """
        user_ok = hmac.compare_digest(username, self._settings.auth_username)
        pass_ok = hmac.compare_digest(password, self._settings.auth_password)
        return user_ok and pass_ok

    def issue_token(self, username: str) -> str:
        """Rilascia un token firmato a tempo per l'utente indicato.

        Args:
            username: Nome utente da incapsulare nel token.

        Returns:
            Il token firmato (URL-safe).
        """
        return self._serializer.dumps({"sub": username})

    def verify_token(self, token: str) -> bool:
        """Verifica firma e scadenza di un token.

        Args:
            token: Token ricevuto dal client.

        Returns:
            ``True`` se il token e' valido e non scaduto.
        """
        try:
            self._serializer.loads(token, max_age=self._settings.auth_token_ttl)
        except (BadSignature, SignatureExpired):
            return False
        return True
