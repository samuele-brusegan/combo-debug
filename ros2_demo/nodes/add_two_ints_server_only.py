"""Nodo demo 'add_two_ints_server_only': server senza client (zombie per assenza di subscriber).

Rappresenta un server senza client: il servizio /add_two_ints_no_sub rimane nel grafo
ma nessun client lo usa, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsServerOnly(Node):
    """Server per il servizio AddTwoInts senza client."""

    def __init__(self) -> None:
        """Inizializza il nodo e il server."""
        super().__init__("add_two_ints_server_only")
        self._server = self.create_service(AddTwoInts, "add_two_ints_no_sub", self._on_request)
        self.get_logger().info("AddTwoIntsServerOnly avviato: servizio /add_two_ints_no_sub disponibile (nessun client).")

    def _on_request(self, request: AddTwoInts.Request, response: AddTwoInts.Response) -> AddTwoInts.Response:
        """Callback del servizio: somma i due interi."""
        response.sum = request.a + request.b
        self.get_logger().info(f"Richiesta: {request.a} + {request.b} = {response.sum}")
        return response


def main() -> None:
    """Punto di ingresso del nodo add_two_ints_server_only."""
    rclpy.init()
    node = AddTwoIntsServerOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
