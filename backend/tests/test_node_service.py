"""Test del servizio dei nodi e del relativo color-coding."""

from __future__ import annotations

from app.adapters.ros_cli import CommandResult
from app.core.config import Settings
from app.models.schemas import NodeStatus
from app.services.node_service import NodeService
from tests.fakes import FakeRosCommandRunner


def _settings() -> Settings:
    """Crea impostazioni di test con un set fisso di nodi attesi."""
    return Settings(expected_nodes="/talker,/crasher", expected_topics="")


def test_active_node_is_green_when_responsive() -> None:
    """Un nodo presente e responsivo deve risultare VERDE."""
    runner = FakeRosCommandRunner(
        {
            ("node", "list"): CommandResult(["node", "list"], 0, "/talker\n", ""),
            ("node", "info", "/talker"): CommandResult(
                ["node", "info", "/talker"], 0, "ok", ""
            ),
        }
    )
    service = NodeService(runner=runner, settings=_settings())
    nodes = {node.name: node for node in service.get_nodes()}
    assert nodes["/talker"].status is NodeStatus.GREEN


def test_expected_but_absent_node_is_red() -> None:
    """Un nodo atteso ma assente dal grafo deve risultare ROSSO."""
    runner = FakeRosCommandRunner(
        {("node", "list"): CommandResult(["node", "list"], 0, "/talker\n", "")}
    )
    service = NodeService(runner=runner, settings=_settings())
    nodes = {node.name: node for node in service.get_nodes()}
    assert nodes["/crasher"].status is NodeStatus.RED


def test_unresponsive_node_is_red() -> None:
    """Un nodo presente ma non interrogabile deve risultare ROSSO."""
    runner = FakeRosCommandRunner(
        {
            ("node", "list"): CommandResult(["node", "list"], 0, "/talker\n", ""),
            ("node", "info", "/talker"): CommandResult(
                ["node", "info", "/talker"], 1, "", "timeout"
            ),
        }
    )
    service = NodeService(runner=runner, settings=_settings())
    nodes = {node.name: node for node in service.get_nodes()}
    assert nodes["/talker"].status is NodeStatus.RED
