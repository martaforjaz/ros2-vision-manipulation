"""Render the verified chess sequence from sampled MuJoCo link positions."""
import argparse
import json
from pathlib import Path

import chess
import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vision_grasp.chessboard import SCRIPT, TRAY, Workcell, center

FPS = 12
NAVY = "#142d50"
PLUM = "#955e84"
GOLD = "#ffbd70"
PIECE_LABELS = {"p": "P", "r": "R", "n": "N", "b": "B", "q": "Q", "k": "K"}
FONT = ImageFont.load_default(size=14)


def screen(point):
    x, y = point
    return round(170 + y * 720), round(350 - x * 720)


def frame(board, step, status, motion=None):
    image = Image.new("RGB", (480, 384), "#f8f5f4")
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 479, 33), fill=NAVY)
    d.text((13, 7), "MuJoCo | Vision-verified robotic chess", fill="white", font=FONT)
    for square in chess.SQUARES:
        x, y = screen(center(square))
        shaded = (chess.square_rank(square) + chess.square_file(square)) % 2
        d.rectangle((x-11, y-11, x+11, y+11), fill="#cba9bc" if shaded else "#efe2e8")
    pieces = {center(square): piece for square, piece in board.piece_map().items()}
    if motion:
        _, pick, drop, elbow, tcp, payload = motion
        if drop != TRAY and step and board.is_capture(step):
            pieces.pop(center(step.to_square), None)
        moving = pieces.pop(pick, None)
        d.line((*screen((0, 0)), *screen(elbow), *screen(tcp)), width=8, fill=NAVY)
        for point in ((0, 0), elbow, tcp):
            x, y = screen(point)
            d.ellipse((x-5, y-5, x+5, y+5), fill=PLUM)
        if moving:
            pieces[payload] = moving
    for point, piece in pieces.items():
        x, y = screen(point)
        ink = NAVY if piece.color else "white"
        d.ellipse((x-8, y-8, x+8, y+8), fill="white" if piece.color else "#303958", outline=NAVY)
        d.text((x, y), PIECE_LABELS[piece.symbol().lower()], fill=ink, font=FONT, anchor="mm")
    x, y = screen(TRAY)
    d.rectangle((x-11,y-11,x+11,y+11), outline=PLUM, width=2)
    d.text((290, 180), "Capture tray", fill=NAVY, font=FONT)
    d.text((290, 205), step.uci() if step else "Start", fill=PLUM, font=FONT)
    d.text((290, 230), status, fill=NAVY, font=FONT)
    return np.asarray(image)


def render(trace_path, output, timestamps):
    records = json.loads(trace_path.read_text(encoding="utf-8"))
    assert [r["move"] for r in records] == SCRIPT
    workcell = Workcell()
    frames = 0
    complete = [0]
    with imageio.get_writer(output, fps=FPS, codec="libx264", pixelformat="yuv420p",
                            ffmpeg_params=["-movflags", "+faststart"], quality=5) as writer:
        def append(image, copies):
            nonlocal frames
            for _ in range(copies):
                writer.append_data(image)
            frames += copies

        append(frame(workcell.board, None, "Starting position"), 10)
        for record in records:
            before = workcell.board.copy(stack=False)
            move = chess.Move.from_uci(record["move"])
            motions = []
            def observe(*data):
                motions.append(data)
            actual = workcell.play(record["move"], inject_occlusion=bool(record["verification_retries"]),
                                   observe_motion=observe)
            assert actual["fen"] == record["fen"]
            assert actual["capture"] == record["capture"]
            assert actual["verification_retries"] == record["verification_retries"]
            for motion in motions[::3]:
                status = "Capture removal" if motion[2] == TRAY else motion[0].capitalize()
                append(frame(before, move, status, motion), 1)
            if record["verification_retries"]:
                append(frame(before, move, "Camera retry"), 6)
            complete.append(round(frames / FPS, 6))
            append(frame(workcell.board, move, "Board verified"), 10)
    timestamps.write_text(json.dumps(complete, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("timestamps", type=Path)
    args = parser.parse_args()
    render(args.trace, args.video, args.timestamps)

