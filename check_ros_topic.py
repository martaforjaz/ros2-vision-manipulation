"""Read the ROS message payload independently of CLI YAML formatting."""
import json
from time import monotonic

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main():
    rclpy.init()
    node = Node("vision_grasp_smoke_test")
    received = []
    node.create_subscription(String, "simulated_grasp/plan", received.append, 10)
    try:
        deadline = monotonic() + 25
        while not received and monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
        if not received:
            raise RuntimeError("No simulated grasp plan received")
        plan = json.loads(received[0].data)
        if plan["status"] != "reachable" or plan["simulation"]["place_error_metres"] > 0.002:
            raise ValueError(f"Unexpected ROS plan: {plan}")
        print(json.dumps(plan))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
