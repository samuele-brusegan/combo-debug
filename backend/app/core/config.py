"""Configurazione centralizzata dell'applicazione.

Tutta la configurazione e' esposta tramite un singolo oggetto immutabile
`Settings`, caricato dalle variabili d'ambiente. Questo evita che i singoli
moduli leggano `os.environ` sparpagliato (Single Responsibility) e rende la
configurazione facilmente sostituibile nei test.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Impostazioni runtime del backend.

    Gli attributi possono essere sovrascritti tramite variabili d'ambiente con
    prefisso ``COMBO_DEBUG_`` (es. ``COMBO_DEBUG_ROS_LOG_DIR``).

    Attributes:
        app_name: Nome leggibile dell'applicazione.
        api_prefix: Prefisso comune a tutte le route REST.
        ros_log_dir: Cartella radice dei log ROS 2 da analizzare.
        ros_command_timeout: Timeout (secondi) per ogni SysCall alla CLI ros2.
        topic_hz_window: Durata (secondi) della finestra di misura di `ros2 topic hz`.
        topic_hz_attempts: Numero di tentativi di misura per topic. Una misura puo'
            fallire in modo transitorio (finestra troppo corta per catturare
            abbastanza messaggi): si ritenta prima di dichiarare il topic "sotto
            soglia", evitando falsi positivi sui topic sani.
        expected_topics: Topic attesi usati dall'euristica di nodo bloccato,
            nel formato ``topic=frequenza_minima_hz`` separati da virgola.
        expected_nodes: Nodi che ci si aspetta siano sempre presenti nel grafo.
            Se uno di questi e' assente viene mostrato in ROSSO (crashato/offline).
            Elenco separato da virgola.
        cors_origins: Origini consentite per le richieste CORS del frontend.
        start_demo: ``True`` se i nodi ROS 2 di esempio sono stati avviati nel
            container (variabile ``COMBO_DEBUG_START_DEMO``). Usato per segnalare
            in dashboard la "Modalita' DEMO".
        boot_ros_domain_id: ``ROS_DOMAIN_ID`` rilevato all'avvio del processo,
            cioe' il dominio su cui girano i nodi demo. Confrontato col dominio
            corrente per capire se si sta ancora osservando la demo.
    """

    model_config = SettingsConfigDict(env_prefix="COMBO_DEBUG_", env_file=None)

    app_name: str = "Combo-Debug"
    api_prefix: str = "/api"
    ros_log_dir: Path = Path.home() / ".ros" / "log"
    ros_command_timeout: float = 8.0
    topic_hz_window: float = 6.0
    topic_hz_attempts: int = 2
    expected_topics: str = "/chatter=0.5,/heartbeat=1.0"
    expected_nodes: str = "/talker,/listener,/stuck_spinner,/crasher"
    cors_origins: list[str] = ["*"]
    start_demo: bool = True
    boot_ros_domain_id: str = Field(
        default_factory=lambda: os.environ.get("ROS_DOMAIN_ID", "0")
    )

    def parse_expected_nodes(self) -> list[str]:
        """Restituisce l'elenco dei nomi dei nodi attesi.

        Returns:
            Lista dei nomi dei nodi attesi, ripulita da spazi e voci vuote.
        """
        return [name.strip() for name in self.expected_nodes.split(",") if name.strip()]

    def parse_expected_topics(self) -> dict[str, float]:
        """Converte ``expected_topics`` in una mappa topic -> frequenza minima.

        Returns:
            Dizionario che associa ad ogni topic atteso la sua frequenza minima
            accettabile in Hz. Le voci malformate vengono ignorate.
        """
        result: dict[str, float] = {}
        for raw in self.expected_topics.split(","):
            entry = raw.strip()
            if not entry or "=" not in entry:
                continue
            topic, _, freq = entry.partition("=")
            try:
                result[topic.strip()] = float(freq.strip())
            except ValueError:
                continue
        return result


@lru_cache
def get_settings() -> Settings:
    """Restituisce l'istanza singleton delle impostazioni.

    L'uso di ``lru_cache`` implementa un singleton leggero: la configurazione
    viene letta una sola volta e riutilizzata da tutta l'applicazione.

    Returns:
        L'oggetto `Settings` condiviso.
    """
    return Settings()
