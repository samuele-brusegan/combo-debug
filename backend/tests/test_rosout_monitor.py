"""Test del monitor /rosout e dell'integrazione con il LogService."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.models.schemas import LogEntry, LogLevel
from app.services.log_service import LogService
from app.services.rosout_monitor import RosoutMonitor


def _entry(level: LogLevel, message: str, source: str) -> LogEntry:
    """Crea una `LogEntry` di comodo per i test."""
    return LogEntry(level=level, message=message, source=source, line_number=0)


def test_get_logs_filters_by_node_and_level() -> None:
    """Il buffer filtra per nodo e per livello, dal piu' recente."""
    monitor = RosoutMonitor()
    monitor.add_entries(
        [
            _entry(LogLevel.INFO, "talker info", "talker"),
            _entry(LogLevel.ERROR, "talker boom", "talker"),
            _entry(LogLevel.WARN, "listener slow", "listener"),
        ]
    )

    only_talker = monitor.get_logs(node="/talker")
    assert {e.message for e in only_talker} == {"talker info", "talker boom"}
    # Il piu' recente inserito per il nodo deve venire prima.
    assert only_talker[0].message == "talker boom"

    errors = monitor.get_logs(levels={LogLevel.ERROR})
    assert [e.message for e in errors] == ["talker boom"]


def test_summary_counts_by_level() -> None:
    """Il riepilogo conteggia le righe per livello."""
    monitor = RosoutMonitor()
    monitor.add_entries(
        [
            _entry(LogLevel.ERROR, "x", "a"),
            _entry(LogLevel.ERROR, "y", "b"),
            _entry(LogLevel.INFO, "z", "a"),
        ]
    )
    assert monitor.summary() == {"error": 2, "info": 1}


def test_log_service_prefers_rosout_when_active(tmp_path: Path) -> None:
    """Con il monitor /rosout attivo, il LogService legge da li' e non dai file."""
    (tmp_path / "node.log").write_text("[ERROR] dai file locali\n")
    monitor = RosoutMonitor()
    monitor.add_entries([_entry(LogLevel.INFO, "dal rosout live", "talker")])

    service = LogService(settings=Settings(ros_log_dir=tmp_path), rosout=monitor)
    messages = [e.message for e in service.parse()]
    assert messages == ["dal rosout live"]


def test_log_service_falls_back_to_files_when_inactive(tmp_path: Path) -> None:
    """Senza monitor attivo, il LogService legge i file locali."""
    (tmp_path / "node.log").write_text("[ERROR] dai file locali\n")
    monitor = RosoutMonitor()  # non attivo: nessuna entry iniettata

    service = LogService(settings=Settings(ros_log_dir=tmp_path), rosout=monitor)
    messages = [e.message for e in service.parse()]
    assert messages == ["[ERROR] dai file locali"]
