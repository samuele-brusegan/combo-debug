"""Test del servizio di ispezione del grafo (topic/servizi/azioni + zombie)."""

from __future__ import annotations

from app.adapters.ros_cli import CommandResult
from app.core.config import Settings
from app.models.schemas import EntityStatus
from app.services.graph_service import GraphService
from tests.fakes import FakeRosCommandRunner

_TALKER_INFO = """\
/talker
  Subscribers:

  Publishers:
    /chatter: std_msgs/msg/String
    /rosout: rcl_interfaces/msg/Log
  Service Servers:
    /add_two_ints: example_interfaces/srv/AddTwoInts
    /talker/get_parameters: rcl_interfaces/srv/GetParameters
  Service Clients:

  Action Servers:
    /fibonacci: example_interfaces/action/Fibonacci
  Action Clients:

"""

_LISTENER_INFO = """\
/listener
  Subscribers:
    /chatter: std_msgs/msg/String
    /orphan: std_msgs/msg/String
  Publishers:
    /rosout: rcl_interfaces/msg/Log
  Service Servers:

  Service Clients:
    /add_two_ints: example_interfaces/srv/AddTwoInts
  Action Servers:

  Action Clients:
    /fibonacci: example_interfaces/action/Fibonacci
"""


def _runner() -> FakeRosCommandRunner:
    """Crea un runner fake con un grafo di esempio (sani, in attesa, zombie)."""
    return FakeRosCommandRunner(
        {
            ("node", "list"): CommandResult(
                ["node", "list"], 0, "/talker\n/listener\n", ""
            ),
            ("node", "info", "/talker"): CommandResult(
                ["node", "info", "/talker"], 0, _TALKER_INFO, ""
            ),
            ("node", "info", "/listener"): CommandResult(
                ["node", "info", "/listener"], 0, _LISTENER_INFO, ""
            ),
            ("topic", "list"): CommandResult(
                ["topic", "list"],
                0,
                "/chatter\n/orphan\n/ghost_topic\n/rosout\n",
                "",
            ),
            ("service", "list"): CommandResult(
                ["service", "list"],
                0,
                "/add_two_ints\n/ghost_service\n/talker/get_parameters\n",
                "",
            ),
            ("action", "list"): CommandResult(
                ["action", "list"], 0, "/fibonacci\n/ghost_action\n", ""
            ),
        }
    )


def _snapshot() -> dict[str, dict[str, EntityStatus]]:
    """Restituisce lo snapshot indicizzato per tipo e nome -> stato."""
    service = GraphService(runner=_runner(), settings=Settings())
    snap = service.get_snapshot()
    return {
        "topics": {e.name: e.status for e in snap.topics},
        "services": {e.name: e.status for e in snap.services},
        "actions": {e.name: e.status for e in snap.actions},
    }


def test_topic_with_active_publisher_is_green() -> None:
    """Un topic con almeno un publisher attivo e' VERDE."""
    assert _snapshot()["topics"]["/chatter"] is EntityStatus.GREEN


def test_topic_with_only_subscriber_is_yellow() -> None:
    """Un topic con solo subscriber attivi (nessun publisher) e' GIALLO."""
    assert _snapshot()["topics"]["/orphan"] is EntityStatus.YELLOW


def test_topic_without_active_endpoints_is_zombie() -> None:
    """Un topic ancora elencato ma senza endpoint attivi e' ZOMBIE."""
    assert _snapshot()["topics"]["/ghost_topic"] is EntityStatus.ZOMBIE


def test_service_with_active_server_is_green() -> None:
    """Un servizio con server attivo e' VERDE."""
    assert _snapshot()["services"]["/add_two_ints"] is EntityStatus.GREEN


def test_zombie_service_detected() -> None:
    """Un servizio senza alcun nodo attivo associato e' ZOMBIE."""
    assert _snapshot()["services"]["/ghost_service"] is EntityStatus.ZOMBIE


def test_default_parameter_services_are_filtered() -> None:
    """I servizi parametro standard non compaiono nell'elenco."""
    assert "/talker/get_parameters" not in _snapshot()["services"]


def test_action_with_active_server_is_green() -> None:
    """Un'azione con server attivo e' VERDE."""
    assert _snapshot()["actions"]["/fibonacci"] is EntityStatus.GREEN


def test_zombie_action_detected() -> None:
    """Un'azione senza alcun nodo attivo associato e' ZOMBIE."""
    assert _snapshot()["actions"]["/ghost_action"] is EntityStatus.ZOMBIE


def test_entity_type_is_captured() -> None:
    """Il tipo dell'entita' viene estratto dall'output di node info."""
    service = GraphService(runner=_runner(), settings=Settings())
    chatter = next(e for e in service.get_snapshot().topics if e.name == "/chatter")
    assert chatter.entity_type == "std_msgs/msg/String"
    assert "talker" in chatter.producers
