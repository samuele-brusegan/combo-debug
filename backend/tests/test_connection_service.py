"""Test del servizio di connessione: riavvio del monitor /rosout su cambio DDS."""

from __future__ import annotations

import os

from app.core.config import Settings
from app.models.schemas import ConnectionUpdate
from app.services.connection_service import ConnectionService
from app.services.rosout_monitor import RosoutMonitor
from tests.fakes import FakeRosCommandRunner


class _SpyRosout(RosoutMonitor):
    """RosoutMonitor che conta quante volte viene richiesto il restart."""

    def __init__(self) -> None:
        super().__init__()
        self.restart_calls = 0

    def restart(self) -> None:  # type: ignore[override]
        self.restart_calls += 1


def _service(rosout: RosoutMonitor) -> ConnectionService:
    """Crea un ConnectionService con runner fittizio e il monitor dato."""
    return ConnectionService(
        runner=FakeRosCommandRunner({}),
        settings=Settings(),
        rosout=rosout,
    )


def test_changing_domain_restarts_rosout() -> None:
    """Cambiare ROS_DOMAIN_ID deve riavviare la sottoscrizione /rosout."""
    os.environ["ROS_DOMAIN_ID"] = "0"
    spy = _SpyRosout()
    service = _service(spy)

    service.apply(ConnectionUpdate(ros_domain_id="42"))
    assert spy.restart_calls == 1


def test_changing_only_expected_nodes_does_not_restart() -> None:
    """Modificare solo i nodi attesi non deve riavviare /rosout (nessun cambio DDS)."""
    spy = _SpyRosout()
    service = _service(spy)

    service.apply(ConnectionUpdate(expected_nodes="/a,/b"))
    assert spy.restart_calls == 0
