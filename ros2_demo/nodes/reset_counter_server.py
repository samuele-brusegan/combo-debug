"""Nodo demo 'reset_counter_server': server sano per /reset_counter.

Rappresenta un server sano: risponde alle richieste, quindi appare VERDE nella
dashboard e il servizio /reset_counter risulta attivo.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class ResetCounterServer(Node):
    """Server per il servizio ResetCounter."""

    def __init__(self) -> None:
        """Inizializza il nodo, il server e il contatore."""
        super().__init__("reset_counter_server")
        self._counter = 0
        self._server = self.create_service(Trigger, "reset_counter", self._on_request)
        self.get_logger().info("ResetCounterServer avviato: servizio /reset_counter disponibile.")

    def _on_request(self, request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        """Callback del servizio: resetta il contatore."""
        self._counter = 0
        response.success = True
        response.message = "Contatore resettato."
        self.get_logger().info("Contatore resettato.")
        return response


def main() -> None:
    """Punto di ingresso del nodo reset_counter_server."""
    rclpy.init()
    node = ResetCounterServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
