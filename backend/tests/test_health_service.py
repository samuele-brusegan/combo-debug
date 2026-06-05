"""Test dell'euristica di salute (frequenza topic / spin bloccato)."""

from __future__ import annotations

from app.adapters.ros_cli import CommandResult
from app.core.config import Settings
from app.models.schemas import NodeStatus
from app.services.health_service import HealthService, TopicFrequencyCheck
from tests.fakes import FakeRosCommandRunner


def test_topic_above_threshold_is_healthy() -> None:
    """Un topic alla frequenza attesa produce uno stato GREEN."""
    settings = Settings(expected_topics="/chatter=0.5", expected_nodes="")
    runner = FakeRosCommandRunner(
        {
            ("topic", "hz", "/chatter"): CommandResult(
                ["topic", "hz", "/chatter"], 0, "average rate: 1.000\n", ""
            )
        }
    )
    service = HealthService([TopicFrequencyCheck(runner=runner, settings=settings)])
    report = service.build_report()
    assert report.status is NodeStatus.GREEN
    assert report.topics[0].measured_hz == 1.0


def test_absent_topic_is_skipped_without_measuring() -> None:
    """Un topic assente dal grafo viene marcato senza misurarlo (no timeout)."""
    settings = Settings(expected_topics="/chatter=0.5", expected_nodes="")
    # 'topic list' ha successo ma NON contiene /chatter: non deve essere misurato.
    runner = FakeRosCommandRunner(
        {
            ("topic", "list"): CommandResult(
                ["topic", "list"], 0, "/altro\n/rosout\n", ""
            ),
            # Se venisse misurato comunque, risulterebbe sano: il test fallirebbe.
            ("topic", "hz", "/chatter"): CommandResult(
                ["topic", "hz", "/chatter"], 0, "average rate: 5.0\n", ""
            ),
        }
    )
    service = HealthService([TopicFrequencyCheck(runner=runner, settings=settings)])
    report = service.build_report()
    assert report.status is NodeStatus.YELLOW
    assert report.topics[0].measured_hz is None
    assert "non presente" in report.topics[0].detail.lower()


def test_silent_topic_triggers_yellow() -> None:
    """Un topic senza messaggi (nessun 'average rate') produce stato YELLOW."""
    settings = Settings(expected_topics="/heartbeat=1.0", expected_nodes="")
    runner = FakeRosCommandRunner(
        {
            ("topic", "hz", "/heartbeat"): CommandResult(
                ["topic", "hz", "/heartbeat"], 124, "", "Timeout", timed_out=True
            )
        }
    )
    service = HealthService([TopicFrequencyCheck(runner=runner, settings=settings)])
    report = service.build_report()
    assert report.status is NodeStatus.YELLOW
    assert report.topics[0].measured_hz is None
    assert report.topics[0].healthy is False
