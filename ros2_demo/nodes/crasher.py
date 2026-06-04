"""Nodo demo 'crasher': si avvia e poi crasha dopo alcuni secondi.

Serve a dimostrare lo stato ROSSO della dashboard: il nodo e' incluso tra i
nodi attesi, ma dopo un breve periodo solleva un'eccezione e termina,
sparendo dal grafo ROS. La dashboard lo mostrera' quindi come crashato/offline.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node

# Secondi di vita prima del crash simulato.
_LIFETIME_SECONDS = 15.0


class Crasher(Node):
    """Nodo che simula un crash dopo un intervallo prefissato."""

    def __init__(self) -> None:
        """Inizializza il nodo e il timer che provochera' il crash."""
        super().__init__("crasher")
        self.create_timer(_LIFETIME_SECONDS, self._crash)
        self.get_logger().info(
            f"Crasher avviato: crashero' tra {_LIFETIME_SECONDS:.0f} secondi."
        )

    def _crash(self) -> None:
        """Solleva un'eccezione per simulare un crash del nodo.

        Raises:
            RuntimeError: Sempre, per terminare il processo del nodo.
        """
        self.get_logger().error("Crash simulato del nodo crasher!")
        raise RuntimeError("Crash simulato del nodo crasher.")


def main() -> None:
    """Punto di ingresso del nodo crasher."""
    rclpy.init()
    node = Crasher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
