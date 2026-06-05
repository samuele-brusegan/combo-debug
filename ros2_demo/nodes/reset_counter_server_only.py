"""Nodo demo 'reset_counter_server_only': server senza client (zombie per assenza di subscriber).

Rappresenta un server senza client: il servizio /reset_counter_no_sub rimane nel grafo
ma nessun client lo usa, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class ResetCounterServerOnly(Node):
    """Server per il servizio ResetCounter senza client."""

    def __init__(self) -> None:
        """Inizializza il nodo, il server e il contatore."""
        super().__init__("reset_counter_server_only")
        self._counter = 0
        self._server = self.create_service(Trigger, "reset_counter_no_sub", self._on_request)
        self.get_logger().info("ResetCounterServerOnly avviato: servizio /reset_counter_no_sub disponibile (nessun client).")

    def _on_request(self, request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        """Callback del servizio: resetta il contatore."""
        self._counter = 0
        response.success = True
        response.message = "Contatore resettato."
        self.get_logger().info("Contatore resettato.")
        return response


def main() -> None:
    """Punto di ingresso del nodo reset_counter_server_only."""
    rclpy.init()
    node = ResetCounterServerOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
