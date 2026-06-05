"""Nodo demo 'navigate_server_only': server azione senza client (zombie per assenza di subscriber).

Rappresenta un server azione senza client: l'azione /navigate_no_sub rimane nel grafo
ma nessun client la usa, quindi appare ZOMBIE (viola) nella dashboard.
"""

from __future__ import annotations

import rclpy
from rclpy.action import ActionServer
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from example_interfaces.action import Fibonacci


class NavigateServerOnly(Node):
    """Server per l'azione NavigateToPose senza client (simulata con Fibonacci)."""

    def __init__(self) -> None:
        """Inizializza il nodo e il server azione."""
        super().__init__("navigate_server_only")
        self._action_server = ActionServer(self, Fibonacci, "navigate_no_sub", self._execute_callback)
        self.get_logger().info("NavigateServerOnly avviato: azione /navigate_no_sub disponibile (nessun client).")

    async def _execute_callback(self, goal_handle) -> Fibonacci.Result:
        """Callback del goal: simula la navigazione."""
        self.get_logger().info(f"Ricevuto goal: order={goal_handle.request.order}")

        feedback_msg = Fibonacci.Feedback()
        feedback_msg.sequence = [0, 1]

        for i in range(1, goal_handle.request.order):
            feedback_msg.sequence.append(feedback_msg.sequence[i] + feedback_msg.sequence[i - 1])
            goal_handle.publish_feedback(feedback_msg)

        goal_handle.succeed()
        result = Fibonacci.Result()
        result.sequence = feedback_msg.sequence
        self.get_logger().info(f"Goal completato: {result.sequence}")
        return result


def main() -> None:
    """Punto di ingresso del nodo navigate_server_only."""
    rclpy.init()
    node = NavigateServerOnly()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
