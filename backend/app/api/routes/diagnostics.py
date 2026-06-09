"""Endpoint REST per lo stato diagnostico del sistema (``/diagnostics``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_diagnostics_monitor
from app.models.schemas import DiagnosticsSnapshot
from app.services.diagnostics_monitor import DiagnosticsMonitor

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("", response_model=DiagnosticsSnapshot, summary="Stato diagnostico")
def get_diagnostics(
    monitor: DiagnosticsMonitor = Depends(get_diagnostics_monitor),
) -> DiagnosticsSnapshot:
    """Restituisce l'ultimo stato diagnostico noto di ogni componente.

    I dati provengono dal monitor in background sottoscritto a ``/diagnostics``.
    Se ROS non e' disponibile o nessun messaggio e' ancora arrivato, l'esito ha
    ``available=False`` e un campo ``detail`` esplicativo.

    Args:
        monitor: Monitor diagnostico iniettato.

    Returns:
        La fotografia diagnostica corrente.
    """
    return monitor.snapshot()
