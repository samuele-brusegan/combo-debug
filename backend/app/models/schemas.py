"""Schemi dati (DTO) condivisi tra service e API.

Questi modelli Pydantic costituiscono il "contratto" pubblico del backend:
sono cio' che il frontend Vanilla JS riceve in formato JSON. Tenerli in un
unico modulo facilita la manutenzione e la generazione automatica di OpenAPI.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """Stato sintetico di un nodo, mappato sul color-coding della dashboard.

    Attributes:
        GREEN: Nodo attivo, presente nel grafo ROS e responsivo.
        RED: Nodo crashato, offline o non raggiungibile.
        YELLOW: Stato sospetto (es. spin potenzialmente bloccato). Usato dalle
            funzionalita' euristiche avanzate, ma resta compatibile con la
            richiesta verde/rosso (il giallo e' un sottocaso di "attenzione").
    """

    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"


class RosNode(BaseModel):
    """Rappresenta un nodo ROS 2 osservato nel grafo.

    Attributes:
        name: Nome completo del nodo (es. ``/talker``).
        status: Stato color-coded del nodo.
        reason: Spiegazione testuale dello stato (utile per il debug).
    """

    name: str
    status: NodeStatus
    reason: str = ""


class EnvVariable(BaseModel):
    """Coppia chiave/valore di una variabile d'ambiente ROS.

    Attributes:
        key: Nome della variabile (es. ``ROS_DOMAIN_ID``).
        value: Valore corrente della variabile.
    """

    key: str
    value: str


class LogLevel(str, Enum):
    """Livello di severita' di una riga di log."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class LogEntry(BaseModel):
    """Singola riga di log analizzata dal parser.

    Attributes:
        level: Severita' classificata della riga.
        message: Contenuto testuale della riga.
        source: File di log di provenienza (relativo alla cartella dei log).
        line_number: Numero di riga all'interno del file di origine.
        timestamp: Istante dell'evento in formato ISO 8601 (``None`` se non
            disponibile). Per i log live proviene dallo ``stamp`` del messaggio
            ``/rosout``; per i file locali non e' valorizzato.
    """

    level: LogLevel
    message: str
    source: str
    line_number: int
    timestamp: str | None = None


class EntityStatus(str, Enum):
    """Stato di un'entita' del grafo (topic, servizio o azione).

    Attributes:
        GREEN: Entita' sana: esiste almeno un produttore attivo (publisher per
            i topic, server per servizi/azioni).
        YELLOW: Esistono solo consumatori attivi (subscriber/client) ma nessun
            produttore: l'entita' e' "in attesa" (produttore mancante/crashato).
        ZOMBIE: L'entita' e' ancora presente nel grafo DDS ma nessun nodo
            attivo la usa: tutti i produttori/consumatori associati sono
            crashati (endpoint fantasma rimasti nella discovery).
    """

    GREEN = "green"
    YELLOW = "yellow"
    ZOMBIE = "zombie"


class GraphEntityKind(str, Enum):
    """Tipo di entita' del grafo ROS 2 rilevata."""

    TOPIC = "topic"
    SERVICE = "service"
    ACTION = "action"


class GraphEntity(BaseModel):
    """Topic, servizio o azione osservato nel grafo ROS 2.

    Attributes:
        name: Nome completo dell'entita' (es. ``/chatter``).
        kind: Tipo di entita' (topic/servizio/azione).
        status: Stato color-coded (sano / in attesa / zombie).
        entity_type: Tipo del messaggio/servizio/azione, se noto.
        producers: Nodi attivi che producono (publisher / server).
        consumers: Nodi attivi che consumano (subscriber / client).
        reason: Spiegazione testuale dello stato (utile per il debug).
    """

    name: str
    kind: GraphEntityKind
    status: EntityStatus
    entity_type: str = ""
    producers: list[str] = Field(default_factory=list)
    consumers: list[str] = Field(default_factory=list)
    reason: str = ""


class GraphSnapshot(BaseModel):
    """Fotografia del grafo ROS 2: topic, servizi e azioni con il loro stato.

    Aggrega in un'unica risposta i tre elenchi cosi' che la dashboard possa
    popolare i rispettivi pannelli con una sola richiesta.

    Attributes:
        topics: Topic rilevati con il relativo stato.
        services: Servizi rilevati con il relativo stato.
        actions: Azioni rilevate con il relativo stato.
    """

    topics: list[GraphEntity] = Field(default_factory=list)
    services: list[GraphEntity] = Field(default_factory=list)
    actions: list[GraphEntity] = Field(default_factory=list)


class ConnectionConfig(BaseModel):
    """Configurazione runtime della connessione al grafo ROS 2.

    Rappresenta i parametri che determinano *quale* grafo ROS il backend ispeziona
    tramite la CLI ``ros2``. Possono essere modificati a caldo (senza riavviare il
    container) dalla UI: i nuovi valori vengono applicati alle SysCall successive.

    Attributes:
        ros_domain_id: Dominio DDS condiviso (``ROS_DOMAIN_ID``).
        rmw_implementation: Implementazione RMW (``RMW_IMPLEMENTATION``).
        ros_discovery_server: Indirizzo del Discovery Server di Fast DDS
            (``ROS_DISCOVERY_SERVER``); stringa vuota se non usato.
        expected_nodes: Nodi attesi (assenti ⇒ rosso), separati da virgola.
        expected_topics: Topic attesi ``nome=freq_min_hz`` separati da virgola.
        ros_log_dir: Cartella dei log analizzata dal parser.
        demo_mode: ``True`` se la dashboard sta osservando i nodi ROS 2 di
            esempio (demo avviata e dominio ancora quello di boot).
        start_demo: ``True`` se i nodi demo sono stati avviati nel container.
    """

    ros_domain_id: str = "0"
    rmw_implementation: str = ""
    ros_discovery_server: str = ""
    expected_nodes: str = ""
    expected_topics: str = ""
    ros_log_dir: str = ""
    demo_mode: bool = False
    start_demo: bool = False


class ConnectionUpdate(BaseModel):
    """Aggiornamento parziale della configurazione di connessione.

    Tutti i campi sono opzionali: vengono applicati solo quelli valorizzati,
    cosi' la UI puo' inviare anche un sottoinsieme dei parametri.

    Attributes:
        ros_domain_id: Nuovo ``ROS_DOMAIN_ID`` (opzionale).
        rmw_implementation: Nuova ``RMW_IMPLEMENTATION`` (opzionale).
        ros_discovery_server: Nuovo ``ROS_DISCOVERY_SERVER`` (vuoto = rimuovi).
        expected_nodes: Nuovo elenco nodi attesi (opzionale).
        expected_topics: Nuovo elenco topic attesi (opzionale).
        ros_log_dir: Nuova cartella dei log (opzionale).
    """

    ros_domain_id: str | None = None
    rmw_implementation: str | None = None
    ros_discovery_server: str | None = None
    expected_nodes: str | None = None
    expected_topics: str | None = None
    ros_log_dir: str | None = None


class ConnectionProbe(BaseModel):
    """Esito di una verifica della connessione al grafo ROS 2.

    Attributes:
        available: ``True`` se la CLI ``ros2`` e' disponibile ed eseguibile.
        node_count: Numero di nodi rilevati nel grafo con la config corrente.
        nodes: Nomi dei nodi rilevati.
        detail: Messaggio descrittivo dell'esito (utile in caso di errore).
    """

    available: bool
    node_count: int
    nodes: list[str] = Field(default_factory=list)
    detail: str = ""


class ConnectionDiscovery(BaseModel):
    """Nodi e topic rilevati nel grafo ROS 2 con la configurazione corrente.

    Usato dalla UI per popolare i nodi/topic attesi senza digitarli a mano.

    Attributes:
        available: ``True`` se la CLI ``ros2`` e' disponibile ed eseguibile.
        nodes: Nomi dei nodi rilevati nel grafo.
        topics: Nomi dei topic rilevati nel grafo.
        detail: Messaggio descrittivo dell'esito (utile in caso di errore).
    """

    available: bool
    nodes: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    detail: str = ""


class RmwOptions(BaseModel):
    """Implementazioni RMW disponibili per il collegamento al grafo ROS 2.

    Usato dalla UI per popolare il menu a tendina di ``RMW_IMPLEMENTATION`` con
    le RMW realmente installate nel container (cosi' l'utente sceglie tra quelle
    che funzionano davvero, invece di digitarle a rischio di errore).

    Attributes:
        available: Nomi dei pacchetti RMW installati e selezionabili.
        current: RMW attualmente attiva (``RMW_IMPLEMENTATION`` corrente).
        detail: Messaggio descrittivo (es. come aggiungerne di nuove).
    """

    available: list[str] = Field(default_factory=list)
    current: str = ""
    detail: str = ""
