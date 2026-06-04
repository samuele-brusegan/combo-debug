"""Test del log parser (classificazione e filtri)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.models.schemas import LogLevel
from app.services.log_service import LogService


def _service(tmp_path: Path) -> LogService:
    """Crea un LogService che legge dalla cartella temporanea data."""
    return LogService(settings=Settings(ros_log_dir=tmp_path))


def test_classify_levels() -> None:
    """La classificazione riconosce i livelli principali."""
    service = LogService(settings=Settings())
    assert service.classify("[ERROR] qualcosa") is LogLevel.ERROR
    assert service.classify("operazione WARNING") is LogLevel.WARN
    assert service.classify("tutto ok") is LogLevel.INFO


def test_parse_filters_by_level(tmp_path: Path) -> None:
    """Il filtro per livello restituisce solo le righe richieste."""
    log_file = tmp_path / "node.log"
    log_file.write_text("info riga\n[ERROR] boom\nwarning attenzione\n")
    service = _service(tmp_path)

    only_errors = service.parse(levels={LogLevel.ERROR})
    assert len(only_errors) == 1
    assert only_errors[0].level is LogLevel.ERROR
    assert only_errors[0].source == "node.log"


def test_summary_counts(tmp_path: Path) -> None:
    """Il riepilogo conteggia correttamente le righe per livello."""
    (tmp_path / "a.log").write_text("[ERROR] x\nwarning y\ninfo z\n")
    service = _service(tmp_path)
    summary = service.summary()
    assert summary["error"] == 1
    assert summary["warn"] == 1
