"""Render the ROS pipeline and the measured MuJoCo trajectory as SVG."""
import csv
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAVY, PLUM, GRAY = "#102b59", "#915883", "#506078"


def label(x, y, value, size=18, color=NAVY, weight=400):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}">{escape(value)}</text>')


def save(name, parts, height):
    directory = ROOT / "figures"
    directory.mkdir(exist_ok=True)
    with (directory / f"{name}.svg").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" '
                     f'viewBox="0 0 960 {height}" font-family="Arial,sans-serif" role="img">'
                     f'<title>{name}</title><rect width="960" height="{height}" fill="white"/>'
                     + "".join(parts) + "</svg>\n")


parts = [label(28, 49, "From an ArUco image to a simulated pick and place", 30, weight=700)]
for i, (heading, first, second) in enumerate([
    ("I. Publish image", "Synthetic camera", "ROS 2 sensor_msgs/Image"),
    ("II. Estimate pose", "OpenCV ArUco + PnP", "Reject missing markers"),
    ("III. Plan motion", "Camera-to-arm transform", "Reject unreachable targets"),
    ("IV. Execute", "MuJoCo arm dynamics", "ROS 2 result topic"),
]):
    x = 28 + i * 234
    parts += [f'<rect x="{x}" y="85" width="210" height="45" rx="22" fill="{NAVY}"/>',
              label(x+14, 114, heading, 19, "#fff", 700),
              label(x+4, 164, first, 16, NAVY, 700), label(x+4, 192, second, 15, GRAY)]
    if i < 3:
        parts.append(label(x+211, 166, "→", 22, PLUM, 700))
save("pipeline", parts, 228)

with (ROOT / "evidence/trajectory.csv").open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
parts = [label(28, 49, "The simulated arm approached and transferred the payload", 28, weight=700),
         label(28, 79, "End-effector trajectory in the planar arm frame", 17, GRAY)]


def point(x, y):
    return 135+1300*x, 390-900*y


for i in range(5):
    x, _ = point(i / 10, 0)
    _, y = point(0, i / 10)
    parts += [f'<path d="M{x} 120V435 M135 {y}H760" stroke="#e1e6ef" fill="none"/>',
              label(x-10, 460, f"{i/10:.1f}", 14, GRAY)]
    if i <= 3:
        parts.append(label(99, y+4, f"{i/10:.1f}", 14, GRAY))
parts += [label(360, 490, "x (m)", 17, GRAY), label(49, 258, "y (m)", 17, GRAY)]
for phase, color, y in (("approach", NAVY, 150), ("transfer", PLUM, 182)):
    points = [point(float(r["x_metres"]), float(r["y_metres"])) for r in rows if r["phase"] == phase]
    encoded = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    parts += [f'<polyline points="{encoded}" fill="none" stroke="{color}" stroke-width="3"/>',
              f'<path d="M760 {y}h25" stroke="{color}" stroke-width="3"/>',
              label(797, y+5, phase.title(), 17, color, 700)]
    x, end_y = points[-1]
    parts.append(f'<circle cx="{x:.2f}" cy="{end_y:.2f}" r="6" fill="{color}"/>')
save("trajectory", parts, 510)
