"""Verify the positive path and two fail-closed paths without ROS or a robot."""
import json
import csv
from math import dist
from pathlib import Path

from vision_grasp.core import estimate, forward, frame, inverse, target
from vision_grasp.sim import execute

results = {}
for mode, expected in (("reachable", "reachable"), ("unreachable", "unreachable"),
                       ("missing", "marker_missing")):
    pose = estimate(frame(mode))
    status = "marker_missing"
    if pose is not None:
        xy = target(pose[1])
        joints = inverse(*xy)
        status = "unreachable" if joints is None else "reachable"
        results[mode] = {"target_metres": [round(x, 6) for x in xy]}
        if joints is not None:
            residual = dist(xy, forward(*joints))
            assert abs(xy[0] - 0.3) < 0.01 and residual < 1e-9
            results[mode]["forward_residual_metres"] = round(residual, 12)
            results[mode]["simulation"], trajectory = execute(xy)
    assert status == expected
    results.setdefault(mode, {})["status"] = status
path = Path(__file__).resolve().parent / "evidence"
path.mkdir(exist_ok=True)
with (path / "scenarios.json").open("w", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(results, indent=2) + "\n")
with (path / "trajectory.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["phase", "simulation_seconds", "x_metres", "y_metres"])
    writer.writerows((phase, t, round(x, 7), round(y, 7)) for phase, t, x, y in trajectory)
print(json.dumps(results, indent=2))
