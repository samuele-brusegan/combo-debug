"""Nodo demo 'navigate_server': server azione sano per /navigate_to_pose.

Rappresenta un server azione sano: risponde alle richieste, quindi appare VERDE nella
dashboard e l'azione /navigate_to_pose risulta attiva.
"""

from __future__ import annotations

import rclpy
from rclpy.action import ActionServer
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from example_interfaces.action import Fibonacci


class NavigateServer(Node):
    """Server per l'azione NavigateToPose (simulata con Fibonacci)."""

    def __init__(self) -> None:
        """Inizializza il nodo e il server azione."""
        super().__init__("navigate_server")
        self._action_server = ActionServer(self, Fibonacci, "navigate_to_pose", self._execute_callback)
        self.get_logger().info("NavigateServer avviato: azione /navigate_to_pose disponibile.")

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
    """Punto di ingresso del nodo navigate_server."""
    rclpy.init()
    node = NavigateServer()
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
