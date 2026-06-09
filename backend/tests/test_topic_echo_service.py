"""Test del servizio di echo on-demand dei topic."""

from __future__ import annotations

from app.adapters.ros_cli import CommandResult
from app.core.config import Settings
from app.services.topic_echo_service import TopicEchoService
from tests.fakes import FakeRosCommandRunner


def _service(result: CommandResult) -> TopicEchoService:
    """Crea un TopicEchoService il cui runner restituisce sempre `result`."""
    responses = {("topic", "echo"): result}
    return TopicEchoService(runner=FakeRosCommandRunner(responses), settings=Settings())


def test_echo_returns_message() -> None:
    """Un messaggio catturato deve risultare available=True."""
    service = _service(CommandResult(["topic", "echo"], 0, "data: 'ciao'\n---\n", ""))
    echo = service.echo("/chatter")
    assert echo.available is True
    assert "ciao" in echo.message


def test_echo_timeout_reports_silent_topic() -> None:
    """Un timeout senza output deve segnalare un topic silente."""
    service = _service(
        CommandResult(["topic", "echo"], 124, "", "Timeout", timed_out=True)
    )
    echo = service.echo("/silent")
    assert echo.available is False
    assert echo.message == ""
    assert "timeout" in echo.detail.lower()
