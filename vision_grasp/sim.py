"""Physics-backed planar pick and place with an idealized carried object."""
from math import dist

import mujoco

from .core import inverse

PLACE = (0.20, 0.22)
MODEL = """
<mujoco model="planar_arm">
  <option timestep="0.004" gravity="0 0 0"/>
  <default>
    <joint damping="0.75"/>
    <geom contype="0" conaffinity="0" density="700"/>
  </default>
  <worldbody>
    <body name="shoulder">
      <joint name="q1" type="hinge" axis="0 0 1"/>
      <geom type="capsule" fromto="0 0 0 .24 0 0" size=".017"/>
      <body name="elbow" pos=".24 0 0">
        <joint name="q2" type="hinge" axis="0 0 1"/>
        <geom type="capsule" fromto="0 0 0 .20 0 0" size=".013"/>
        <site name="tcp" pos=".20 0 0" size=".01"/>
      </body>
    </body>
    <body name="payload" mocap="true">
      <geom type="box" size=".015 .015 .015" rgba=".6 .3 .5 1"/>
    </body>
  </worldbody>
  <actuator>
    <position joint="q1" kp="45"/>
    <position joint="q2" kp="35"/>
  </actuator>
</mujoco>
"""


def execute(pick, place=PLACE, *, observe_motion=None):
    joints = inverse(*pick)
    if joints is None:
        raise ValueError("Pick pose is outside the arm workspace")
    drop_joints = inverse(*place)
    if drop_joints is None:
        raise ValueError("Drop pose is outside the arm workspace")
    model = mujoco.MjModel.from_xml_string(MODEL)
    data = mujoco.MjData(model)
    data.mocap_pos[0] = (*pick, 0.0)
    mujoco.mj_forward(model, data)
    trajectory = []

    def phase(name, angles, carrying):
        data.ctrl[:] = angles
        for step in range(600):
            mujoco.mj_step(model, data)
            tcp = data.site("tcp").xpos
            if carrying:
                data.mocap_pos[0] = tcp
            if step % 20 == 0 or step == 599:
                trajectory.append((name, round(float(data.time), 4), *map(float, tcp[:2])))
                if observe_motion is not None:
                    observe_motion(name, pick, place, tuple(data.body("elbow").xpos[:2]),
                                   tuple(tcp[:2]), tuple(data.mocap_pos[0, :2]))
        return tuple(map(float, data.site("tcp").xpos[:2]))

    reached = phase("approach", joints, False)
    pick_error = dist(reached, pick)
    if pick_error > 0.002:
        raise RuntimeError(f"Approach failed to settle: {pick_error:.6f} m")
    phase("transfer", drop_joints, True)
    placed = tuple(map(float, data.mocap_pos[0, :2]))
    place_error = round(dist(placed, place), 9)
    if place_error > 0.002:
        raise RuntimeError(f"Transfer failed to settle: {place_error:.6f} m")
    return {"pick_error_metres": round(pick_error, 9), "place_error_metres": place_error,
            "drop_target_metres": place, "payload_final_metres": placed}, trajectory
