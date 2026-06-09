"""Monitor in background dell'albero delle trasformate TF (``/tf``, ``/tf_static``).

In ROS 2 le relazioni spaziali tra i frame di riferimento sono pubblicate come
``tf2_msgs/msg/TFMessage`` sui topic ``/tf`` (dinamiche) e ``/tf_static``. Questo
monitor mantiene una sottoscrizione continua a entrambi e ricostruisce l'albero
parent -> child dei frame, permettendo alla dashboard di mostrarlo e di
evidenziare eventuali alberi scollegati (piu' di una radice).

Come gli altri monitor, l'import di ``rclpy`` e' lazy: senza ROS il monitor non
si attiva e l'albero risulta vuoto/non disponibile.
"""

from __future__ import annotations

import threading

from app.models.schemas import TfFrameInfo, TfTree

# Nome del nodo rclpy creato internamente per ascoltare ``/tf`` e ``/tf_static``.
LISTENER_NODE_NAME = "combo_debug_tf_listener"


class TfMonitor:
    """Sottoscrittore in background di ``/tf`` e ``/tf_static``.

    Mantiene la relazione genitore di ciascun frame (ultima osservata). E'
    thread-safe e riavviabile a caldo quando cambia il dominio DDS.
    """

    def __init__(self) -> None:
        """Inizializza il monitor (senza avviarlo)."""
        # frame_id -> (parent_frame_id, is_static)
        self._parents: dict[str, tuple[str, bool]] = {}
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
            target=self._run, name="tf-monitor", daemon=True
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
        """Indica se le sottoscrizioni TF sono realmente attive.

        Returns:
            ``True`` se ``rclpy`` e' disponibile e il nodo sta ascoltando.
        """
        return self._active

    # -- Lettura -------------------------------------------------------------

    def get_tree(self) -> TfTree:
        """Costruisce l'albero TF corrente dai frame osservati.

        Returns:
            Un `TfTree` con l'elenco dei frame, il loro genitore e le radici.
            Piu' di una radice indica alberi TF scollegati tra loro.
        """
        with self._lock:
            parents = dict(self._parents)

        if not parents and not self._active:
            return TfTree(
                available=self._active,
                detail=(
                    "Monitor TF non attivo (ROS non disponibile) o nessuna "
                    "trasformata ancora ricevuta su /tf, /tf_static."
                ),
            )

        all_frames: set[str] = set(parents)
        for parent, _is_static in parents.values():
            all_frames.add(parent)

        frames: list[TfFrameInfo] = []
        roots: list[str] = []
        for frame in sorted(all_frames):
            if frame in parents:
                parent, is_static = parents[frame]
                frames.append(
                    TfFrameInfo(frame_id=frame, parent=parent, is_static=is_static)
                )
            else:
                # Frame mai apparso come child: e' una radice dell'albero.
                frames.append(TfFrameInfo(frame_id=frame, parent=None))
                roots.append(frame)
        return TfTree(available=self._active, frames=frames, roots=sorted(roots))

    # -- Thread interno ------------------------------------------------------

    def _run(self) -> None:
        """Loop principale del thread: gestisce avvio e riavvii delle sub."""
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
        """Crea contesto/nodo rclpy, sottoscrive i topic TF e fa spin."""
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import QoSDurabilityPolicy, QoSProfile
        from tf2_msgs.msg import TFMessage

        context = rclpy.Context()
        rclpy.init(context=context)
        node = None
        executor = None
        try:
            node = rclpy.create_node(LISTENER_NODE_NAME, context=context)
            node.create_subscription(
                TFMessage, "/tf", lambda m: self._on_message(m, False), 50
            )
            # /tf_static usa durability TRANSIENT_LOCAL: serve un QoS compatibile
            # per ricevere le trasformate gia' pubblicate prima della sub.
            static_qos = QoSProfile(
                depth=50, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
            )
            node.create_subscription(
                TFMessage,
                "/tf_static",
                lambda m: self._on_message(m, True),
                static_qos,
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

    def _on_message(
        self, msg: object, is_static: bool
    ) -> None:  # pragma: no cover - richiede ROS
        """Callback di sottoscrizione: aggiorna le relazioni parent/child.

        Args:
            msg: Messaggio ``tf2_msgs/msg/TFMessage`` ricevuto.
            is_static: ``True`` se proviene da ``/tf_static``.
        """
        for transform in getattr(msg, "transforms", []) or []:
            header = getattr(transform, "header", None)
            parent = str(getattr(header, "frame_id", "")).lstrip("/")
            child = str(getattr(transform, "child_frame_id", "")).lstrip("/")
            if parent and child:
                self.update_transform(child, parent, is_static)

    def update_transform(self, child: str, parent: str, is_static: bool) -> None:
        """Registra una relazione child -> parent (usato anche nei test).

        Args:
            child: Frame figlio.
            parent: Frame genitore.
            is_static: ``True`` se la trasformata e' statica.
        """
        with self._lock:
            self._parents[child] = (parent, is_static)
        self._active = True
