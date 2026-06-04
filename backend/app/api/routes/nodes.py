"""Endpoint REST per i nodi ROS 2 e il loro stato (requisito 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_node_service
from app.models.schemas import RosNode
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=list[RosNode], summary="Elenco nodi con stato")
def list_nodes(service: NodeService = Depends(get_node_service)) -> list[RosNode]:
    """Restituisce l'elenco dei nodi ROS 2 con indicatore di stato.

    Args:
        service: Servizio dei nodi iniettato.

    Returns:
        Lista di nodi con stato VERDE/ROSSO per il color-coding della dashboard.
    """
    return service.get_nodes()
