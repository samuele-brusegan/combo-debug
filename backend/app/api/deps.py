"""Provider di dependency injection per i router FastAPI.

Centralizza la costruzione dei service e delle loro dipendenze (Composition
Root). I router dichiarano cosa serve loro tramite ``Depends(...)`` senza
conoscere come gli oggetti vengono costruiti, rispettando l'inversione delle
dipendenze.
"""

from __future__ import annotations

from functools import lru_cache

from app.adapters.ros_cli import RosCommandRunner, SubprocessRosCommandRunner
from app.core.config import Settings, get_settings
from app.services.connection_service import ConnectionService
from app.services.env_service import EnvService
from app.services.health_monitor import HealthMonitor
from app.services.health_service import (
    HealthService,
    TopicFrequencyCheck,
)
from app.services.log_service import LogService
from app.services.node_service import NodeService
from app.services.rosout_monitor import RosoutMonitor


@lru_cache
def get_runner() -> RosCommandRunner:
    """Restituisce il runner ROS 2 condiviso.

    Returns:
        Un'istanza singleton di `SubprocessRosCommandRunner` configurata col
        timeout di default delle impostazioni.
    """
    settings = get_settings()
    return SubprocessRosCommandRunner(default_timeout=settings.ros_command_timeout)


@lru_cache
def get_rosout_monitor() -> RosoutMonitor:
    """Restituisce il monitor singleton del topic ``/rosout``.

    Returns:
        Un `RosoutMonitor` condiviso. Va avviato dal lifespan dell'app.
    """
    return RosoutMonitor()


@lru_cache
def get_health_monitor() -> HealthMonitor:
    """Restituisce il monitor singleton delle euristiche di salute.

    Il factory rilegge le impostazioni correnti ad ogni ciclo, cosi' da seguire
    le riconfigurazioni a caldo (nodi/topic attesi).

    Returns:
        Un `HealthMonitor` condiviso. Va avviato dal lifespan dell'app.
    """
    return HealthMonitor(service_factory=get_health_service)


def get_node_service() -> NodeService:
    """Costruisce il servizio dei nodi.

    Returns:
        Un `NodeService` pronto all'uso.
    """
    return NodeService(runner=get_runner(), settings=get_settings())


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


def get_health_service() -> HealthService:
    """Costruisce il servizio delle euristiche di salute.

    Returns:
        Un `HealthService` con le strategie di verifica registrate.
    """
    settings: Settings = get_settings()
    checks = [TopicFrequencyCheck(runner=get_runner(), settings=settings)]
    return HealthService(checks=checks)


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
    )
