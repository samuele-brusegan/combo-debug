"""Monitor in background del topic ``/rosout`` (log centralizzati di ROS 2).

Quando il backend gira insieme a ROS 2 (container o robot reale), ogni nodo
pubblica i propri log sul topic ``/rosout`` (``rcl_interfaces/msg/Log``). Questo
monitor mantiene una sottoscrizione **continua** a quel topic in un thread
dedicato, accumulando le righe in un buffer circolare indicizzabile per nodo.

In questo modo la dashboard puo' mostrare i log *reali* del grafo ROS osservato
(non i soli file locali della demo) e, al click su un nodo, filtrare i log per
quel nodo specifico.

L'import di ``rclpy`` e' volutamente **lazy** (dentro il thread): nei test e in
ambienti senza ROS il modulo resta importabile e il monitor semplicemente non
si attiva (``is_active() == False``), lasciando attivo il fallback su file.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from app.models.schemas import LogEntry, LogLevel

if TYPE_CHECKING:  # pragma: no cover - solo per il type checker
    from collections.abc import Iterable

# Nome del nodo rclpy creato internamente per ascoltare ``/rosout``. E' esposto
# come costante cosi' che il NodeService possa escluderlo dalla lista dei nodi
# mostrati in dashboard (e' un nodo "di servizio", non parte del sistema osservato).
LISTENER_NODE_NAME = "combo_debug_rosout_listener"

# Mappa dei livelli numerici di ``rcl_interfaces/msg/Log`` -> livelli interni.
_LEVEL_MAP: dict[int, LogLevel] = {
    10: LogLevel.DEBUG,
    20: LogLevel.INFO,
    30: LogLevel.WARN,
    40: LogLevel.ERROR,
    50: LogLevel.FATAL,
}


def _normalize(name: str) -> str:
    """Normalizza un nome di nodo/logger per il confronto.

    I log su ``/rosout`` riportano il logger name senza lo slash iniziale
    (es. ``talker``), mentre ``ros2 node list`` usa il nome completo
    (es. ``/talker``). Normalizziamo entrambi rimuovendo lo slash iniziale.

    Args:
        name: Nome del nodo o del logger.

    Returns:
        Il nome senza slash iniziale e senza spazi.
    """
    return name.strip().lstrip("/")


class RosoutMonitor:
    """Sottoscrittore in background del topic ``/rosout``.

    Mantiene un buffer circolare delle ultime righe di log osservate nel grafo
    ROS corrente. E' thread-safe e puo' essere riavviato a caldo quando cambia
    il dominio DDS (vedi `restart`), cosi' da seguire la riconfigurazione della
    connessione verso un ROS reale.
    """

    def __init__(self, buffer_size: int = 5000) -> None:
        """Inizializza il monitor (senza avviarlo).

        Args:
            buffer_size: Numero massimo di righe di log mantenute in memoria.
        """
        self._buffer: deque[LogEntry] = deque(maxlen=buffer_size)
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
            target=self._run, name="rosout-monitor", daemon=True
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
        """Richiede il riavvio della sottoscrizione (es. dopo cambio dominio).

        Il thread tear-down il contesto rclpy corrente e ne crea uno nuovo, che
        eredita il ``ROS_DOMAIN_ID`` aggiornato dall'ambiente.
        """
        if self._running:
            self._restart_event.set()

    def is_active(self) -> bool:
        """Indica se la sottoscrizione a ``/rosout`` e' realmente attiva.

        Returns:
            ``True`` se ``rclpy`` e' disponibile e il nodo sta ascoltando.
        """
        return self._active

    # -- Lettura del buffer --------------------------------------------------

    def get_logs(
        self,
        node: str | None = None,
        levels: set[LogLevel] | None = None,
        max_entries: int = 500,
    ) -> list[LogEntry]:
        """Restituisce le righe di log accumulate, dalla piu' recente.

        Args:
            node: Se valorizzato, filtra i log per il nodo indicato (match sul
                nome normalizzato, con o senza slash iniziale).
            levels: Se valorizzato, mantiene solo i livelli indicati.
            max_entries: Numero massimo di righe restituite.

        Returns:
            Lista di `LogEntry` ordinata dalla piu' recente alla piu' vecchia.
        """
        target = _normalize(node) if node else None
        with self._lock:
            snapshot = list(self._buffer)

        result: list[LogEntry] = []
        for entry in reversed(snapshot):
            if target is not None and _normalize(entry.source) != target:
                continue
            if levels is not None and entry.level not in levels:
                continue
            result.append(entry)
            if len(result) >= max_entries:
                break
        return result

    def summary(self) -> dict[str, int]:
        """Conteggia le righe di log nel buffer per livello.

        Returns:
            Mappa livello -> numero di righe.
        """
        counter: dict[str, int] = {}
        with self._lock:
            snapshot = list(self._buffer)
        for entry in snapshot:
            counter[entry.level.value] = counter.get(entry.level.value, 0) + 1
        return counter

    def known_nodes(self) -> list[str]:
        """Restituisce i nomi dei nodi che hanno prodotto almeno un log.

        Returns:
            Lista ordinata dei nomi (normalizzati) presenti nel buffer.
        """
        with self._lock:
            names = {_normalize(entry.source) for entry in self._buffer}
        return sorted(names)

    # -- Thread interno ------------------------------------------------------

    def _run(self) -> None:
        """Loop principale del thread: gestisce avvio e riavvii della sottoscrizione."""
        try:
            import rclpy  # noqa: F401  (verifica disponibilita')
        except Exception:  # pragma: no cover - dipende dall'ambiente runtime
            # ROS/rclpy non disponibili (es. ambiente di test): nessun monitor.
            self._active = False
            self._running = False
            return

        while self._running:
            self._restart_event.clear()
            try:
                self._spin_once_session()
            except Exception:  # pragma: no cover - robustezza runtime
                self._active = False
            # Se l'uscita non e' dovuta a un riavvio richiesto, evitiamo un
            # busy-loop in caso di errori ripetuti.
            if self._running and not self._restart_event.is_set():
                self._restart_event.wait(timeout=2.0)

    def _spin_once_session(self) -> None:  # pragma: no cover - richiede ROS
        """Crea contesto/nodo rclpy, sottoscrive ``/rosout`` e fa spin.

        Resta in spin finche' non viene richiesto stop o restart; al termine
        rilascia in modo pulito le risorse rclpy.
        """
        import rclpy
        from rcl_interfaces.msg import Log
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import QoSProfile, ReliabilityPolicy

        context = rclpy.Context()
        rclpy.init(context=context)
        node = None
        executor = None
        try:
            node = rclpy.create_node(LISTENER_NODE_NAME, context=context)
            # /rosout e' pubblicato in modalita' affidabile con history ampia:
            # una sub RELIABLE con depth elevata massimizza la cattura dei log.
            qos = QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE)
            node.create_subscription(Log, "/rosout", self._on_message, qos)
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
        """Callback di sottoscrizione: converte un msg ``Log`` in `LogEntry`.

        Args:
            msg: Messaggio ``rcl_interfaces/msg/Log`` ricevuto da ``/rosout``.
        """
        level = _LEVEL_MAP.get(int(getattr(msg, "level", 20)), LogLevel.INFO)
        name = str(getattr(msg, "name", "") or "sconosciuto")
        text = str(getattr(msg, "msg", ""))
        line = int(getattr(msg, "line", 0) or 0)
        timestamp = self._extract_timestamp(getattr(msg, "stamp", None))
        entry = LogEntry(
            level=level,
            message=text,
            source=name,
            line_number=line,
            timestamp=timestamp,
        )
        with self._lock:
            self._buffer.append(entry)

    @staticmethod
    def _extract_timestamp(stamp: object) -> str:  # pragma: no cover - richiede ROS
        """Converte lo ``stamp`` di un messaggio ``Log`` in stringa ISO 8601.

        Lo ``stamp`` e' un ``builtin_interfaces/msg/Time`` (``sec``/``nanosec``).
        Se non e' valorizzato (orario simulato non impostato) si ripiega
        sull'orario di ricezione del backend, cosi' la colonna e' sempre piena.

        Args:
            stamp: Campo ``stamp`` del messaggio ``/rosout`` (o ``None``).

        Returns:
            L'istante dell'evento in formato ISO 8601 con i millisecondi.
        """
        sec = int(getattr(stamp, "sec", 0) or 0)
        nanosec = int(getattr(stamp, "nanosec", 0) or 0)
        epoch = sec + nanosec / 1e9 if sec > 0 else datetime.now().timestamp()
        return datetime.fromtimestamp(epoch).isoformat(timespec="milliseconds")

    def add_entries(self, entries: Iterable[LogEntry]) -> None:
        """Inietta manualmente delle righe nel buffer (utile nei test).

        Args:
            entries: Righe di log da aggiungere al buffer.
        """
        with self._lock:
            self._buffer.extend(entries)
        self._active = True
