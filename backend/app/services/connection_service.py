"""Servizio di configurazione runtime della connessione al grafo ROS 2.

Permette di ricollegare il backend a un grafo ROS diverso (es. un robot reale)
**senza riavviare il container**: i parametri DDS (dominio, RMW, discovery
server) vengono scritti in ``os.environ`` e quindi ereditati da ogni nuova
SysCall ``ros2`` (ogni invocazione e' un processo figlio fresco). I nodi e i
topic attesi vengono aggiornati direttamente sull'oggetto `Settings` condiviso,
cosi' che i service li rileggano ad ogni richiesta.

Questo isola in un unico punto la logica di "riconfigurazione a caldo",
mantenendo i restanti service ignari del meccanismo (Single Responsibility).
"""

from __future__ import annotations

import os
from pathlib import Path

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import (
    ConnectionConfig,
    ConnectionDiscovery,
    ConnectionProbe,
    ConnectionUpdate,
)

# Variabili d'ambiente DDS gestite dalla riconfigurazione a caldo.
_ENV_DOMAIN = "ROS_DOMAIN_ID"
_ENV_RMW = "RMW_IMPLEMENTATION"
_ENV_DISCOVERY = "ROS_DISCOVERY_SERVER"


class ConnectionService:
    """Legge e applica a runtime la configurazione di connessione ROS 2."""

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per verificare il grafo (``ros2 node list``).
            settings: Configurazione condivisa da aggiornare a caldo.
        """
        self._runner = runner
        self._settings = settings

    def get_config(self) -> ConnectionConfig:
        """Restituisce la configurazione di connessione attualmente attiva.

        Returns:
            Lo stato corrente derivato da ``os.environ`` e dalle `Settings`.
        """
        current_domain = os.environ.get(_ENV_DOMAIN, "0")
        # Si e' "in demo" se i nodi di esempio sono stati avviati e si sta ancora
        # osservando il dominio su cui girano (cambiando dominio dalla UI per un
        # robot reale, la demo non e' piu' visibile e l'indicatore sparisce).
        demo_mode = self._settings.start_demo and current_domain == self._settings.boot_ros_domain_id
        return ConnectionConfig(
            ros_domain_id=current_domain,
            rmw_implementation=os.environ.get(_ENV_RMW, ""),
            ros_discovery_server=os.environ.get(_ENV_DISCOVERY, ""),
            expected_nodes=self._settings.expected_nodes,
            expected_topics=self._settings.expected_topics,
            ros_log_dir=str(self._settings.ros_log_dir),
            demo_mode=demo_mode,
            start_demo=self._settings.start_demo,
        )

    def apply(self, update: ConnectionUpdate) -> ConnectionConfig:
        """Applica a caldo i parametri forniti e restituisce la nuova config.

        I campi non valorizzati (``None``) vengono ignorati. Per
        ``ros_discovery_server`` una stringa vuota rimuove la variabile
        d'ambiente (discovery via multicast di default).

        Args:
            update: Aggiornamento parziale dei parametri di connessione.

        Returns:
            La configurazione risultante dopo l'applicazione.
        """
        if update.ros_domain_id is not None:
            os.environ[_ENV_DOMAIN] = update.ros_domain_id.strip()
        if update.rmw_implementation is not None:
            self._set_or_clear(_ENV_RMW, update.rmw_implementation)
        if update.ros_discovery_server is not None:
            self._set_or_clear(_ENV_DISCOVERY, update.ros_discovery_server)
        if update.expected_nodes is not None:
            self._settings.expected_nodes = update.expected_nodes.strip()
        if update.expected_topics is not None:
            self._settings.expected_topics = update.expected_topics.strip()
        if update.ros_log_dir is not None and update.ros_log_dir.strip():
            self._settings.ros_log_dir = Path(update.ros_log_dir.strip())

        return self.get_config()

    def test(self) -> ConnectionProbe:
        """Verifica la connessione interrogando il grafo con la config corrente.

        Returns:
            L'esito con disponibilita' della CLI e i nodi attualmente rilevati.
        """
        result = self._runner.run(["node", "list"])
        if not result.ok:
            detail = result.stderr.strip() or "Comando 'ros2 node list' fallito."
            return ConnectionProbe(available=False, node_count=0, detail=detail)
        nodes = sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})
        detail = (
            f"Rilevati {len(nodes)} nodi nel grafo."
            if nodes
            else "Connessione riuscita ma nessun nodo presente nel grafo."
        )
        return ConnectionProbe(
            available=True,
            node_count=len(nodes),
            nodes=nodes,
            detail=detail,
        )

    def discover(self) -> ConnectionDiscovery:
        """Rileva i nodi e i topic presenti nel grafo con la config corrente.

        Permette alla UI di popolare i nodi/topic attesi a partire da cio' che e'
        realmente presente nel grafo, invece di digitarli manualmente.

        Returns:
            I nodi e i topic rilevati, oppure ``available=False`` se la CLI
            ``ros2`` non e' disponibile.
        """
        node_result = self._runner.run(["node", "list"])
        if not node_result.ok:
            detail = node_result.stderr.strip() or "Comando 'ros2 node list' fallito."
            return ConnectionDiscovery(available=False, detail=detail)

        nodes = self._parse_lines(node_result.stdout)
        topic_result = self._runner.run(["topic", "list"])
        topics = self._parse_lines(topic_result.stdout) if topic_result.ok else []
        return ConnectionDiscovery(
            available=True,
            nodes=nodes,
            topics=topics,
            detail=f"Rilevati {len(nodes)} nodi e {len(topics)} topic nel grafo.",
        )

    @staticmethod
    def _parse_lines(output: str) -> list[str]:
        """Estrae i nomi (uno per riga) dall'output di un comando ``ros2``.

        Args:
            output: Standard output del comando.

        Returns:
            Lista ordinata e deduplicata dei nomi non vuoti.
        """
        return sorted({line.strip() for line in output.splitlines() if line.strip()})

    @staticmethod
    def _set_or_clear(key: str, value: str) -> None:
        """Imposta una variabile d'ambiente o la rimuove se il valore e' vuoto.

        Args:
            key: Nome della variabile d'ambiente.
            value: Valore da impostare; se vuoto/spazi la variabile viene rimossa.
        """
        cleaned = value.strip()
        if cleaned:
            os.environ[key] = cleaned
        else:
            os.environ.pop(key, None)
