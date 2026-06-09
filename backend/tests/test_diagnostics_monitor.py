"""Test del monitor di diagnostica (senza ROS, via injection diretta)."""

from __future__ import annotations

from app.models.schemas import DiagnosticLevel, DiagnosticStatus, DiagnosticValue
from app.services.diagnostics_monitor import DiagnosticsMonitor


def test_snapshot_unavailable_when_inactive() -> None:
    """Senza messaggi e monitor inattivo, lo snapshot e' non disponibile."""
    monitor = DiagnosticsMonitor()
    snapshot = monitor.snapshot()
    assert snapshot.available is False
    assert snapshot.statuses == []


def test_update_status_is_reflected_in_snapshot() -> None:
    """Un'entrata inserita deve comparire nello snapshot, ordinata per nome."""
    monitor = DiagnosticsMonitor()
    monitor.update_status(
        DiagnosticStatus(
            name="motore",
            level=DiagnosticLevel.WARN,
            message="temperatura alta",
            values=[DiagnosticValue(key="temp", value="80")],
        )
    )
    monitor.update_status(DiagnosticStatus(name="batteria", level=DiagnosticLevel.OK))
    snapshot = monitor.snapshot()
    assert snapshot.available is True
    assert [s.name for s in snapshot.statuses] == ["batteria", "motore"]


def test_update_status_keeps_only_latest_per_component() -> None:
    """Aggiornamenti successivi sullo stesso componente sostituiscono il prec."""
    monitor = DiagnosticsMonitor()
    monitor.update_status(DiagnosticStatus(name="lidar", level=DiagnosticLevel.OK))
    monitor.update_status(DiagnosticStatus(name="lidar", level=DiagnosticLevel.ERROR))
    snapshot = monitor.snapshot()
    assert len(snapshot.statuses) == 1
    assert snapshot.statuses[0].level is DiagnosticLevel.ERROR
