"""Nodo demo 'add_two_ints_server': server sano per /add_two_ints.

Rappresenta un server sano: risponde alle richieste, quindi appare VERDE nella
dashboard e il servizio /add_two_ints risulta attivo.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsServer(Node):
    """Server per il servizio AddTwoInts."""

    def __init__(self) -> None:
        """Inizializza il nodo e il server."""
        super().__init__("add_two_ints_server")
        self._server = self.create_service(AddTwoInts, "add_two_ints", self._on_request)
        self.get_logger().info("AddTwoIntsServer avviato: servizio /add_two_ints disponibile.")

    def _on_request(self, request: AddTwoInts.Request, response: AddTwoInts.Response) -> AddTwoInts.Response:
        """Callback del servizio: somma i due interi."""
        response.sum = request.a + request.b
        self.get_logger().info(f"Richiesta: {request.a} + {request.b} = {response.sum}")
        return response


def main() -> None:
    """Punto di ingresso del nodo add_two_ints_server."""
    rclpy.init()
    node = AddTwoIntsServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
