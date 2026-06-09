"""Endpoint REST per la configurazione runtime della connessione ROS 2.

Consente di ricollegare il backend a un grafo ROS reale a caldo, senza
riavviare il container (vedi `ConnectionService`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_connection_service
from app.models.schemas import (
    ConnectionConfig,
    ConnectionDiscovery,
    ConnectionProbe,
    ConnectionUpdate,
    RmwOptions,
)
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connection", tags=["connection"])


@router.get(
    "",
    response_model=ConnectionConfig,
    summary="Configurazione di connessione attuale",
)
def get_connection(
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionConfig:
    """Restituisce i parametri di connessione ROS 2 attualmente attivi.

    Args:
        service: Servizio di connessione iniettato.

    Returns:
        La configurazione di connessione corrente.
    """
    return service.get_config()


@router.put(
    "",
    response_model=ConnectionConfig,
    summary="Applica la connessione a caldo",
)
def update_connection(
    update: ConnectionUpdate,
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionConfig:
    """Applica a caldo i nuovi parametri di connessione (nessun riavvio).

    Args:
        update: Aggiornamento parziale dei parametri di connessione.
        service: Servizio di connessione iniettato.

    Returns:
        La configurazione risultante dopo l'applicazione.
    """
    return service.apply(update)


@router.post("/test", response_model=ConnectionProbe, summary="Verifica la connessione")
def test_connection(
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionProbe:
    """Verifica la connessione interrogando il grafo con la config corrente.

    Args:
        service: Servizio di connessione iniettato.

    Returns:
        L'esito con la disponibilita' della CLI e i nodi rilevati.
    """
    return service.test()


@router.get(
    "/rmw",
    response_model=RmwOptions,
    summary="Implementazioni RMW disponibili",
)
def list_rmw(
    service: ConnectionService = Depends(get_connection_service),
) -> RmwOptions:
    """Elenca le implementazioni RMW installate e quella attiva.

    Args:
        service: Servizio di connessione iniettato.

    Returns:
        Le RMW selezionabili dalla UI e quella corrente.
    """
    return service.available_rmw()


@router.get(
    "/discover",
    response_model=ConnectionDiscovery,
    summary="Rileva nodi e topic dal grafo",
)
def discover_graph(
    service: ConnectionService = Depends(get_connection_service),
) -> ConnectionDiscovery:
    """Rileva i nodi e i topic presenti nel grafo con la config corrente.

    Args:
        service: Servizio di connessione iniettato.

    Returns:
        I nodi e i topic rilevati, da usare per popolare i valori attesi.
    """
    return service.discover()
