"""Expose the verification loop as a ROS 2 UCI move topic."""
import json

import chess.engine
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .chessboard import Workcell


class ChessNode(Node):
    def __init__(self):
        super().__init__("verified_chess")
        self.cell = Workcell()
        self.declare_parameter("stockfish_path", "")
        path = self.get_parameter("stockfish_path").value
        self.engine = chess.engine.SimpleEngine.popen_uci(path) if path else None
        self.results = self.create_publisher(String, "chess/result", 10)
        self.create_subscription(String, "chess/move", self.on_move, 10)

    def on_move(self, message):
        try:
            result = self.cell.play(message.data.strip())
        except (ValueError, RuntimeError) as error:
            result = {"status": "rejected", "error": str(error), "fen": self.cell.board.fen()}
        else:
            result["status"] = "verified"
            if self.engine and self.cell.candidate_moves():
                choices = self.cell.candidate_moves()
                try:
                    reply = self.engine.play(self.cell.board, chess.engine.Limit(depth=5), root_moves=choices)
                    result["engine_reply"] = self.cell.play(reply.move.uci())
                except (RuntimeError, ValueError, chess.engine.EngineError) as error:
                    result["engine_error"] = str(error)
        self.results.publish(String(data=json.dumps(result)))


def main():
    rclpy.init()
    node = ChessNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.engine:
            node.engine.quit()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
