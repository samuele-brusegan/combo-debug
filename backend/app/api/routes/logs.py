"""Endpoint REST per il log parser centralizzato (requisito 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_log_service
from app.models.schemas import LogEntry, LogLevel
from app.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[LogEntry], summary="Righe di log classificate")
def get_logs(
    service: LogService = Depends(get_log_service),
    level: list[LogLevel] | None = Query(
        default=None,
        description="Filtra per uno o piu' livelli (es. ?level=error&level=warn).",
    ),
    max_entries: int = Query(default=500, ge=1, le=10_000),
) -> list[LogEntry]:
    """Restituisce le righe di log dei nodi ROS, classificate per severita'.

    Args:
        service: Servizio di parsing dei log iniettato.
        level: Livelli da includere; se assente vengono restituiti tutti.
        max_entries: Numero massimo di righe restituite.

    Returns:
        Lista di righe di log, dalla piu' recente alla piu' vecchia.
    """
    levels = set(level) if level else None
    return service.parse(levels=levels, max_entries=max_entries)


@router.get("/summary", response_model=dict[str, int], summary="Conteggi per livello")
def get_logs_summary(
    service: LogService = Depends(get_log_service),
) -> dict[str, int]:
    """Restituisce il conteggio delle righe di log per livello.

    Args:
        service: Servizio di parsing dei log iniettato.

    Returns:
        Mappa livello -> numero di righe (per i badge di sintesi del frontend).
    """
    return service.summary()
