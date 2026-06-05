"""Test del servizio di connessione: riavvio del monitor /rosout su cambio DDS."""

from __future__ import annotations

import os

from app.adapters.ros_cli import CommandResult
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


def _pkg_list(*packages: str) -> dict:
    """Programma il fake per ``ros2 pkg list`` con i pacchetti indicati."""
    return {
        ("pkg", "list"): CommandResult(
            ["pkg", "list"], 0, "\n".join(packages) + "\n", ""
        )
    }


def test_available_rmw_detects_installed_from_catalog() -> None:
    """Vengono offerte solo le RMW del catalogo effettivamente installate."""
    os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
    runner = FakeRosCommandRunner(
        _pkg_list("std_msgs", "rmw_fastrtps_cpp", "rmw_cyclonedds_cpp", "rclpy")
    )
    service = ConnectionService(runner=runner, settings=Settings())

    options = service.available_rmw()
    assert options.available == ["rmw_cyclonedds_cpp", "rmw_fastrtps_cpp"]
    assert options.current == "rmw_fastrtps_cpp"


def test_available_rmw_includes_current_even_if_custom() -> None:
    """La RMW corrente personalizzata e' sempre inclusa tra le opzioni."""
    os.environ["RMW_IMPLEMENTATION"] = "rmw_personalizzata_cpp"
    runner = FakeRosCommandRunner(_pkg_list("rmw_fastrtps_cpp"))
    service = ConnectionService(runner=runner, settings=Settings())

    options = service.available_rmw()
    assert "rmw_personalizzata_cpp" in options.available
    assert "rmw_fastrtps_cpp" in options.available


def test_available_rmw_falls_back_when_pkg_list_unavailable() -> None:
    """Se ``ros2 pkg list`` non e' disponibile si usa l'elenco di fallback."""
    os.environ.pop("RMW_IMPLEMENTATION", None)
    runner = FakeRosCommandRunner({})  # nessuna risposta -> comando fallisce
    service = ConnectionService(runner=runner, settings=Settings())

    options = service.available_rmw()
    assert options.available == ["rmw_cyclonedds_cpp", "rmw_fastrtps_cpp"]
