"""Esecuzione in background delle euristiche di salute (anti-blocco del backend).

Le verifiche di salute misurano la frequenza dei topic con ``ros2 topic hz``,
un comando che **non termina da solo** e va interrotto via timeout: ogni misura
puo' quindi durare diversi secondi. Eseguire questa misura direttamente
nell'handler HTTP di ``/health`` e' pericoloso: con il polling del frontend le
richieste lente si accumulano e saturano il threadpool di Starlette, fino a
rendere irraggiungibile l'intero backend (anche ``/healthz``).

`HealthMonitor` sposta la misura in un thread dedicato che aggiorna
periodicamente un report in cache. L'endpoint HTTP restituisce semplicemente
l'ultimo report calcolato, in modo immediato e non bloccante.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from app.models.schemas import HealthReport, NodeStatus
from app.services.health_service import HealthService


class HealthMonitor:
    """Calcola in background il report di salute e lo mantiene in cache."""

    def __init__(
        self,
        service_factory: Callable[[], HealthService],
        interval: float = 2.0,
    ) -> None:
        """Inizializza il monitor (senza avviarlo).

        Args:
            service_factory: Funzione che costruisce un `HealthService` fresco
                ad ogni ciclo (cosi' rilegge i topic attesi correnti dalle
                impostazioni, anche dopo una riconfigurazione a caldo).
            interval: Pausa (secondi) tra la fine di un ciclo e l'inizio del
                successivo.
        """
        self._service_factory = service_factory
        self._interval = interval
        self._lock = threading.Lock()
        self._report: HealthReport | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._wakeup = threading.Event()

    def start(self) -> None:
        """Avvia il thread di calcolo periodico (idempotente)."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._run, name="health-monitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Ferma il thread e ne attende la terminazione."""
        self._running = False
        self._wakeup.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=10.0)

    def get_report(self) -> HealthReport:
        """Restituisce l'ultimo report calcolato (non bloccante).

        Returns:
            L'ultimo `HealthReport` in cache; se la prima misura non e' ancora
            disponibile, un report neutro con stato GREEN e una nota esplicativa.
        """
        with self._lock:
            if self._report is not None:
                return self._report
        return HealthReport(
            node="system",
            status=NodeStatus.GREEN,
            topics=[],
            notes=["Misura di salute in corso: attendere il primo ciclo."],
        )

    def _run(self) -> None:
        """Loop del thread: ricalcola il report e lo memorizza in cache."""
        while self._running:
            try:
                report = self._service_factory().build_report()
                with self._lock:
                    self._report = report
            except Exception:  # pragma: no cover - robustezza runtime
                # Non interrompiamo il loop: il prossimo ciclo riprovera'.
                pass
            self._wakeup.wait(timeout=self._interval)
            self._wakeup.clear()
