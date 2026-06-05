"""Nodo demo 'fibonacci_client': client azione sano per /fibonacci.

Rappresenta un client azione sano: invia goal periodici, quindi appare VERDE nella
dashboard e l'azione /fibonacci risulta attiva.
"""

from __future__ import annotations

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from example_interfaces.action import Fibonacci


class FibonacciClient(Node):
    """Client per l'azione Fibonacci."""

    def __init__(self) -> None:
        """Inizializza il nodo, il client azione e il timer."""
        super().__init__("fibonacci_client")
        self._action_client = ActionClient(self, Fibonacci, "fibonacci")
        self._counter = 0
        self.create_timer(5.0, self._on_timer)
        self.get_logger().info("FibonacciClient avviato: attendo azione /fibonacci...")

    def _on_timer(self) -> None:
        """Callback del timer: invia un goal."""
        if not self._action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("Azione /fibonacci non disponibile, riprovo...")
            return

        goal_msg = Fibonacci.Goal()
        goal_msg.order = 5 + (self._counter % 5)
        self._counter += 1

        self.get_logger().info(f"Invio goal: order={goal_msg.order}")
        self._action_client.send_goal_async(goal_msg)


def main() -> None:
    """Punto di ingresso del nodo fibonacci_client."""
    rclpy.init()
    node = FibonacciClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
