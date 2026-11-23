"""Verified chess moves for a synthetic, overhead-camera ROS 2 workcell."""
import chess
import cv2
import numpy as np

from .sim import execute
from math import dist

SCRIPT = "e2e4 d7d5 e4d5 d8d5 b1c3 d5a5 g1f3 a5b6 f1c4 g8f6".split()
TILE = 56
OFFSET = 32
TRAY = (.24, -.20)
DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def center(square):
    return .13 + chess.square_rank(square) * .03, (chess.square_file(square)-3.5)*.03


def render(pieces, hide=None):
    side = TILE * 8 + 2 * OFFSET
    frame = np.full((side, side), 255, dtype=np.uint8)
    for square in chess.SQUARES:
        col, row = chess.square_file(square), 7-chess.square_rank(square)
        x, y = OFFSET+TILE*col, OFFSET+TILE*row
        frame[y:y+TILE, x:x+TILE] = 226 if (col+row)%2 else 247
        if square in pieces and square != hide:
            frame[y+12:y+44, x+12:x+44] = cv2.aruco.generateImageMarker(DICTIONARY, pieces[square], 32)
    return frame


def observe(frame):
    corners, ids, _ = cv2.aruco.ArucoDetector(DICTIONARY).detectMarkers(frame)
    seen = {}
    used = set()
    if ids is not None:
        for marker, pixels in zip(ids.ravel(), corners):
            x, y = pixels.reshape(4, 2).mean(axis=0)
            col, row = int((x-OFFSET)//TILE), int((y-OFFSET)//TILE)
            if not (0 <= col < 8 and 0 <= row < 8):
                continue
            square = chess.square(col, 7-row)
            if square in seen or int(marker) in used:
                raise ValueError("Duplicate tag or occupied square in frame")
            used.add(int(marker))
            seen[square] = int(marker)
    return seen


class Workcell:
    def __init__(self):
        self.board = chess.Board()
        self.pieces = {sq: i for i, sq in enumerate(sorted(self.board.piece_map()))}

    def play(self, uci, inject_occlusion=False, inject_wrong_square=None, *, observe_motion=None):
        move = chess.Move.from_uci(uci)
        if (move not in self.board.legal_moves or self.board.is_castling(move) or move.promotion):
            raise ValueError(f"Unsupported or illegal move: {uci}")
        if observe(render(self.pieces)) != self.pieces:
            raise RuntimeError("Initial visual state does not match the ledger")
        expected = self.pieces.copy()
        capture = self.board.is_capture(move)
        errors = []
        if capture:
            square = move.to_square
            if self.board.is_en_passant(move):
                square += -8 if self.board.turn == chess.WHITE else 8
            motion, _ = execute(center(square), TRAY, observe_motion=observe_motion)
            errors.append(motion["place_error_metres"])
            expected.pop(square)
        simulated = expected.copy()
        tag = expected.pop(move.from_square)
        expected[move.to_square] = tag
        commanded = inject_wrong_square if inject_wrong_square is not None else move.to_square
        motion, _ = execute(center(move.from_square), center(commanded), observe_motion=observe_motion)
        errors.append(motion["place_error_metres"])
        placed = motion["payload_final_metres"]
        square = min(chess.SQUARES, key=lambda sq: dist(center(sq), placed))
        if dist(center(square), placed) > .01 or square in simulated:
            raise RuntimeError("Placement is outside the square tolerance or hits an occupied square")
        simulated[square] = simulated.pop(move.from_square)
        first = render(simulated, hide=square if inject_occlusion else None)
        retry = observe(first) != expected
        if retry and observe(render(simulated)) != expected:
            raise RuntimeError("Board did not verify after reacquisition")
        self.pieces = simulated
        self.board.push(move)
        return {"move": uci, "capture": capture, "verification_retries": int(retry),
                "max_simulated_placement_error_metres": max(errors), "fen": self.board.fen()}

    def candidate_moves(self):
        return [move for move in self.board.legal_moves
                if not self.board.is_castling(move) and not move.promotion]
