"""Monitor in background del topic ``/diagnostics`` (diagnostica hardware ROS).

Molti stack ROS 2 (driver, robot_state_publisher, nodi hardware) pubblicano lo
stato dei propri componenti su ``/diagnostics`` come ``DiagnosticArray``. Questo
monitor mantiene una sottoscrizione continua a quel topic in un thread dedicato
e conserva l'**ultimo** stato per ciascun componente, cosi' la dashboard puo'
mostrarlo color-coded (OK/WARN/ERROR/STALE).

Come `RosoutMonitor`, l'import di ``rclpy`` e' lazy (dentro il thread): nei test
e in ambienti senza ROS il modulo resta importabile e il monitor semplicemente
non si attiva (``is_active() == False``).
"""

from __future__ import annotations

import threading

from app.models.schemas import (
    DiagnosticLevel,
    DiagnosticsSnapshot,
    DiagnosticStatus,
    DiagnosticValue,
)

# Nome del nodo rclpy creato internamente per ascoltare ``/diagnostics``.
LISTENER_NODE_NAME = "combo_debug_diagnostics_listener"

# Mappa dei livelli di ``diagnostic_msgs/DiagnosticStatus`` -> livelli interni.
_LEVEL_MAP: dict[int, DiagnosticLevel] = {
    0: DiagnosticLevel.OK,
    1: DiagnosticLevel.WARN,
    2: DiagnosticLevel.ERROR,
    3: DiagnosticLevel.STALE,
}


class DiagnosticsMonitor:
    """Sottoscrittore in background del topic ``/diagnostics``.

    Mantiene l'ultimo stato diagnostico osservato per ciascun componente. E'
    thread-safe e riavviabile a caldo quando cambia il dominio DDS.
    """

    def __init__(self) -> None:
        """Inizializza il monitor (senza avviarlo)."""
        self._latest: dict[str, DiagnosticStatus] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._active = False
        self._restart_event = threading.Event()

    # -- Ciclo di vita -------------------------------------------------------

    def start(self) -> None:
        """Avvia il thread di monitoraggio (idempotente)."""
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._run, name="diagnostics-monitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Ferma il thread di monitoraggio e ne attende la terminazione."""
        self._running = False
        self._restart_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5.0)
        self._active = False

    def restart(self) -> None:
        """Richiede il riavvio della sottoscrizione (es. dopo cambio dominio)."""
        if self._running:
            self._restart_event.set()

    def is_active(self) -> bool:
        """Indica se la sottoscrizione a ``/diagnostics`` e' realmente attiva.

        Returns:
            ``True`` se ``rclpy`` e' disponibile e il nodo sta ascoltando.
        """
        return self._active

    # -- Lettura -------------------------------------------------------------

    def snapshot(self) -> DiagnosticsSnapshot:
        """Restituisce l'ultimo stato diagnostico noto di ogni componente.

        Returns:
            Una `DiagnosticsSnapshot` con le entrate ordinate per nome.
        """
        with self._lock:
            statuses = sorted(self._latest.values(), key=lambda s: s.name)
        if not statuses and not self._active:
            return DiagnosticsSnapshot(
                available=self._active,
                statuses=[],
                detail=(
                    "Monitor diagnostico non attivo (ROS non disponibile) o "
                    "nessun messaggio ancora ricevuto su /diagnostics."
                ),
            )
        return DiagnosticsSnapshot(available=self._active, statuses=statuses)

    # -- Thread interno ------------------------------------------------------

    def _run(self) -> None:
        """Loop principale del thread: gestisce avvio e riavvii della sub."""
        try:
            import rclpy  # noqa: F401  (verifica disponibilita')
        except Exception:  # pragma: no cover - dipende dall'ambiente runtime
            self._active = False
            self._running = False
            return

        while self._running:
            self._restart_event.clear()
            try:
                self._spin_once_session()
            except Exception:  # pragma: no cover - robustezza runtime
                self._active = False
            if self._running and not self._restart_event.is_set():
                self._restart_event.wait(timeout=2.0)

    def _spin_once_session(self) -> None:  # pragma: no cover - richiede ROS
        """Crea contesto/nodo rclpy, sottoscrive ``/diagnostics`` e fa spin."""
        import rclpy
        from diagnostic_msgs.msg import DiagnosticArray
        from rclpy.executors import SingleThreadedExecutor

        context = rclpy.Context()
        rclpy.init(context=context)
        node = None
        executor = None
        try:
            node = rclpy.create_node(LISTENER_NODE_NAME, context=context)
            node.create_subscription(
                DiagnosticArray, "/diagnostics", self._on_message, 10
            )
            executor = SingleThreadedExecutor(context=context)
            executor.add_node(node)
            self._active = True
            while self._running and not self._restart_event.is_set():
                executor.spin_once(timeout_sec=0.5)
        finally:
            self._active = False
            if executor is not None:
                executor.shutdown()
            if node is not None:
                node.destroy_node()
            if context.ok():
                rclpy.shutdown(context=context)

    def _on_message(self, msg: object) -> None:  # pragma: no cover - richiede ROS
        """Callback di sottoscrizione: aggiorna lo stato per ogni componente.

        Args:
            msg: Messaggio ``diagnostic_msgs/msg/DiagnosticArray`` ricevuto.
        """
        for status in getattr(msg, "status", []) or []:
            self.update_status(self._to_status(status))

    @staticmethod
    def _to_status(status: object) -> DiagnosticStatus:  # pragma: no cover - ROS
        """Converte un ``DiagnosticStatus`` ROS nello schema interno.

        Args:
            status: Voce ``diagnostic_msgs/msg/DiagnosticStatus``.

        Returns:
            L'entrata diagnostica come `DiagnosticStatus` interno.
        """
        raw_level = getattr(status, "level", 0)
        # Il campo ``level`` e' un int8: rclpy puo' esporlo come int o come byte.
        if isinstance(raw_level, bytes | bytearray):
            raw_level = int.from_bytes(bytes(raw_level), "big")
        level = _LEVEL_MAP.get(int(raw_level), DiagnosticLevel.STALE)
        values = [
            DiagnosticValue(
                key=str(getattr(kv, "key", "")), value=str(getattr(kv, "value", ""))
            )
            for kv in getattr(status, "values", []) or []
        ]
        return DiagnosticStatus(
            name=str(getattr(status, "name", "") or "sconosciuto"),
            level=level,
            message=str(getattr(status, "message", "")),
            hardware_id=str(getattr(status, "hardware_id", "")),
            values=values,
        )

    def update_status(self, status: DiagnosticStatus) -> None:
        """Inserisce/aggiorna lo stato di un componente (usato anche nei test).

        Args:
            status: Entrata diagnostica da memorizzare come ultima nota.
        """
        with self._lock:
            self._latest[status.name] = status
        self._active = True
