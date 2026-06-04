"""Nodo demo 'talker': pubblica su /chatter a 1 Hz.

Rappresenta un nodo sano: pubblica regolarmente, quindi appare VERDE nella
dashboard e il topic /chatter risulta a frequenza adeguata.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    """Pubblicatore periodico di messaggi testuali su /chatter."""

    def __init__(self) -> None:
        """Inizializza il nodo, il publisher e il timer a 1 Hz."""
        super().__init__("talker")
        self._publisher = self.create_publisher(String, "chatter", 10)
        self._counter = 0
        self.create_timer(1.0, self._on_timer)
        self.get_logger().info("Talker avviato: pubblico su /chatter a 1 Hz.")

    def _on_timer(self) -> None:
        """Callback del timer: pubblica un messaggio incrementale."""
        message = String()
        message.data = f"hello world {self._counter}"
        self._publisher.publish(message)
        self.get_logger().info(f"Pubblicato: {message.data}")
        self._counter += 1


def main() -> None:
    """Punto di ingresso del nodo talker."""
    rclpy.init()
    node = Talker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
