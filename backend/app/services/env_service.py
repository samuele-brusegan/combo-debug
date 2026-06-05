"""Servizio di ispezione delle variabili d'ambiente ROS (requisito 2).

Espone le variabili d'ambiente rilevanti per il debug della configurazione di
rete/DDS di ROS 2 (es. ``ROS_DOMAIN_ID``, ``RMW_IMPLEMENTATION``, ...).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from app.models.schemas import EnvVariable

# Prefissi delle variabili considerate pertinenti all'ecosistema ROS 2 / DDS.
_RELEVANT_PREFIXES: tuple[str, ...] = (
    "ROS",
    "RMW",
    "AMENT",
    "COLCON",
    "RCUTILS",
    "RCL",
    "CYCLONEDDS",
    "FASTRTPS",
    "FASTDDS",
)

# Variabili che definiscono *quale* grafo ROS viene osservato. Devono sempre
# riflettere la connessione attiva: la riconfigurazione a caldo le scrive in
# ``os.environ`` (vedi ConnectionService), che e' anche la sorgente letta qui,
# quindi il pannello mostra sempre il ROS collegato e non i valori della demo.
# Per ciascuna indichiamo il valore *effettivo* usato dai comandi ``ros2`` se la
# variabile non e' impostata, cosi' la voce e' sempre presente e non ambigua.
_CONNECTION_EFFECTIVE_DEFAULTS: dict[str, str] = {
    "ROS_DOMAIN_ID": "0",
}


class EnvService:
    """Estrae le variabili d'ambiente ROS dal processo corrente.

    Poiche' il backend gira nello stesso container dei nodi ROS, l'ambiente del
    processo coincide con quello in cui i nodi sono stati avviati.
    """

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        """Inizializza il servizio.

        Args:
            environ: Mappa delle variabili d'ambiente. Se ``None`` viene usato
                ``os.environ``. L'iniezione facilita i test deterministici.
        """
        self._environ = environ if environ is not None else os.environ

    def get_ros_variables(self) -> list[EnvVariable]:
        """Restituisce le variabili d'ambiente pertinenti a ROS 2.

        I valori sono letti live da ``os.environ``: poiche' la riconfigurazione
        a caldo della connessione vi scrive i parametri DDS, il risultato
        riflette sempre il ROS *attualmente collegato* (non i valori della demo).
        Le variabili che definiscono la connessione sono sempre presenti, col
        valore effettivo usato dai comandi ``ros2`` quando non impostate.

        Returns:
            Lista ordinata per chiave delle variabili rilevanti.
        """
        values: dict[str, str] = {
            key: value
            for key, value in self._environ.items()
            if key.upper().startswith(_RELEVANT_PREFIXES)
        }
        for key, default in _CONNECTION_EFFECTIVE_DEFAULTS.items():
            if key not in values:
                values[key] = self._environ.get(key, default)
        variables = [EnvVariable(key=key, value=value) for key, value in values.items()]
        return sorted(variables, key=lambda item: item.key)
