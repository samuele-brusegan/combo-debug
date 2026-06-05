"""Nodo demo 'fibonacci_client_only': client azione senza server (zombie per assenza di publisher).

Rappresenta un client azione senza server: l'azione /fibonacci_no_pub rimane nel grafo
ma nessun server risponde, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from example_interfaces.action import Fibonacci


class FibonacciClientOnly(Node):
    """Client per l'azione Fibonacci senza server."""

    def __init__(self) -> None:
        """Inizializza il nodo, il client azione e il timer."""
        super().__init__("fibonacci_client_only")
        self._action_client = ActionClient(self, Fibonacci, "fibonacci_no_pub")
        self._counter = 0
        self.create_timer(5.0, self._on_timer)
        self.get_logger().info("FibonacciClientOnly avviato: attendo azione /fibonacci_no_pub (nessun server)...")

    def _on_timer(self) -> None:
        """Callback del timer: invia un goal."""
        if not self._action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("Azione /fibonacci_no_pub non disponibile, riprovo...")
            return

        goal_msg = Fibonacci.Goal()
        goal_msg.order = 5 + (self._counter % 5)
        self._counter += 1

        self.get_logger().info(f"Invio goal: order={goal_msg.order}")
        self._action_client.send_goal_async(goal_msg)


def main() -> None:
    """Punto di ingresso del nodo fibonacci_client_only."""
    rclpy.init()
    node = FibonacciClientOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
