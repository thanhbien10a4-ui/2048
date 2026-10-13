from __future__ import annotations

import os
from dataclasses import dataclass

from .game import Board, Direction, legal_moves


@dataclass
class Suggestion:
    direction: Direction
    provider: str
    confidence: float | None = None
    fallback: bool = False


class DemoAdvisor:
    """No-download advisor used to run the UI before installing model weights."""

    name = "demo"

    def suggest(self, board: Board, score: int) -> Suggestion:
        actions = legal_moves(board)
        if not actions:
            raise ValueError("No legal moves remain")
        # Clearly labeled baseline, not a Laya prediction.
        return Suggestion(actions[0], provider=self.name)


class LayaAdvisor:
    name = "laya"

    def __init__(self) -> None:
        try:
            from laya import Router
        except ImportError as exc:
            raise RuntimeError("Laya is not installed. Install with: pip install -e '.[laya]'") from exc
        self.router = Router(default="english")

    def suggest(self, board: Board, score: int) -> Suggestion:
        actions = legal_moves(board)
        if not actions:
            raise ValueError("No legal moves remain")
        criteria = {
            action: {
                "top": "Move every tile toward the top edge.",
                "down": "Move every tile toward the bottom edge.",
                "left": "Move every tile toward the left edge.",
                "right": "Move every tile toward the right edge.",
            }[action]
            for action in actions
        }
        state = (
            "You are selecting one legal move in the game 2048. "
            "Two equal adjacent tiles merge once when moved. Empty cells are valuable. "
            "Try to keep the largest tile in a corner and preserve open space.\n"
            f"Board rows, top to bottom: {board}\nScore: {score}\n"
            f"Only these moves are legal: {', '.join(actions)}."
        )
        result = self.router.predict(
            state,
            {
                "direction": {
                    "type": "choice",
                    "instructions": "Which legal move is best for the next turn?",
                    "criteria": criteria,
                }
            },
        )
        answer = result["answers"]["direction"]
        chosen = answer.get("choice")
        confidence = answer.get("confidence")
        if chosen not in actions:
            raise ValueError(f"Laya returned an unexpected move: {chosen!r}")
        return Suggestion(chosen, provider=self.name, confidence=confidence)


_advisor = None


def get_advisor():
    global _advisor
    if _advisor is None:
        provider = os.getenv("AI_PROVIDER", "demo").lower()
        if provider == "laya":
            _advisor = LayaAdvisor()
        elif provider == "demo":
            _advisor = DemoAdvisor()
        else:
            raise RuntimeError(f"Unknown AI_PROVIDER={provider!r}; choose 'demo' or 'laya'")
    return _advisor


def reset_advisor_for_tests() -> None:
    global _advisor
    _advisor = None
