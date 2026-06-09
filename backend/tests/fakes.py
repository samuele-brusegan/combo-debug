"""Implementazioni fake usate nei test.

Grazie al pattern Adapter, i service dipendono dall'astrazione
`RosCommandRunner`: nei test la sostituiamo con un runner programmabile, senza
bisogno di un'installazione ROS reale.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from app.adapters.ros_cli import CommandResult


class FakeRosCommandRunner:
    """Runner ROS programmabile per i test.

    Restituisce risultati predefiniti in base al primo argomento del comando
    (es. ``node``, ``topic``).
    """

    def __init__(
        self,
        responses: dict[tuple[str, ...], CommandResult],
        stream_responses: dict[tuple[str, ...], Sequence[str]] | None = None,
    ) -> None:
        """Inizializza il runner.

        Args:
            responses: Mappa da prefisso di argomenti al risultato da restituire.
                Viene scelto il prefisso piu' lungo che combacia.
            stream_responses: Mappa da prefisso di argomenti alla sequenza di
                righe prodotte da `stream_lines` (per i comandi a lunga durata).
        """
        self._responses = responses
        self._stream_responses = stream_responses or {}

    def run(self, args: list[str], timeout: float | None = None) -> CommandResult:
        """Restituisce la risposta programmata per gli argomenti dati.

        Args:
            args: Argomenti del comando.
            timeout: Ignorato (presente per compatibilita' col protocollo).

        Returns:
            Il `CommandResult` associato al prefisso piu' specifico che combacia,
            oppure un risultato di errore se nessun prefisso combacia.
        """
        for length in range(len(args), 0, -1):
            key = tuple(args[:length])
            if key in self._responses:
                return self._responses[key]
        return CommandResult(args=args, returncode=1, stdout="", stderr="no match")

    async def stream_lines(self, args: list[str]) -> AsyncIterator[str]:
        """Produce le righe programmate per il comando di streaming dato.

        Args:
            args: Argomenti del comando (es. ``["topic", "echo", "/chatter"]``).

        Yields:
            Le righe associate al prefisso piu' specifico che combacia; nessuna
            riga se non c'e' corrispondenza.
        """
        for length in range(len(args), 0, -1):
            key = tuple(args[:length])
            if key in self._stream_responses:
                for line in self._stream_responses[key]:
                    yield line
                return
