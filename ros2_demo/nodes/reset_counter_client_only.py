"""Nodo demo 'reset_counter_client_only': client senza server (zombie per assenza di publisher).

Rappresenta un client senza server: il servizio /reset_counter_no_pub rimane nel grafo
ma nessun server risponde, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class ResetCounterClientOnly(Node):
    """Client per il servizio ResetCounter senza server."""

    def __init__(self) -> None:
        """Inizializza il nodo, il client e il timer."""
        super().__init__("reset_counter_client_only")
        self._client = self.create_client(Trigger, "reset_counter_no_pub")
        self._counter = 0
        self.create_timer(3.0, self._on_timer)
        self.get_logger().info("ResetCounterClientOnly avviato: attendo servizio /reset_counter_no_pub (nessun server)...")

    def _on_timer(self) -> None:
        """Callback del timer: invia una richiesta."""
        if not self._client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Servizio /reset_counter_no_pub non disponibile, riprovo...")
            return

        request = Trigger.Request()
        future = self._client.call_async(request)
        future.add_done_callback(self._on_response)

    def _on_response(self, future) -> None:
        """Callback della risposta."""
        try:
            response = future.result()
            self.get_logger().info(f"Risposta: {response.message}")
        except Exception as e:
            self.get_logger().error(f"Errore nella risposta: {e}")


def main() -> None:
    """Punto di ingresso del nodo reset_counter_client_only."""
    rclpy.init()
    node = ResetCounterClientOnly()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
