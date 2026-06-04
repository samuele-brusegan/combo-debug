"""Nodo demo 'stuck_spinner': simula uno spin bloccato/lento.

Dovrebbe pubblicare su /heartbeat a 1 Hz, ma simula un blocco dello spin
pubblicando molto piu' lentamente (circa 0.2 Hz). Serve a dimostrare
l'euristica di "Rilevamento Spin Bloccato": il nodo resta presente (quindi
non sparisce dal grafo) ma la frequenza del topic atteso e' troppo bassa,
producendo uno stato GIALLO nel report di salute.
"""

from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class StuckSpinner(Node):
    """Nodo che pubblica su /heartbeat con un ritardo anomalo (spin lento)."""

    def __init__(self) -> None:
        """Inizializza il nodo, il publisher /heartbeat e un timer 'bloccante'."""
        super().__init__("stuck_spinner")
        self._publisher = self.create_publisher(String, "heartbeat", 10)
        # Timer nominale a 1 Hz, ma la callback "blocca" lo spin con una sleep,
        # abbassando di fatto la frequenza effettiva a ~0.2 Hz.
        self.create_timer(1.0, self._on_timer)
        self.get_logger().warn(
            "StuckSpinner avviato: simulo uno spin bloccato su /heartbeat."
        )

    def _on_timer(self) -> None:
        """Callback che blocca volutamente lo spin prima di pubblicare."""
        # Simulazione del blocco: la sleep tiene occupato il thread di spin.
        time.sleep(4.0)
        message = String()
        message.data = "heartbeat (ritardato)"
        self._publisher.publish(message)
        self.get_logger().warn("Heartbeat pubblicato in ritardo (spin bloccato).")


def main() -> None:
    """Punto di ingresso del nodo stuck_spinner."""
    rclpy.init()
    node = StuckSpinner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
