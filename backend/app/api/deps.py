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
from app.services.health_service import (
    HealthService,
    TopicFrequencyCheck,
)
from app.services.log_service import LogService
from app.services.node_service import NodeService


@lru_cache
def get_runner() -> RosCommandRunner:
    """Restituisce il runner ROS 2 condiviso.

    Returns:
        Un'istanza singleton di `SubprocessRosCommandRunner` configurata col
        timeout di default delle impostazioni.
    """
    settings = get_settings()
    return SubprocessRosCommandRunner(default_timeout=settings.ros_command_timeout)


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
        Un `LogService` configurato con le impostazioni correnti.
    """
    return LogService(settings=get_settings())


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
        Un `ConnectionService` pronto all'uso.
    """
    return ConnectionService(runner=get_runner(), settings=get_settings())
