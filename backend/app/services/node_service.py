"""Servizio di rilevamento dei nodi ROS 2 e del loro stato (color-coding).

Implementa il requisito 1: elenco dei nodi con indicatore VERDE/ROSSO.

Regole di stato:
    * Un nodo presente nel grafo e che risponde a ``ros2 node info`` -> VERDE.
    * Un nodo presente ma non interrogabile (timeout/errore) -> ROSSO
      (irraggiungibile).
    * Un nodo "atteso" (configurato) ma assente dal grafo -> ROSSO
      (crashato/offline).
"""

from __future__ import annotations

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import NodeStatus, RosNode
from app.services.diagnostics_monitor import (
    LISTENER_NODE_NAME as DIAGNOSTICS_LISTENER_NODE_NAME,
)
from app.services.rosout_monitor import LISTENER_NODE_NAME
from app.services.tf_monitor import LISTENER_NODE_NAME as TF_LISTENER_NODE_NAME

# Nodi di servizio interni del backend (sottoscrittori in background), da
# escludere dalla vista dei nodi del sistema ROS osservato.
_INTERNAL_LISTENER_NODES: frozenset[str] = frozenset(
    {LISTENER_NODE_NAME, DIAGNOSTICS_LISTENER_NODE_NAME, TF_LISTENER_NODE_NAME}
)


class NodeService:
    """Raccoglie ed valuta lo stato dei nodi ROS 2.

    Dipende dall'astrazione `RosCommandRunner` (Dependency Inversion), quindi
    e' totalmente testabile senza un'installazione ROS reale.
    """

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per eseguire i comandi ros2.
            settings: Configurazione applicativa.
        """
        self._runner = runner
        self._settings = settings

    def list_active_node_names(self) -> list[str]:
        """Restituisce i nomi dei nodi attualmente presenti nel grafo.

        Returns:
            Lista ordinata e deduplicata dei nomi dei nodi. Vuota se la CLI
            non e' disponibile o il comando fallisce.
        """
        result = self._runner.run(["node", "list"])
        if not result.ok:
            return []
        names = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        # Escludiamo i nodi di servizio interni (sottoscrittori /rosout,
        # /diagnostics, /tf): sono parte del backend, non del sistema osservato.
        for listener in _INTERNAL_LISTENER_NODES:
            names.discard(f"/{listener}")
            names.discard(listener)
        return sorted(names)

    def _is_responsive(self, node_name: str) -> bool:
        """Verifica se un nodo risponde a una interrogazione del grafo.

        Args:
            node_name: Nome completo del nodo (es. ``/talker``).

        Returns:
            ``True`` se ``ros2 node info`` restituisce un esito positivo.
        """
        result = self._runner.run(
            ["node", "info", node_name],
            timeout=self._settings.ros_command_timeout,
        )
        return result.ok

    def get_nodes(self) -> list[RosNode]:
        """Costruisce l'elenco dei nodi con il relativo stato color-coded.

        Combina i nodi realmente presenti nel grafo con quelli attesi dalla
        configurazione, per poter evidenziare in ROSSO i nodi crashati o
        offline anche quando sono spariti dal grafo.

        Returns:
            Lista ordinata di `RosNode`, uno per ciascun nodo osservato o atteso.
        """
        active = self.list_active_node_names()
        expected = self._settings.parse_expected_nodes()
        all_names = sorted(set(active) | set(expected))

        nodes: list[RosNode] = []
        for name in all_names:
            if name not in active:
                nodes.append(
                    RosNode(
                        name=name,
                        status=NodeStatus.RED,
                        reason="Nodo atteso ma assente dal grafo (crashato/offline).",
                    )
                )
                continue

            if self._is_responsive(name):
                nodes.append(
                    RosNode(
                        name=name,
                        status=NodeStatus.GREEN,
                        reason="Nodo attivo e responsivo.",
                    )
                )
            else:
                nodes.append(
                    RosNode(
                        name=name,
                        status=NodeStatus.RED,
                        reason="Nodo presente ma non risponde (irraggiungibile).",
                    )
                )
        return nodes
