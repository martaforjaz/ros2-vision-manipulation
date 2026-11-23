"""Build the README illustration and a replay from a verified MuJoCo move."""
from pathlib import Path

import chess
from PIL import Image, ImageDraw

from vision_grasp.chessboard import Workcell, center, render
from vision_grasp.sim import execute

OUT = Path(__file__).resolve().parent / "figures"
NAVY = "#142d50"
PLUM = "#985d88"
PAPER = "#faf6f4"
LIGHT = "#e7c7d5"
GOLD = "#ffc07d"


def hero():
    image = Image.new("RGB", (1000, 310), PAPER)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((8, 8, 992, 302), 28, fill=NAVY)
    for x, y, size in [(35, 40, 5), (97, 97, 3), (394, 35, 4), (618, 97, 4),
                       (909, 48, 5), (957, 204, 4), (470, 231, 3)]:
        d.line((x-size, y, x+size, y), fill=LIGHT, width=2)
        d.line((x, y-size, x, y+size), fill=LIGHT, width=2)
    d.text((49, 105), "Robotic chess", fill="white", font_size=51, stroke_width=1)
    d.text((51, 178), "Camera-verified moves in ROS 2 + MuJoCo", fill=LIGHT, font_size=20)
    board = (655, 137)
    for row in range(6):
        for col in range(8):
            x, y = board[0]+col*32-row*13, board[1]+row*19
            d.polygon([(x,y),(x+32,y),(x+19,y+19),(x-13,y+19)],
                      fill=LIGHT if (row+col)%2 else "#8b557e")
    for x, y, color in [(703,230,GOLD),(752,208,"#fff5ed"),(779,164,GOLD),(866,178,"#fff5ed")]:
        d.ellipse((x-12,y-6,x+12,y+4), fill=NAVY)
        d.ellipse((x-8,y-18,x+8,y-3), fill=color)
        d.ellipse((x-5,y-25,x+5,y-15), fill=color)
    shoulder, elbow, wrist = (552,209),(592,65),(725,112)
    d.ellipse((506,202,594,251), fill="#29466c")
    d.rounded_rectangle((521,196,580,233), 11, fill=LIGHT)
    d.line((shoulder,elbow,wrist), fill="#f3e6e9", width=18)
    for x,y in (shoulder,elbow,wrist):
        d.ellipse((x-14,y-14,x+14,y+14), fill=PLUM, outline=LIGHT, width=3)
    d.line((725,124,725,151), fill=GOLD, width=5)
    d.line((713,161,713,151,737,151,737,161), fill=GOLD, width=4)
    image.save(OUT / "chess-illustration.png")


def replay():
    workcell = Workcell()
    before = Image.fromarray(render(workcell.pieces)).convert("RGB")
    evidence = workcell.play("e2e4")
    after = Image.fromarray(render(workcell.pieces)).convert("RGB")
    _, trajectory = execute(center(chess.E2), center(chess.E4))
    frames = []
    path = []

    def project(x, y):
        return (312 + 500*y, 288 - 500*x)

    for phase, _, x, y in trajectory:
        frame = Image.new("RGB", (940, 320), PAPER)
        d = ImageDraw.Draw(frame)
        d.text((36, 19), "MuJoCo · end-effector trace", fill=NAVY, font_size=21)
        d.text((616, 19), "Synthetic ArUco camera", fill=NAVY, font_size=21)
        for square in chess.SQUARES:
            px, py = project(*center(square))
            shade = LIGHT if (chess.square_rank(square) + chess.square_file(square)) % 2 else "#ecdce4"
            d.rectangle((px-7, py-7, px+7, py+7), fill=shade)
        for square, color in [(chess.E2, NAVY), (chess.E4, PLUM)]:
            px, py = project(*center(square))
            d.rectangle((px-7, py-7, px+7, py+7), outline=color, width=2)
        pos = project(x, y)
        path.append(pos)
        if len(path) > 1:
            d.line(path, fill=PLUM, width=3)
        d.ellipse((pos[0]-5, pos[1]-5, pos[0]+5, pos[1]+5), fill=NAVY)
        verified = len(path) == len(trajectory)
        camera = after if verified else before
        frame.paste(camera.resize((220, 220), Image.Resampling.NEAREST), (622, 53))
        label = "e2 → e4  ·  Board verified" if verified else f"e2 → e4  ·  {phase.title()}"
        d.text((36, 281), label, fill=NAVY, font_size=18)
        frames.append(frame)
    assert evidence["move"] == "e2e4" and evidence["verification_retries"] == 0
    frames[0].save(OUT / "chess-simulation.gif", save_all=True, append_images=frames[1:],
                   duration=[80]*len(frames[:-1])+[1800], loop=0, optimize=True)


if __name__ == "__main__":
    hero()
    replay()

