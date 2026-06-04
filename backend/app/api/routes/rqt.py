"""Endpoint REST per il bridge verso i tool grafici rqt (requisito 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_rqt_service
from app.models.schemas import CommandSuggestion
from app.services.rqt_service import RqtService

router = APIRouter(prefix="/rqt", tags=["rqt"])


class LaunchRequest(BaseModel):
    """Richiesta di avvio di un comando rqt.

    Attributes:
        command: Comando shell da avviare (tra quelli suggeriti dal backend).
    """

    command: str


class LaunchResponse(BaseModel):
    """Esito dell'avvio di un comando rqt.

    Attributes:
        pid: PID del processo avviato.
    """

    pid: int


@router.get(
    "/tools",
    response_model=list[CommandSuggestion],
    summary="Comandi rqt suggeriti",
)
def list_tools(
    service: RqtService = Depends(get_rqt_service),
) -> list[CommandSuggestion]:
    """Restituisce i comandi diagnostici rqt disponibili.

    Args:
        service: Servizio bridge rqt iniettato.

    Returns:
        Lista di comandi suggeriti da mostrare nell'interfaccia.
    """
    return service.get_suggestions()


@router.post("/launch", response_model=LaunchResponse, summary="Avvia un tool rqt")
def launch_tool(
    payload: LaunchRequest,
    service: RqtService = Depends(get_rqt_service),
) -> LaunchResponse:
    """Tenta di avviare un tool grafico rqt (richiede DISPLAY).

    Args:
        payload: Richiesta contenente il comando da avviare.
        service: Servizio bridge rqt iniettato.

    Returns:
        L'esito con il PID del processo avviato.

    Raises:
        HTTPException: 400 se l'ambiente non dispone di un DISPLAY grafico.
    """
    allowed = {item.command for item in service.get_suggestions()}
    if payload.command not in allowed:
        raise HTTPException(status_code=400, detail="Comando rqt non consentito.")
    try:
        pid = service.launch(payload.command)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LaunchResponse(pid=pid)
