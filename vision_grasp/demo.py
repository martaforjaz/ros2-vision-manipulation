"""Publish synthetic frames and subscribe to a software-only grasp plan."""
from array import array
import json

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .core import estimate, forward, frame, inverse, target
from .sim import execute


def plan(gray):
    pose = estimate(gray)
    if pose is None:
        return {"status": "marker_missing"}
    rotation, translation = pose
    xy = target(translation)
    result = {"rotation_vector": rotation.tolist(), "translation_metres": translation.tolist(),
              "target_metres": xy}
    joints = inverse(*xy)
    if joints is None:
        return {**result, "status": "unreachable"}
    motion, _ = execute(xy)
    return {**result, "status": "reachable", "joints_radians": joints,
            "ideal_tcp_metres": forward(*joints), "simulation": motion}


class Demo(Node):
    def __init__(self):
        super().__init__("vision_grasp_demo")
        self.declare_parameter("scene", "reachable")
        self.images = self.create_publisher(Image, "synthetic_camera/image", qos_profile_sensor_data)
        self.results = self.create_publisher(String, "simulated_grasp/plan", 10)
        self.create_subscription(Image, "synthetic_camera/image", self.on_image, qos_profile_sensor_data)
        self.create_timer(1.0, self.tick)

    def tick(self):
        scene = self.get_parameter("scene").value
        gray = frame(scene)
        msg = Image(height=gray.shape[0], width=gray.shape[1], encoding="mono8", step=gray.shape[1],
                    data=array("B", gray.tobytes()))
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "synthetic_camera_optical_frame"
        self.images.publish(msg)

    def on_image(self, msg):
        if msg.encoding != "mono8" or msg.step < msg.width or len(msg.data) != msg.step * msg.height:
            return
        gray = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width]
        self.results.publish(String(data=json.dumps(plan(gray))))


def main(args=None):
    rclpy.init(args=args)
    node = Demo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
