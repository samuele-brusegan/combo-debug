"""Euristiche avanzate sullo stato di salute dei nodi (requisito 4).

Fornisce il "Rilevamento Spin Bloccato": stima se un nodo e' in blocco
verificando che pubblichi sui topic attesi alla frequenza minima richiesta.
Se un topic atteso non riceve dati (o a frequenza troppo bassa) il nodo
relativo viene segnalato come sospetto (GIALLO).

Le verifiche sono modellate con il pattern Strategy tramite il protocollo
`HealthCheck`, cosi' da poter aggiungere nuove euristiche senza modificare il
servizio orchestratore (Open/Closed Principle).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import HealthReport, NodeStatus, TopicHealth

_AVERAGE_RATE_RE = re.compile(r"average rate:\s*([0-9]+\.?[0-9]*)", re.IGNORECASE)


class HealthCheck(Protocol):
    """Contratto di una singola euristica di salute."""

    def run(self) -> list[TopicHealth]:
        """Esegue l'euristica.

        Returns:
            Esiti dei controlli effettuati dalla strategia.
        """
        ...


class TopicFrequencyCheck:
    """Verifica che i topic attesi pubblichino alla frequenza minima richiesta.

    Misura la frequenza tramite ``ros2 topic hz`` lasciato girare per una breve
    finestra temporale e interrotto da timeout; l'output parziale contiene la
    riga ``average rate:`` da cui si estrae la frequenza media.
    """

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza la strategia.

        Args:
            runner: Adapter per i comandi ros2.
            settings: Configurazione (topic attesi e finestra di misura).
        """
        self._runner = runner
        self._settings = settings

    def _existing_topics(self) -> set[str] | None:
        """Elenca i topic attualmente presenti nel grafo ROS.

        Serve a evitare di misurare con ``ros2 topic hz`` topic che non
        esistono (es. i topic demo quando si e' collegati a un ROS reale): per
        un topic assente la misura attenderebbe inutilmente l'intero timeout,
        moltiplicando i tempi e contribuendo alla saturazione del backend.

        Returns:
            L'insieme dei topic presenti nel grafo, oppure ``None`` se il
            comando ``ros2 topic list`` non e' disponibile/fallisce (in tal
            caso non si fa alcuna assunzione e si misura comunque).
        """
        result = self._runner.run(["topic", "list"])
        if not result.ok:
            return None
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

    def _measure_hz(self, topic: str) -> float | None:
        """Misura la frequenza di pubblicazione di un topic.

        La misura entro una finestra fissa puo' fallire in modo transitorio (es.
        per un topic a bassa frequenza la finestra cattura troppo pochi messaggi
        perche' `ros2 topic hz` emetta una riga ``average rate``). Per evitare
        falsi positivi sui topic sani si ritenta fino a ``topic_hz_attempts``
        volte, fermandosi al primo successo; un topic davvero silenzioso fallira'
        comunque tutti i tentativi.

        Args:
            topic: Nome del topic da misurare.

        Returns:
            La frequenza media in Hz, oppure ``None`` se nessun tentativo e'
            riuscito a misurarla (nessun messaggio nella finestra).
        """
        attempts = max(1, self._settings.topic_hz_attempts)
        for _ in range(attempts):
            measured = self._measure_hz_once(topic)
            if measured is not None:
                return measured
        return None

    def _measure_hz_once(self, topic: str) -> float | None:
        """Esegue una singola misura di frequenza su un topic.

        Args:
            topic: Nome del topic da misurare.

        Returns:
            La frequenza media in Hz dell'ultima riga ``average rate`` prodotta,
            oppure ``None`` se non ce ne sono.
        """
        # `ros2 topic hz` non termina da solo: lo interrompiamo via timeout e
        # leggiamo l'output parziale gia' prodotto.
        window = self._settings.topic_hz_window
        result = self._runner.run(["topic", "hz", topic], timeout=window)
        matches = _AVERAGE_RATE_RE.findall(result.stdout)
        if not matches:
            return None
        try:
            return float(matches[-1])
        except ValueError:
            return None

    def run(self) -> list[TopicHealth]:
        """Controlla tutti i topic attesi configurati.

        Returns:
            Un `TopicHealth` per ciascun topic atteso.
        """
        results: list[TopicHealth] = []
        existing = self._existing_topics()
        for topic, expected_hz in self._settings.parse_expected_topics().items():
            if existing is not None and topic not in existing:
                results.append(
                    TopicHealth(
                        topic=topic,
                        expected_hz=expected_hz,
                        measured_hz=None,
                        healthy=False,
                        detail=(
                            "Topic non presente nel grafo ROS corrente "
                            "(nodo non in esecuzione o topic non pubblicato)."
                        ),
                    )
                )
                continue
            measured = self._measure_hz(topic)
            if measured is None:
                results.append(
                    TopicHealth(
                        topic=topic,
                        expected_hz=expected_hz,
                        measured_hz=None,
                        healthy=False,
                        detail=(
                            "Nessun messaggio rilevato nella finestra: il nodo "
                            "potrebbe essere bloccato o non in esecuzione."
                        ),
                    )
                )
                continue
            healthy = measured >= expected_hz
            results.append(
                TopicHealth(
                    topic=topic,
                    expected_hz=expected_hz,
                    measured_hz=round(measured, 3),
                    healthy=healthy,
                    detail=(
                        "Frequenza adeguata."
                        if healthy
                        else "Frequenza sotto la soglia attesa (spin lento/bloccato)."
                    ),
                )
            )
        return results


class HealthService:
    """Orchestratore delle euristiche di salute.

    Aggrega gli esiti delle strategie registrate in un unico report.
    """

    def __init__(self, checks: Sequence[HealthCheck]) -> None:
        """Inizializza il servizio.

        Args:
            checks: Strategie di verifica da eseguire.
        """
        self._checks = checks

    def build_report(self) -> HealthReport:
        """Esegue tutte le euristiche e produce il report complessivo.

        Returns:
            Un `HealthReport` con stato GREEN se tutti i controlli passano,
            YELLOW se almeno un controllo segnala un problema.
        """
        topics: list[TopicHealth] = []
        for check in self._checks:
            topics.extend(check.run())

        unhealthy = [topic for topic in topics if not topic.healthy]
        status = NodeStatus.GREEN if not unhealthy else NodeStatus.YELLOW
        notes = [
            f"Topic '{item.topic}' sotto soglia: {item.detail}" for item in unhealthy
        ]
        return HealthReport(
            node="system",
            status=status,
            topics=topics,
            notes=notes,
        )
