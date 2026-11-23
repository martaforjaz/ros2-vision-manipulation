from setuptools import setup

setup(name="vision_grasp", version="0.1.0", packages=["vision_grasp"],
      data_files=[
          ("share/ament_index/resource_index/packages", ["resource/vision_grasp"]),
          ("share/vision_grasp", ["package.xml"]),
      ],
      entry_points={"console_scripts": ["demo = vision_grasp.demo:main",
                                        "chess_demo = vision_grasp.chess_node:main"]})
