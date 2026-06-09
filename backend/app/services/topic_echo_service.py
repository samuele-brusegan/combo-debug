"""Servizio di streaming on-demand dei messaggi di un topic ROS 2.

Mantiene una sottoscrizione continua a un topic (``ros2 topic echo``) e ne
trasmette i messaggi in tempo reale verso la dashboard come eventi SSE
(Server-Sent Events). Dipende dall'astrazione `RosCommandRunner`, quindi la
logica di raggruppamento/formattazione e' testabile senza un'installazione ROS
reale.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings

# ``ros2 topic echo`` separa i messaggi consecutivi con una riga ``---``.
ECHO_SEPARATOR = "---"


def format_sse(data: str, event: str | None = None) -> str:
    """Formatta un payload come evento SSE (Server-Sent Events).

    Ogni riga del payload viene prefissata con ``data: `` (come richiesto dal
    protocollo per i contenuti multiriga) e l'evento e' chiuso da una riga
    vuota.

    Args:
        data: Contenuto da inviare (puo' essere multiriga).
        event: Nome opzionale dell'evento (es. ``message``, ``info``, ``end``).

    Returns:
        La stringa pronta da scrivere sullo stream ``text/event-stream``.
    """
    chunk = f"event: {event}\n" if event else ""
    for line in data.split("\n"):
        chunk += f"data: {line}\n"
    return chunk + "\n"


class TopicEchoService:
    """Trasmette in streaming i messaggi pubblicati su un topic, on-demand."""

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per eseguire i comandi ros2.
            settings: Configurazione applicativa.
        """
        self._runner = runner
        self._settings = settings

    async def stream(self, topic: str) -> AsyncIterator[str]:
        """Sottoscrive il topic e produce i messaggi come eventi SSE.

        Avvia ``ros2 topic echo --full-length <topic>`` (senza ``--once``,
        quindi resta in ascolto) e converte ogni messaggio catturato in un
        evento SSE ``message``. La sottoscrizione termina quando il consumatore
        chiude lo stream (disconnessione del client): l'iteratore del runner
        viene chiuso e il processo ``ros2`` interrotto.

        Args:
            topic: Nome del topic da ascoltare (es. ``/chatter``).

        Yields:
            Eventi SSE gia' formattati: un ``info`` iniziale, un ``message`` per
            ogni messaggio catturato e un ``end`` finale.
        """
        yield format_sse(f"In ascolto su {topic} — in attesa di messaggi…", "info")

        lines = self._runner.stream_lines(
            ["topic", "echo", "--full-length", topic]
        )
        buffer: list[str] = []
        received = False
        try:
            async for line in lines:
                if line.strip() == ECHO_SEPARATOR:
                    if buffer:
                        yield format_sse("\n".join(buffer), "message")
                        buffer = []
                        received = True
                    continue
                buffer.append(line)
            if buffer:
                yield format_sse("\n".join(buffer), "message")
                received = True
        finally:
            await lines.aclose()

        detail = (
            "Stream terminato."
            if received
            else "Stream terminato senza messaggi: topic silente o inesistente."
        )
        yield format_sse(detail, "end")
