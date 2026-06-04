"""Implementazioni fake usate nei test.

Grazie al pattern Adapter, i service dipendono dall'astrazione
`RosCommandRunner`: nei test la sostituiamo con un runner programmabile, senza
bisogno di un'installazione ROS reale.
"""

from __future__ import annotations

from app.adapters.ros_cli import CommandResult


class FakeRosCommandRunner:
    """Runner ROS programmabile per i test.

    Restituisce risultati predefiniti in base al primo argomento del comando
    (es. ``node``, ``topic``).
    """

    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        """Inizializza il runner.

        Args:
            responses: Mappa da prefisso di argomenti al risultato da restituire.
                Viene scelto il prefisso piu' lungo che combacia.
        """
        self._responses = responses

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
