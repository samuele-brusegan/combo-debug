"""Adapter verso la CLI di ROS 2 (pattern Adapter + Dependency Inversion).

Questo modulo e' l'unico punto del backend che esegue realmente delle SysCall
(`subprocess`). Tutto il resto del codice dipende dall'astrazione
`RosCommandRunner` e non dall'implementazione concreta: questo rispetta il
Dependency Inversion Principle e permette di sostituire facilmente il runner
nei test (con un fake) o, in futuro, con un client `rclpy` nativo senza
toccare i service.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    """Esito dell'esecuzione di un comando esterno.

    Attributes:
        args: Argomenti del comando eseguito.
        returncode: Codice di uscita del processo.
        stdout: Output standard catturato.
        stderr: Error standard catturato.
        timed_out: ``True`` se il comando e' stato interrotto per timeout.
    """

    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """bool: ``True`` se il comando e' terminato con successo (rc == 0)."""
        return self.returncode == 0 and not self.timed_out


class RosCommandRunner(Protocol):
    """Astrazione per l'esecuzione di comandi `ros2`.

    Definisce il contratto richiesto dai service. Qualsiasi implementazione
    (subprocess reale, fake nei test, futuro backend rclpy) deve rispettarlo.
    """

    def run(self, args: list[str], timeout: float | None = None) -> CommandResult:
        """Esegue un comando e ne restituisce l'esito.

        Args:
            args: Argomenti del comando, CLI esclusa (es. ``["node", "list"]``).
            timeout: Timeout in secondi; ``None`` per usare il default del runner.

        Returns:
            L'esito dell'esecuzione incapsulato in un `CommandResult`.
        """
        ...

    def stream_lines(self, args: list[str]) -> AsyncIterator[str]:
        """Esegue un comando `ros2` a lunga durata producendo le righe di stdout.

        A differenza di `run` (che attende il termine del processo), questo
        metodo avvia il comando e restituisce le righe man mano che vengono
        prodotte, utile per le sottoscrizioni continue (es. ``ros2 topic echo``).
        Il processo viene terminato quando il consumatore chiude l'iteratore
        asincrono (es. alla disconnessione del client).

        Args:
            args: Argomenti del comando, CLI esclusa (es. ``["topic", "echo"]``).

        Returns:
            Un iteratore asincrono di righe di stdout (senza il newline finale).
        """
        ...


class SubprocessRosCommandRunner:
    """Implementazione concreta di `RosCommandRunner` basata su `subprocess`.

    Esegue i comandi tramite l'eseguibile `ros2` presente nel PATH del
    container. L'eseguibile e' configurabile per favorire i test.
    """

    def __init__(self, executable: str = "ros2", default_timeout: float = 8.0) -> None:
        """Inizializza il runner.

        Args:
            executable: Nome o percorso dell'eseguibile della CLI ROS 2.
            default_timeout: Timeout di default applicato ai comandi.
        """
        self._executable = executable
        self._default_timeout = default_timeout

    def is_available(self) -> bool:
        """Indica se l'eseguibile ROS 2 e' presente nel sistema.

        Returns:
            ``True`` se l'eseguibile e' risolvibile nel PATH.
        """
        return shutil.which(self._executable) is not None

    def run(self, args: list[str], timeout: float | None = None) -> CommandResult:
        """Esegue ``ros2 <args>`` catturandone l'output.

        Args:
            args: Argomenti passati alla CLI ros2.
            timeout: Timeout in secondi; se ``None`` usa il default.

        Returns:
            L'esito dell'esecuzione. In caso di eseguibile mancante o timeout
            viene comunque restituito un `CommandResult` (mai un'eccezione),
            cosi' i service possono degradare in modo controllato.
        """
        command = [self._executable, *args]
        effective_timeout = timeout if timeout is not None else self._default_timeout

        if not self.is_available():
            return CommandResult(
                args=command,
                returncode=127,
                stdout="",
                stderr=f"Eseguibile '{self._executable}' non trovato nel PATH.",
            )

        # Forziamo l'output non bufferizzato del processo figlio (la CLI ros2 e'
        # Python): comandi come `ros2 topic hz` non terminano da soli e li
        # interrompiamo via timeout (SIGKILL). Con il buffering a blocchi tipico
        # di uno stdout collegato a una pipe, le righe gia' prodotte resterebbero
        # nel buffer del figlio e andrebbero perse alla kill, causando misure
        # "vuote" intermittenti. ``PYTHONUNBUFFERED`` fa sì che ogni riga venga
        # scaricata subito e quindi catturata anche in caso di timeout.
        child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
                env=child_env,
            )
        except subprocess.TimeoutExpired as exc:
            raw_partial: object = exc.stdout
            if isinstance(raw_partial, bytes):
                partial = raw_partial.decode(errors="replace")
            elif isinstance(raw_partial, str):
                partial = raw_partial
            else:
                partial = ""
            return CommandResult(
                args=command,
                returncode=124,
                stdout=partial,
                stderr=f"Timeout dopo {effective_timeout}s",
                timed_out=True,
            )

        return CommandResult(
            args=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    async def stream_lines(  # pragma: no cover - avvia un subprocess reale
        self, args: list[str]
    ) -> AsyncIterator[str]:
        """Avvia ``ros2 <args>`` e produce le righe di stdout man mano che arrivano.

        Usa `asyncio.create_subprocess_exec` cosi' che la lettura sia
        cancellabile: alla chiusura dell'iteratore (es. disconnessione del
        client SSE) il blocco ``finally`` termina il processo figlio, evitando
        comandi ``ros2`` orfani.

        Args:
            args: Argomenti passati alla CLI ros2 (es. ``["topic", "echo", ...]``).

        Yields:
            Le righe di stdout del processo, senza il newline finale.
        """
        if not self.is_available():
            return

        process = await asyncio.create_subprocess_exec(
            self._executable,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        assert process.stdout is not None
        try:
            while True:
                raw = await process.stdout.readline()
                if not raw:
                    break  # EOF: il processo e' terminato.
                yield raw.decode(errors="replace").rstrip("\n")
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except (TimeoutError, asyncio.TimeoutError):
                    with contextlib.suppress(ProcessLookupError):
                        process.kill()
