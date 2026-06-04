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
