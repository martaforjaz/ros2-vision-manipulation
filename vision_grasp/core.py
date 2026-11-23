"""Camera pose and planar arm math, independent of ROS."""
from math import acos, atan2, cos, sin

import cv2
import numpy as np

CAMERA = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1]])
SIZE = 0.06
MARKER = 7
LINKS = (0.24, 0.20)


def dictionary():
    return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def estimate(gray, camera=CAMERA):
    corners, ids, _ = cv2.aruco.ArucoDetector(dictionary()).detectMarkers(gray)
    if ids is None or MARKER not in ids.ravel():
        return None
    pixels = corners[list(ids.ravel()).index(MARKER)].reshape(4, 2)
    half = SIZE / 2
    square = np.array([[-half, half, 0], [half, half, 0],
                       [half, -half, 0], [-half, -half, 0]], dtype=float)
    ok, rotation, translation = cv2.solvePnP(
        square, pixels, camera, None, flags=cv2.SOLVEPNP_IPPE_SQUARE
    )
    if not ok or float(translation[2, 0]) <= 0:
        return None
    return rotation.ravel(), translation.ravel()


def inverse(x, y, links=LINKS):
    a, b = links
    elbow_cos = (x*x + y*y - a*a - b*b) / (2*a*b)
    if not -1 <= elbow_cos <= 1:
        return None
    elbow = acos(elbow_cos)
    shoulder = atan2(y, x) - atan2(b*sin(elbow), a+b*cos(elbow))
    return shoulder, elbow


def forward(shoulder, elbow, links=LINKS):
    a, b = links
    return a*cos(shoulder) + b*cos(shoulder+elbow), a*sin(shoulder) + b*sin(shoulder+elbow)


def target(translation):
    """Idealized camera-to-arm mapping for the synthetic rig (metres)."""
    return float(translation[2]), float(-translation[0])


def frame(mode="reachable"):
    gray = np.full((480, 640), 255, dtype=np.uint8)
    if mode != "missing":
        width = 120 if mode == "reachable" else 60
        marker = cv2.aruco.generateImageMarker(dictionary(), MARKER, width)
        gray[240-width//2:240+width//2, 320-width//2:320+width//2] = marker
    return gray
