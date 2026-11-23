"""Reproduce a ten-ply match and a deterministic camera retry."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import chess.engine
import chess

from vision_grasp.chessboard import SCRIPT, Workcell


def run(stockfish=None):
    fault = Workcell()
    before = fault.board.fen()
    try:
        fault.play("e2e4", inject_wrong_square=chess.D3)
    except RuntimeError:
        assert fault.board.fen() == before
    else:
        raise AssertionError("A wrong-square placement must not advance the game")
    workcell = Workcell()
    trace = []
    engine = chess.engine.SimpleEngine.popen_uci(stockfish) if stockfish else None
    try:
        for index, scripted in enumerate(SCRIPT):
            move = scripted
            if engine:
                move = engine.play(workcell.board, chess.engine.Limit(depth=5),
                                   root_moves=workcell.candidate_moves()).move.uci()
            start = perf_counter()
            result = workcell.play(move, inject_occlusion=index == 2)
            result["wall_seconds"] = round(perf_counter()-start, 4)
            trace.append(result)
    finally:
        if engine:
            engine.quit()
    assert len(trace) == 10
    assert sum(move["verification_retries"] for move in trace) == 1
    if not engine:
        assert sum(move["capture"] for move in trace) == 2
    return trace


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stockfish", help="Path to a Stockfish UCI executable")
    args = parser.parse_args()
    evidence = Path(__file__).parent / "evidence"
    tag = "stockfish" if args.stockfish else "scripted"
    output = json.dumps(run(args.stockfish), indent=2) + "\n"
    (evidence / f"chess-{tag}.json").write_text(output, encoding="utf-8")
    print(output)
