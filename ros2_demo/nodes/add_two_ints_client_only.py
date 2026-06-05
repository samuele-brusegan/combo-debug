"""Nodo demo 'add_two_ints_client_only': client senza server (zombie per assenza di publisher).

Rappresenta un client senza server: il servizio /add_two_ints_no_pub rimane nel grafo
ma nessun server risponde, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsClientOnly(Node):
    """Client per il servizio AddTwoInts senza server."""

    def __init__(self) -> None:
        """Inizializza il nodo, il client e il timer."""
        super().__init__("add_two_ints_client_only")
        self._client = self.create_client(AddTwoInts, "add_two_ints_no_pub")
        self._counter = 0
        self.create_timer(2.0, self._on_timer)
        self.get_logger().info("AddTwoIntsClientOnly avviato: attendo servizio /add_two_ints_no_pub (nessun server)...")

    def _on_timer(self) -> None:
        """Callback del timer: invia una richiesta."""
        if not self._client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Servizio /add_two_ints_no_pub non disponibile, riprovo...")
            return

        request = AddTwoInts.Request()
        request.a = self._counter
        request.b = self._counter + 1
        self._counter += 1

        future = self._client.call_async(request)
        future.add_done_callback(self._on_response)

    def _on_response(self, future) -> None:
        """Callback della risposta."""
        try:
            response = future.result()
            self.get_logger().info(f"Risposta: {response.sum}")
        except Exception as e:
            self.get_logger().error(f"Errore nella risposta: {e}")


def main() -> None:
    """Punto di ingresso del nodo add_two_ints_client_only."""
    rclpy.init()
    node = AddTwoIntsClientOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
