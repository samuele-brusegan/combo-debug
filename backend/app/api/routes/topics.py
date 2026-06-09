"""Endpoint REST per lo streaming dei messaggi dei topic ROS 2."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_topic_echo_service
from app.services.topic_echo_service import TopicEchoService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/echo/stream", summary="Stream SSE dei messaggi di un topic")
async def echo_topic_stream(
    topic: str = Query(description="Nome del topic (es. /chatter)."),
    service: TopicEchoService = Depends(get_topic_echo_service),
) -> StreamingResponse:
    """Sottoscrive un topic e ne trasmette i messaggi come stream SSE.

    A differenza di una semplice GET, la risposta resta aperta: ogni messaggio
    pubblicato sul topic viene inviato come evento ``message`` (Server-Sent
    Events) finche' il client non chiude la connessione (chiusura del modal).

    Args:
        topic: Nome del topic da ascoltare.
        service: Servizio di echo iniettato.

    Returns:
        Una `StreamingResponse` ``text/event-stream`` con i messaggi del topic.
    """
    return StreamingResponse(
        service.stream(topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disattiva il buffering di nginx anche senza config dedicata: lo
            # stream deve arrivare al browser riga per riga, non a blocchi.
            "X-Accel-Buffering": "no",
        },
    )
