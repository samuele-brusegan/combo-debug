"""Endpoint REST per le variabili d'ambiente ROS (requisito 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_env_service
from app.models.schemas import EnvVariable
from app.services.env_service import EnvService

router = APIRouter(prefix="/env", tags=["environment"])


@router.get("", response_model=list[EnvVariable], summary="Variabili d'ambiente ROS")
def list_env(service: EnvService = Depends(get_env_service)) -> list[EnvVariable]:
    """Restituisce le variabili d'ambiente pertinenti a ROS 2.

    Args:
        service: Servizio delle variabili d'ambiente iniettato.

    Returns:
        Lista ordinata di coppie chiave/valore (es. ``ROS_DOMAIN_ID``).
    """
    return service.get_ros_variables()
