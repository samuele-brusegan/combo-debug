"""Endpoint REST per le euristiche di salute / spin bloccato (requisito 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_health_monitor
from app.models.schemas import HealthReport
from app.services.health_monitor import HealthMonitor

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthReport, summary="Report euristico di salute")
def get_health(
    monitor: HealthMonitor = Depends(get_health_monitor),
) -> HealthReport:
    """Restituisce l'ultimo report di salute calcolato in background.

    La misura della frequenza dei topic (``ros2 topic hz``) e' lenta e viene
    eseguita da un thread dedicato che ne mantiene il risultato in cache: questo
    endpoint la legge in modo immediato, senza bloccare il threadpool del
    server (evitando che il polling del frontend renda irraggiungibile il
    backend).

    Args:
        monitor: Monitor di salute iniettato.

    Returns:
        L'ultimo report con stato complessivo e dettaglio dei controlli.
    """
    return monitor.get_report()
