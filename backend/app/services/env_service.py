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

        Returns:
            Lista ordinata per chiave delle variabili il cui nome inizia con
            uno dei prefissi rilevanti.
        """
        variables = [
            EnvVariable(key=key, value=value)
            for key, value in self._environ.items()
            if key.upper().startswith(_RELEVANT_PREFIXES)
        ]
        return sorted(variables, key=lambda item: item.key)
