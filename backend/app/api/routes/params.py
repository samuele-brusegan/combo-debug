"""Endpoint REST per l'ispezione e la modifica dei parametri dei nodi ROS 2.

Il nome del nodo e del parametro sono passati come query string (non nel path):
i nomi ROS possono contenere ``/`` (namespace) e renderebbero ambiguo il routing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_param_service
from app.models.schemas import NodeParams, ParamSetRequest, ParamSetResult, ParamValue
from app.services.param_service import ParamService, ParamWriteNotConfirmedError

router = APIRouter(prefix="/params", tags=["params"])


@router.get("", response_model=NodeParams, summary="Parametri di un nodo")
def list_params(
    node: str = Query(description="Nome del nodo (es. /talker)."),
    service: ParamService = Depends(get_param_service),
) -> NodeParams:
    """Elenca i parametri dichiarati da un nodo.

    Args:
        node: Nome del nodo (es. ``/talker``).
        service: Servizio dei parametri iniettato.

    Returns:
        I nomi dei parametri del nodo e l'esito dell'interrogazione.
    """
    return service.list_params(_normalize_node(node))


@router.get("/value", response_model=ParamValue, summary="Valore di un parametro")
def get_param(
    node: str = Query(description="Nome del nodo (es. /talker)."),
    name: str = Query(description="Nome del parametro."),
    service: ParamService = Depends(get_param_service),
) -> ParamValue:
    """Restituisce il valore corrente di un parametro di un nodo.

    Args:
        node: Nome del nodo (es. ``/talker``).
        name: Nome del parametro.
        service: Servizio dei parametri iniettato.

    Returns:
        Il valore del parametro e l'esito della lettura.
    """
    return service.get_param(_normalize_node(node), name)


@router.post(
    "/value",
    response_model=ParamSetResult,
    summary="Modifica parametro (richiede conferma)",
)
def set_param(
    request: ParamSetRequest,
    node: str = Query(description="Nome del nodo (es. /talker)."),
    name: str = Query(description="Nome del parametro."),
    service: ParamService = Depends(get_param_service),
) -> ParamSetResult:
    """Modifica un parametro di un nodo, previa conferma esplicita.

    La scrittura puo' alterare lo stato di un robot in esecuzione: il campo
    ``confirm`` del corpo deve essere ``True``, altrimenti la richiesta viene
    rifiutata con HTTP 409 e nessuna modifica viene applicata.

    Args:
        request: Corpo con il nuovo valore e la conferma di sicurezza.
        node: Nome del nodo (es. ``/talker``).
        name: Nome del parametro da modificare.
        service: Servizio dei parametri iniettato.

    Returns:
        L'esito della scrittura.

    Raises:
        HTTPException: 409 se la modifica non e' stata confermata.
    """
    try:
        return service.set_param(
            _normalize_node(node), name, request.value, request.confirm
        )
    except ParamWriteNotConfirmedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


def _normalize_node(node: str) -> str:
    """Garantisce che il nome del nodo inizi con uno slash.

    Args:
        node: Nome del nodo dalla query string.

    Returns:
        Il nome del nodo con lo slash iniziale garantito.
    """
    return node if node.startswith("/") else f"/{node}"
