"""Nodo demo 'publisher_only': publisher senza subscriber (giallo per assenza di subscriber).

Rappresenta un publisher senza subscriber: il topic /chatter_no_sub rimane nel grafo
ma nessun subscriber lo ascolta, quindi appare GIALLO nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class PublisherOnly(Node):
    """Publisher periodico di messaggi testuali su /chatter_no_sub senza subscriber."""

    def __init__(self) -> None:
        """Inizializza il nodo, il publisher e il timer a 1 Hz."""
        super().__init__("publisher_only")
        self._publisher = self.create_publisher(String, "chatter_no_sub", 10)
        self._counter = 0
        self.create_timer(1.0, self._on_timer)
        self.get_logger().info("PublisherOnly avviato: pubblico su /chatter_no_sub a 1 Hz (nessun subscriber).")

    def _on_timer(self) -> None:
        """Callback del timer: pubblica un messaggio incrementale."""
        message = String()
        message.data = f"hello world {self._counter}"
        self._publisher.publish(message)
        self.get_logger().info(f"Pubblicato: {message.data}")
        self._counter += 1


def main() -> None:
    """Punto di ingresso del nodo publisher_only."""
    rclpy.init()
    node = PublisherOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
