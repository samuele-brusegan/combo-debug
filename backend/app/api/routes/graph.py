"""Endpoint REST per il grafo ROS 2: topic, servizi e azioni con stato."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_graph_service
from app.models.schemas import GraphSnapshot
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphSnapshot, summary="Topic, servizi e azioni")
def get_graph(service: GraphService = Depends(get_graph_service)) -> GraphSnapshot:
    """Restituisce topic, servizi e azioni del grafo ROS 2 con il loro stato.

    Ogni entita' e' classificata VERDE (produttore attivo), GIALLA (solo
    consumatori, produttore mancante) o ZOMBIE (presente nel grafo ma senza
    alcun nodo attivo associato), per il color-coding dei pannelli dedicati.

    Args:
        service: Servizio di ispezione del grafo iniettato.

    Returns:
        Una fotografia del grafo con i tre elenchi e il rispettivo stato.
    """
    return service.get_snapshot()
