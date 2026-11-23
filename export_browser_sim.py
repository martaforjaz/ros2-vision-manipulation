"""Export the MuJoCo model and verified chess transfer schedule for the web demo."""
import json
from pathlib import Path

import chess

from vision_grasp.chessboard import TRAY, Workcell, center
from vision_grasp.sim import MODEL


def export(out):
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent
    records = json.loads((root / "evidence/chess-scripted.json").read_text(encoding="utf-8"))
    workcell = Workcell()
    plan = []
    for record in records:
        move = chess.Move.from_uci(record["move"])
        board = workcell.board
        transfers = []
        if board.is_capture(move):
            square = move.to_square
            if board.is_en_passant(move):
                square += -8 if board.turn else 8
            transfers.append({"square": chess.square_name(square), "pick": center(square), "drop": TRAY})
        transfers.append({"square": chess.square_name(move.from_square), "pick": center(move.from_square),
                          "drop": center(move.to_square)})
        result = workcell.play(record["move"], inject_occlusion=bool(record["verification_retries"]))
        assert result["fen"] == record["fen"]
        assert result["verification_retries"] == record["verification_retries"]
        plan.append({**result, "transfers": transfers})
    (out / "chess-arm.xml").write_text(MODEL.strip() + "\n", encoding="utf-8")
    (out / "chess-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export(Path(__file__).resolve().parent / "web")
