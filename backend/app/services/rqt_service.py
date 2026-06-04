"""Bridge verso i tool di diagnostica grafici di ROS (rqt) - requisito 4.

I tool ``rqt`` sono applicazioni grafiche (richiedono un server X / DISPLAY).
Per ragioni di sicurezza e portabilita' il backend non avvia di default
processi grafici: espone invece i comandi pronti da eseguire sulla macchina
ROS, che il frontend mostra all'operatore (es. con un pulsante "copia").

E' comunque previsto un metodo opzionale di lancio diretto, utilizzabile solo
quando l'ambiente ha un DISPLAY valido.
"""

from __future__ import annotations

import os
import subprocess

from app.models.schemas import CommandSuggestion


class RqtService:
    """Fornisce i comandi dei tool rqt e ne consente il lancio opzionale."""

    def get_suggestions(self) -> list[CommandSuggestion]:
        """Restituisce i comandi diagnostici rqt suggeriti.

        Returns:
            Lista di `CommandSuggestion` con i principali tool rqt.
        """
        return [
            CommandSuggestion(
                label="rqt_graph",
                command="ros2 run rqt_graph rqt_graph",
                description="Visualizza il grafo dei nodi e dei topic.",
            ),
            CommandSuggestion(
                label="rqt_console",
                command="ros2 run rqt_console rqt_console",
                description="Aggregatore grafico dei messaggi di log.",
            ),
            CommandSuggestion(
                label="rqt_top",
                command="ros2 run rqt_top rqt_top",
                description="Monitor di CPU/memoria dei processi dei nodi.",
            ),
            CommandSuggestion(
                label="rqt (suite)",
                command="rqt",
                description="Avvia la suite rqt completa con tutti i plugin.",
            ),
        ]

    def has_display(self) -> bool:
        """Indica se l'ambiente dispone di un server grafico (DISPLAY).

        Returns:
            ``True`` se la variabile ``DISPLAY`` e' impostata.
        """
        return bool(os.environ.get("DISPLAY"))

    def launch(self, command: str) -> int:
        """Avvia un comando rqt in modo detached (uso opzionale).

        Args:
            command: Comando shell da eseguire (tipicamente uno dei suggeriti).

        Returns:
            Il PID del processo avviato.

        Raises:
            RuntimeError: Se non e' disponibile un DISPLAY grafico.
        """
        if not self.has_display():
            raise RuntimeError(
                "Nessun DISPLAY disponibile: impossibile avviare un tool grafico "
                "rqt da questo container."
            )
        process = subprocess.Popen(  # noqa: S602 - comando controllato/whitelist
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return process.pid
