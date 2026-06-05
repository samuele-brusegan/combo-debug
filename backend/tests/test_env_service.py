"""Test del servizio delle variabili d'ambiente ROS.

Verifica in particolare che le variabili riflettano sempre la connessione
corrente (lettura live dell'ambiente), non valori "congelati" della demo.
"""

from __future__ import annotations

from app.services.env_service import EnvService


def test_filters_only_ros_relevant_variables() -> None:
    """Restituisce solo le variabili pertinenti a ROS/DDS."""
    service = EnvService(
        environ={
            "ROS_DOMAIN_ID": "5",
            "RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp",
            "PATH": "/usr/bin",
            "HOME": "/root",
        }
    )
    result = {v.key: v.value for v in service.get_ros_variables()}
    assert result["ROS_DOMAIN_ID"] == "5"
    assert result["RMW_IMPLEMENTATION"] == "rmw_cyclonedds_cpp"
    assert "PATH" not in result
    assert "HOME" not in result


def test_reflects_live_connection_changes() -> None:
    """Le variabili seguono i cambi di connessione (lettura live dell'ambiente).

    Simula la riconfigurazione a caldo: il ConnectionService scrive i nuovi
    parametri DDS nell'ambiente, e l'EnvService (che legge la stessa mappa) deve
    riportarli subito, senza restare sui valori iniziali della demo.
    """
    environ: dict[str, str] = {"ROS_DOMAIN_ID": "1", "RMW_IMPLEMENTATION": "rmw_fastrtps_cpp"}
    service = EnvService(environ=environ)

    assert {v.key: v.value for v in service.get_ros_variables()}["ROS_DOMAIN_ID"] == "1"

    # Collegamento a un ROS reale: cambia il dominio nell'ambiente condiviso.
    environ["ROS_DOMAIN_ID"] = "42"
    environ["ROS_DISCOVERY_SERVER"] = "192.168.1.10:11811"

    updated = {v.key: v.value for v in service.get_ros_variables()}
    assert updated["ROS_DOMAIN_ID"] == "42"
    assert updated["ROS_DISCOVERY_SERVER"] == "192.168.1.10:11811"


def test_domain_id_always_present_with_effective_default() -> None:
    """``ROS_DOMAIN_ID`` e' sempre mostrato col valore effettivo (0 se assente)."""
    service = EnvService(environ={"RMW_IMPLEMENTATION": "rmw_fastrtps_cpp"})
    result = {v.key: v.value for v in service.get_ros_variables()}
    assert result["ROS_DOMAIN_ID"] == "0"
