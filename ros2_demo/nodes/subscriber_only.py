"""Nodo demo 'subscriber_only': subscriber senza publisher (giallo per assenza di publisher).

Rappresenta un subscriber senza publisher: il topic /chatter_no_pub rimane nel grafo
ma nessun publisher ci scrive, quindi appare GIALLO nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SubscriberOnly(Node):
    """Subscriber di messaggi testuali su /chatter_no_pub senza publisher."""

    def __init__(self) -> None:
        """Inizializza il nodo e il subscriber."""
        super().__init__("subscriber_only")
        self._subscriber = self.create_subscription(String, "chatter_no_pub", self._on_message, 10)
        self.get_logger().info("SubscriberOnly avviato: ascolto /chatter_no_pub (nessun publisher).")

    def _on_message(self, message: String) -> None:
        """Callback del messaggio: logga il contenuto."""
        self.get_logger().info(f"Ricevuto: {message.data}")


def main() -> None:
    """Punto di ingresso del nodo subscriber_only."""
    rclpy.init()
    node = SubscriberOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
