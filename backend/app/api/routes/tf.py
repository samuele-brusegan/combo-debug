"""Endpoint REST per l'albero delle trasformate TF (``/tf``, ``/tf_static``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_tf_monitor
from app.models.schemas import TfTree
from app.services.tf_monitor import TfMonitor

router = APIRouter(prefix="/tf", tags=["tf"])


@router.get("", response_model=TfTree, summary="Albero delle trasformate TF")
def get_tf(monitor: TfMonitor = Depends(get_tf_monitor)) -> TfTree:
    """Restituisce l'albero TF corrente con le relazioni tra i frame.

    I dati provengono dal monitor in background sottoscritto a ``/tf`` e
    ``/tf_static``. Piu' di una radice indica alberi TF scollegati tra loro.

    Args:
        monitor: Monitor TF iniettato.

    Returns:
        L'albero dei frame con genitori e radici.
    """
    return monitor.get_tree()
