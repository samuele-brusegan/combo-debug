"""Endpoint REST per le euristiche di salute / spin bloccato (requisito 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_health_service
from app.models.schemas import HealthReport
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthReport, summary="Report euristico di salute")
def get_health(
    service: HealthService = Depends(get_health_service),
) -> HealthReport:
    """Esegue le euristiche di salute e restituisce il report.

    Args:
        service: Servizio delle euristiche iniettato.

    Returns:
        Report con stato complessivo e dettaglio dei controlli sui topic.
    """
    return service.build_report()
