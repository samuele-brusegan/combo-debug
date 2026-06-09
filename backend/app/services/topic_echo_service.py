"""Servizio di echo on-demand di un topic ROS 2.

Cattura un singolo messaggio da un topic (``ros2 topic echo --once``) per
ispezionarne il contenuto dalla dashboard. Dipende dall'astrazione
`RosCommandRunner`, quindi e' testabile senza un'installazione ROS reale.
"""

from __future__ import annotations

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import TopicEcho


class TopicEchoService:
    """Recupera l'ultimo messaggio pubblicato su un topic, on-demand."""

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per eseguire i comandi ros2.
            settings: Configurazione applicativa.
        """
        self._runner = runner
        self._settings = settings

    def echo(self, topic: str) -> TopicEcho:
        """Cattura un singolo messaggio dal topic indicato.

        Usa ``ros2 topic echo <topic> --once``: il comando termina dopo il primo
        messaggio. Se il topic non pubblica entro il timeout, il comando viene
        interrotto e l'esito segnala l'assenza di messaggi.

        Args:
            topic: Nome del topic (es. ``/chatter``).

        Returns:
            Il messaggio catturato (YAML) o un esito che spiega l'assenza.
        """
        result = self._runner.run(
            ["topic", "echo", "--once", "--full-length", topic],
            timeout=self._settings.ros_command_timeout,
        )
        message = result.stdout.strip()
        if message:
            return TopicEcho(topic=topic, message=message, available=True)
        if result.timed_out:
            detail = (
                "Nessun messaggio ricevuto entro il timeout: il topic potrebbe "
                "essere silente o privo di publisher attivi."
            )
        else:
            detail = result.stderr.strip() or "Nessun messaggio disponibile."
        return TopicEcho(topic=topic, message="", available=False, detail=detail)
