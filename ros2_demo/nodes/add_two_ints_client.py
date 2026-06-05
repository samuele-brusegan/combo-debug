"""Nodo demo 'add_two_ints_client': client sano per /add_two_ints.

Rappresenta un client sano: invia richieste periodiche, quindi appare VERDE nella
dashboard e il servizio /add_two_ints risulta attivo.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts


class AddTwoIntsClient(Node):
    """Client per il servizio AddTwoInts."""

    def __init__(self) -> None:
        """Inizializza il nodo, il client e il timer."""
        super().__init__("add_two_ints_client")
        self._client = self.create_client(AddTwoInts, "add_two_ints")
        self._counter = 0
        self.create_timer(2.0, self._on_timer)
        self.get_logger().info("AddTwoIntsClient avviato: attendo servizio /add_two_ints...")

    def _on_timer(self) -> None:
        """Callback del timer: invia una richiesta."""
        if not self._client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Servizio /add_two_ints non disponibile, riprovo...")
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
    """Punto di ingresso del nodo add_two_ints_client."""
    rclpy.init()
    node = AddTwoIntsClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
