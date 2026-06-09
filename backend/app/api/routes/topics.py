"""Endpoint REST per l'echo on-demand dei topic ROS 2."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_topic_echo_service
from app.models.schemas import TopicEcho
from app.services.topic_echo_service import TopicEchoService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/echo", response_model=TopicEcho, summary="Echo di un singolo messaggio")
def echo_topic(
    topic: str = Query(description="Nome del topic (es. /chatter)."),
    service: TopicEchoService = Depends(get_topic_echo_service),
) -> TopicEcho:
    """Cattura e restituisce un singolo messaggio dal topic indicato.

    Args:
        topic: Nome del topic da ispezionare.
        service: Servizio di echo iniettato.

    Returns:
        Il messaggio catturato (YAML) o un esito che ne spiega l'assenza.
    """
    return service.echo(topic)
