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
    """

    level: LogLevel
    message: str
    source: str
    line_number: int


class TopicHealth(BaseModel):
    """Esito del controllo di frequenza su un topic atteso.

    Attributes:
        topic: Nome del topic monitorato.
        expected_hz: Frequenza minima attesa in Hz.
        measured_hz: Frequenza misurata in Hz (``None`` se non misurabile).
        healthy: ``True`` se la frequenza misurata e' adeguata.
        detail: Descrizione testuale dell'esito.
    """

    topic: str
    expected_hz: float
    measured_hz: float | None
    healthy: bool
    detail: str


class HealthReport(BaseModel):
    """Report euristico sullo stato di salute di un nodo / del sistema.

    Attributes:
        node: Nome del nodo a cui il report si riferisce.
        status: Stato complessivo derivato dalle euristiche.
        topics: Esiti dei controlli sui topic attesi.
        notes: Annotazioni aggiuntive prodotte dalle euristiche.
    """

    node: str
    status: NodeStatus
    topics: list[TopicHealth] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


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
