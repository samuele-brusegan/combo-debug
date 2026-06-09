"""Provider di dependency injection per i router FastAPI.

Centralizza la costruzione dei service e delle loro dipendenze (Composition
Root). I router dichiarano cosa serve loro tramite ``Depends(...)`` senza
conoscere come gli oggetti vengono costruiti, rispettando l'inversione delle
dipendenze.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.ros_cli import RosCommandRunner, SubprocessRosCommandRunner
from app.core.config import get_settings
from app.services.auth_service import AuthService
from app.services.connection_service import ConnectionService
from app.services.diagnostics_monitor import DiagnosticsMonitor
from app.services.env_service import EnvService
from app.services.graph_service import GraphService
from app.services.log_service import LogService
from app.services.node_service import NodeService
from app.services.param_service import ParamService
from app.services.rosout_monitor import RosoutMonitor
from app.services.tf_monitor import TfMonitor
from app.services.topic_echo_service import TopicEchoService


@lru_cache
def get_runner() -> RosCommandRunner:
    """Restituisce il runner ROS 2 condiviso.

    Returns:
        Un'istanza singleton di `SubprocessRosCommandRunner` configurata col
        timeout di default delle impostazioni.
    """
    settings = get_settings()
    return SubprocessRosCommandRunner(
        executable=settings.ros_executable,
        default_timeout=settings.ros_command_timeout,
    )


@lru_cache
def get_rosout_monitor() -> RosoutMonitor:
    """Restituisce il monitor singleton del topic ``/rosout``.

    Returns:
        Un `RosoutMonitor` condiviso. Va avviato dal lifespan dell'app.
    """
    return RosoutMonitor()


@lru_cache
def get_diagnostics_monitor() -> DiagnosticsMonitor:
    """Restituisce il monitor singleton del topic ``/diagnostics``.

    Returns:
        Un `DiagnosticsMonitor` condiviso. Va avviato dal lifespan dell'app.
    """
    return DiagnosticsMonitor()


@lru_cache
def get_tf_monitor() -> TfMonitor:
    """Restituisce il monitor singleton dei topic TF (``/tf``, ``/tf_static``).

    Returns:
        Un `TfMonitor` condiviso. Va avviato dal lifespan dell'app.
    """
    return TfMonitor()


@lru_cache
def get_auth_service() -> AuthService:
    """Restituisce il servizio di autenticazione singleton.

    Returns:
        Un `AuthService` configurato con le impostazioni correnti.
    """
    return AuthService(settings=get_settings())


def get_node_service() -> NodeService:
    """Costruisce il servizio dei nodi.

    Returns:
        Un `NodeService` pronto all'uso.
    """
    return NodeService(runner=get_runner(), settings=get_settings())


def get_graph_service() -> GraphService:
    """Costruisce il servizio di ispezione del grafo (topic/servizi/azioni).

    Returns:
        Un `GraphService` configurato con runner e impostazioni correnti.
    """
    return GraphService(runner=get_runner(), settings=get_settings())


def get_param_service() -> ParamService:
    """Costruisce il servizio di ispezione/modifica dei parametri.

    Returns:
        Un `ParamService` configurato con runner e impostazioni correnti.
    """
    return ParamService(runner=get_runner(), settings=get_settings())


def get_topic_echo_service() -> TopicEchoService:
    """Costruisce il servizio di echo on-demand dei topic.

    Returns:
        Un `TopicEchoService` configurato con runner e impostazioni correnti.
    """
    return TopicEchoService(runner=get_runner(), settings=get_settings())


def get_env_service() -> EnvService:
    """Costruisce il servizio delle variabili d'ambiente.

    Returns:
        Un `EnvService` che legge l'ambiente del processo.
    """
    return EnvService()


def get_log_service() -> LogService:
    """Costruisce il servizio di parsing dei log.

    Returns:
        Un `LogService` configurato con le impostazioni correnti e collegato al
        monitor ``/rosout`` (usato quando attivo, altrimenti fallback su file).
    """
    return LogService(settings=get_settings(), rosout=get_rosout_monitor())


@lru_cache
def get_connection_service() -> ConnectionService:
    """Costruisce il servizio di connessione runtime al grafo ROS 2.

    Singleton (``lru_cache``) cosi' che condivida lo stesso `Settings` e runner
    degli altri service: le riconfigurazioni a caldo si riflettono ovunque.

    Returns:
        Un `ConnectionService` pronto all'uso. Riceve il monitor ``/rosout`` per
        riavviarlo quando cambia il dominio DDS (cosi' la sottoscrizione segue
        il nuovo grafo ROS).
    """
    return ConnectionService(
        runner=get_runner(),
        settings=get_settings(),
        rosout=get_rosout_monitor(),
        extra_monitors=[get_diagnostics_monitor(), get_tf_monitor()],
    )


# Schema di sicurezza HTTP Bearer. ``auto_error=False`` perche' la gestione del
# "manca il token" la facciamo noi (per consentire l'accesso quando l'auth e'
# disabilitata da configurazione).
_bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> None:
    """Protegge un endpoint richiedendo un token valido, se l'auth e' attiva.

    Quando l'autenticazione e' disabilitata da configurazione la dependency e'
    un no-op (la demo resta accessibile senza login). Quando e' abilitata,
    richiede un header ``Authorization: Bearer <token>`` con token valido.

    Args:
        credentials: Credenziali Bearer estratte dall'header (se presenti).
        auth: Servizio di autenticazione iniettato.

    Raises:
        HTTPException: 401 se l'auth e' abilitata e il token manca o non e' valido.
    """
    if not auth.enabled:
        return
    token = credentials.credentials if credentials else ""
    if not token or not auth.verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta o token non valido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
