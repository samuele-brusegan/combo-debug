"""Servizio di ispezione del grafo ROS 2: topic, servizi e azioni.

Costruisce un quadro completo del grafo aggregando l'output di
``ros2 node info`` su tutti i nodi attivi e incrociandolo con gli elenchi
``ros2 topic/service/action list``. Da questo incrocio deriva il rilevamento
degli **zombie**: un'entita' (topic, servizio o azione) ancora presente nella
discovery DDS ma che nessun nodo attivo usa piu' (tutti i publisher/server, o
client, associati sono crashati lasciando endpoint fantasma).

Regole di stato (vedi `EntityStatus`):
    * Almeno un produttore attivo (publisher/server)  -> VERDE.
    * Solo consumatori attivi (subscriber/client)     -> GIALLO (produttore
      mancante/crashato, l'entita' resta "in attesa").
    * Nessun nodo attivo associato ma ancora nel grafo -> ZOMBIE.

Come gli altri service dipende dall'astrazione `RosCommandRunner`, quindi e'
testabile senza un'installazione ROS reale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import (
    EntityStatus,
    GraphEntity,
    GraphEntityKind,
    GraphSnapshot,
)
from app.services.diagnostics_monitor import (
    LISTENER_NODE_NAME as DIAGNOSTICS_LISTENER_NODE_NAME,
)
from app.services.rosout_monitor import LISTENER_NODE_NAME
from app.services.tf_monitor import LISTENER_NODE_NAME as TF_LISTENER_NODE_NAME

# Nodi di servizio interni del backend, da escludere dall'aggregazione del grafo.
_INTERNAL_LISTENER_NODES: frozenset[str] = frozenset(
    {LISTENER_NODE_NAME, DIAGNOSTICS_LISTENER_NODE_NAME, TF_LISTENER_NODE_NAME}
)

# Intestazioni delle sezioni di ``ros2 node info`` mappate sul ruolo che il
# nodo svolge per ciascuna entita' del grafo.
_TOPIC_PRODUCER = "Publishers:"
_TOPIC_CONSUMER = "Subscribers:"
_SERVICE_PRODUCER = "Service Servers:"
_SERVICE_CONSUMER = "Service Clients:"
_ACTION_PRODUCER = "Action Servers:"
_ACTION_CONSUMER = "Action Clients:"
_SECTION_HEADERS = frozenset(
    {
        _TOPIC_PRODUCER,
        _TOPIC_CONSUMER,
        _SERVICE_PRODUCER,
        _SERVICE_CONSUMER,
        _ACTION_PRODUCER,
        _ACTION_CONSUMER,
    }
)

# Servizi standard esposti automaticamente da ogni nodo per la gestione dei
# parametri: sono sempre "sani" (serviti dal nodo stesso) e renderebbero solo
# rumoroso l'elenco, quindi li filtriamo dalla vista dei servizi.
_DEFAULT_PARAMETER_SERVICE_SUFFIXES: tuple[str, ...] = (
    "/describe_parameters",
    "/get_parameter_types",
    "/get_parameters",
    "/list_parameters",
    "/set_parameters",
    "/set_parameters_atomically",
)


@dataclass
class _Endpoints:
    """Insiemi di nodi attivi che producono/consumano una data entita'.

    Attributes:
        producers: Nodi attivi che producono (publisher / server).
        consumers: Nodi attivi che consumano (subscriber / client).
        entity_type: Tipo (messaggio/servizio/azione) come riportato dal grafo.
    """

    producers: set[str] = field(default_factory=set)
    consumers: set[str] = field(default_factory=set)
    entity_type: str = ""


class GraphService:
    """Rileva topic, servizi e azioni del grafo ROS 2 e ne valuta lo stato."""

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per eseguire i comandi ros2.
            settings: Configurazione applicativa.
        """
        self._runner = runner
        self._settings = settings

    def get_snapshot(self) -> GraphSnapshot:
        """Costruisce la fotografia completa del grafo (topic/servizi/azioni).

        Esegue una sola volta l'aggregazione di ``ros2 node info`` sui nodi
        attivi e la riusa per i tre elenchi, evitando interrogazioni ripetute.

        Returns:
            Uno `GraphSnapshot` con topic, servizi e azioni e il loro stato.
        """
        active_nodes = self._active_node_names()

        topics: dict[str, _Endpoints] = {}
        services: dict[str, _Endpoints] = {}
        actions: dict[str, _Endpoints] = {}
        for node in active_nodes:
            self._collect_node_endpoints(node, topics, services, actions)

        topic_names = self._list_names(["topic", "list"])
        service_names = self._without_default_parameter_services(
            self._list_names(["service", "list"])
        )
        action_names = self._list_names(["action", "list"])

        # I servizi parametro standard vanno esclusi sia dall'elenco sia dagli
        # endpoint aggregati (altrimenti rientrerebbero dall'unione dei nomi).
        services = {
            name: ep
            for name, ep in services.items()
            if not name.endswith(_DEFAULT_PARAMETER_SERVICE_SUFFIXES)
        }

        return GraphSnapshot(
            topics=self._build_entities(
                GraphEntityKind.TOPIC, topic_names, topics, "publisher", "subscriber"
            ),
            services=self._build_entities(
                GraphEntityKind.SERVICE,
                service_names,
                services,
                "server",
                "client",
            ),
            actions=self._build_entities(
                GraphEntityKind.ACTION, action_names, actions, "server", "client"
            ),
        )

    # -- Raccolta dati -------------------------------------------------------

    def _active_node_names(self) -> list[str]:
        """Restituisce i nomi dei nodi attivi nel grafo (senza slash iniziale).

        Returns:
            Lista deduplicata dei nodi attivi, escluso il nodo di servizio
            interno che ascolta ``/rosout``.
        """
        result = self._runner.run(["node", "list"])
        if not result.ok:
            return []
        excluded = {
            name
            for listener in _INTERNAL_LISTENER_NODES
            for name in (f"/{listener}", listener)
        }
        return sorted(
            {
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and line.strip() not in excluded
            }
        )

    def _collect_node_endpoints(
        self,
        node: str,
        topics: dict[str, _Endpoints],
        services: dict[str, _Endpoints],
        actions: dict[str, _Endpoints],
    ) -> None:
        """Interroga ``ros2 node info`` per un nodo e aggiorna gli endpoint.

        Args:
            node: Nome del nodo da interrogare.
            topics: Mappa (mutata) topic -> endpoint attivi.
            services: Mappa (mutata) servizio -> endpoint attivi.
            actions: Mappa (mutata) azione -> endpoint attivi.
        """
        result = self._runner.run(
            ["node", "info", node], timeout=self._settings.ros_command_timeout
        )
        if not result.ok:
            return
        node_name = node.lstrip("/")
        for section, name, entity_type in self._parse_node_info(result.stdout):
            target, is_producer = self._target_for_section(
                section, topics, services, actions
            )
            if target is None:
                continue
            endpoints = target.setdefault(name, _Endpoints())
            (endpoints.producers if is_producer else endpoints.consumers).add(node_name)
            if entity_type and not endpoints.entity_type:
                endpoints.entity_type = entity_type

    @staticmethod
    def _target_for_section(
        section: str,
        topics: dict[str, _Endpoints],
        services: dict[str, _Endpoints],
        actions: dict[str, _Endpoints],
    ) -> tuple[dict[str, _Endpoints] | None, bool]:
        """Mappa l'intestazione di sezione alla mappa target e al ruolo.

        Args:
            section: Intestazione di sezione (es. ``Publishers:``).
            topics: Mappa dei topic.
            services: Mappa dei servizi.
            actions: Mappa delle azioni.

        Returns:
            La coppia ``(mappa, is_producer)``; ``(None, False)`` se la sezione
            non e' di interesse.
        """
        mapping: dict[str, tuple[dict[str, _Endpoints], bool]] = {
            _TOPIC_PRODUCER: (topics, True),
            _TOPIC_CONSUMER: (topics, False),
            _SERVICE_PRODUCER: (services, True),
            _SERVICE_CONSUMER: (services, False),
            _ACTION_PRODUCER: (actions, True),
            _ACTION_CONSUMER: (actions, False),
        }
        if section in mapping:
            target, is_producer = mapping[section]
            return target, is_producer
        return None, False

    @staticmethod
    def _parse_node_info(text: str) -> list[tuple[str, str, str]]:
        """Estrae le voci di ``ros2 node info`` raggruppate per sezione.

        Riconosce le intestazioni note (Publishers/Subscribers/Service.../
        Action...) e le voci indentate sottostanti, tollerando sia il formato
        ``/nome: tipo`` sia ``/nome [tipo]``.

        Args:
            text: Standard output di ``ros2 node info <nodo>``.

        Returns:
            Lista di triple ``(intestazione_sezione, nome_entita', tipo)``.
        """
        entries: list[tuple[str, str, str]] = []
        current: str | None = None
        for raw in text.splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            header = line.strip()
            if header in _SECTION_HEADERS:
                current = header
                continue
            # Le voci sono indentate; una riga non indentata (es. il nome del
            # nodo) chiude la sezione corrente.
            if not (raw.startswith(" ") or raw.startswith("\t")):
                current = None
                continue
            if current is None:
                continue
            name, entity_type = GraphService._parse_entry(line.strip())
            if name:
                entries.append((current, name, entity_type))
        return entries

    @staticmethod
    def _parse_entry(entry: str) -> tuple[str, str]:
        """Estrae nome e tipo da una singola voce di ``ros2 node info``.

        Args:
            entry: Voce gia' ripulita (es. ``/chatter: std_msgs/msg/String``).

        Returns:
            La coppia ``(nome, tipo)``; il tipo e' stringa vuota se assente.
        """
        token = entry.split()[0] if entry.split() else ""
        name = token.rstrip(":")
        entity_type = entry[len(token) :].strip().strip(":").strip().strip("[]").strip()
        return name, entity_type

    def _list_names(self, args: list[str]) -> list[str]:
        """Esegue un comando ``ros2 ... list`` e ne estrae i nomi.

        Args:
            args: Argomenti del comando (es. ``["topic", "list"]``).

        Returns:
            Lista deduplicata dei nomi non vuoti; vuota se il comando fallisce.
        """
        result = self._runner.run(args)
        if not result.ok:
            return []
        return sorted(
            {line.strip() for line in result.stdout.splitlines() if line.strip()}
        )

    @staticmethod
    def _without_default_parameter_services(names: list[str]) -> list[str]:
        """Rimuove i servizi parametro standard (rumore) dall'elenco servizi.

        Args:
            names: Nomi dei servizi rilevati.

        Returns:
            I servizi privi dei tipici servizi di gestione parametri.
        """
        return [
            name
            for name in names
            if not name.endswith(_DEFAULT_PARAMETER_SERVICE_SUFFIXES)
        ]

    # -- Valutazione dello stato --------------------------------------------

    def _build_entities(
        self,
        kind: GraphEntityKind,
        listed: list[str],
        endpoints: dict[str, _Endpoints],
        producer_label: str,
        consumer_label: str,
    ) -> list[GraphEntity]:
        """Combina elenco e endpoint attivi in entita' con stato valutato.

        Args:
            kind: Tipo di entita' (topic/servizio/azione).
            listed: Nomi rilevati da ``ros2 ... list``.
            endpoints: Endpoint attivi raccolti da ``ros2 node info``.
            producer_label: Etichetta del produttore (es. ``publisher``).
            consumer_label: Etichetta del consumatore (es. ``subscriber``).

        Returns:
            Lista ordinata di `GraphEntity`, una per entita' osservata o attesa.
        """
        names = sorted(set(listed) | set(endpoints))
        entities: list[GraphEntity] = []
        for name in names:
            info = endpoints.get(name, _Endpoints())
            producers = sorted(info.producers)
            consumers = sorted(info.consumers)
            status, reason = self._evaluate(
                producers, consumers, producer_label, consumer_label
            )
            entities.append(
                GraphEntity(
                    name=name,
                    kind=kind,
                    status=status,
                    entity_type=info.entity_type,
                    producers=producers,
                    consumers=consumers,
                    reason=reason,
                )
            )
        return entities

    @staticmethod
    def _evaluate(
        producers: list[str],
        consumers: list[str],
        producer_label: str,
        consumer_label: str,
    ) -> tuple[EntityStatus, str]:
        """Deriva stato e motivazione dagli endpoint attivi di un'entita'.

        Args:
            producers: Nodi attivi produttori.
            consumers: Nodi attivi consumatori.
            producer_label: Etichetta del produttore (per il messaggio).
            consumer_label: Etichetta del consumatore (per il messaggio).

        Returns:
            La coppia ``(stato, motivazione)``.
        """
        if producers:
            return (
                EntityStatus.GREEN,
                f"{len(producers)} {producer_label} attivo/i: {', '.join(producers)}.",
            )
        if consumers:
            return (
                EntityStatus.YELLOW,
                f"Nessun {producer_label} attivo: solo {len(consumers)} "
                f"{consumer_label} in attesa ({', '.join(consumers)}).",
            )
        return (
            EntityStatus.ZOMBIE,
            f"Zombie: presente nel grafo ma nessun {producer_label}/"
            f"{consumer_label} attivo (tutti gli endpoint associati crashati).",
        )
