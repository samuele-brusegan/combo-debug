"""Nodo demo 'listener': sottoscrive /chatter.

Nodo sano consumatore: resta in ascolto su /chatter e logga i messaggi
ricevuti. Appare VERDE nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    """Sottoscrittore dei messaggi pubblicati su /chatter."""

    def __init__(self) -> None:
        """Inizializza il nodo e la subscription a /chatter."""
        super().__init__("listener")
        self._subscription = self.create_subscription(
            String, "chatter", self._on_message, 10
        )
        self.get_logger().info("Listener avviato: ascolto su /chatter.")

    def _on_message(self, message: String) -> None:
        """Callback di ricezione messaggi.

        Args:
            message: Messaggio ricevuto dal topic /chatter.
        """
        self.get_logger().info(f"Ricevuto: {message.data}")


def main() -> None:
    """Punto di ingresso del nodo listener."""
    rclpy.init()
    node = Listener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
