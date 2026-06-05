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
        expected_topics: Topic attesi indicati dalla UI di connessione, nel
            formato ``topic=frequenza_minima_hz`` separati da virgola (memorizzati
            per comodita' dell'utente).
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


@lru_cache
def get_settings() -> Settings:
    """Restituisce l'istanza singleton delle impostazioni.

    L'uso di ``lru_cache`` implementa un singleton leggero: la configurazione
    viene letta una sola volta e riutilizzata da tutta l'applicazione.

    Returns:
        L'oggetto `Settings` condiviso.
    """
    return Settings()
