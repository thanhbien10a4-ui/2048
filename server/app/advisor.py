from __future__ import annotations

import math
import os
from dataclasses import dataclass
from functools import lru_cache

from .game import Board, DIRECTIONS, Direction, legal_moves, move_board


@dataclass
class Suggestion:
    direction: Direction
    provider: str
    confidence: float | None = None
    fallback: bool = False


def _log_tile(value: int) -> float:
    return math.log2(value) if value else 0.0


def _evaluate(board: tuple[tuple[int, ...], ...]) -> float:
    """Estimate a board's long-term health; larger values are better."""
    cells = [value for row in board for value in row]
    empty = cells.count(0)
    largest = max(cells)
    largest_log = _log_tile(largest)

    # Keep values ordered along rows and columns. For each line, allow either
    # direction and charge for reversals in the chosen direction.
    monotonicity = 0.0
    lines = list(board) + [tuple(board[r][c] for r in range(4)) for c in range(4)]
    for line in lines:
        logs = [_log_tile(value) for value in line]
        inc = dec = 0.0
        for left, right in zip(logs, logs[1:]):
            delta = right - left
            if delta > 0:
                inc += delta
            else:
                dec -= delta
        monotonicity -= min(inc, dec)

    smoothness = 0.0
    merge_pairs = 0
    for r in range(4):
        for c in range(4):
            value = board[r][c]
            if not value:
                continue
            for nr, nc in ((r + 1, c), (r, c + 1)):
                if nr < 4 and nc < 4 and board[nr][nc]:
                    neighbor = board[nr][nc]
                    smoothness += abs(_log_tile(value) - _log_tile(neighbor))
                    if neighbor == value:
                        merge_pairs += 1

    corners = (board[0][0], board[0][3], board[3][0], board[3][3])
    corner_bonus = 1.0 if largest in corners else 0.0
    return (
        empty * 270.0
        + monotonicity * 45.0
        - smoothness * 8.0
        + merge_pairs * 32.0
        + largest_log * 115.0 * corner_bonus
        + largest_log * 12.0
    )


class ExpectimaxAdvisor:
    """A CPU-only 2048 policy that looks ahead through random tile spawns."""

    name = "expectimax"

    def __init__(self, depth: int = 2) -> None:
        self.depth = depth

    def suggest(self, board: Board, score: int) -> Suggestion:
        actions = legal_moves(board)
        if not actions:
            raise ValueError("No legal moves remain")

        @lru_cache(maxsize=100_000)
        def player_value(state: tuple[tuple[int, ...], ...], depth: int) -> float:
            if depth <= 0:
                return _evaluate(state)
            candidates: list[float] = []
            current = [list(row) for row in state]
            for action in DIRECTIONS:
                moved, _ = move_board(current, action)
                if moved != current:
                    candidates.append(chance_value(tuple(tuple(row) for row in moved), depth))
            return max(candidates) if candidates else _evaluate(state)

        @lru_cache(maxsize=100_000)
        def chance_value(state: tuple[tuple[int, ...], ...], depth: int) -> float:
            if depth <= 0:
                return _evaluate(state)
            empty_cells = [(r, c) for r in range(4) for c in range(4) if state[r][c] == 0]
            if not empty_cells:
                return player_value(state, depth - 1)
            expected = 0.0
            for r, c in empty_cells:
                for value, probability in ((2, 0.9), (4, 0.1)):
                    spawned = [list(row) for row in state]
                    spawned[r][c] = value
                    expected += probability * player_value(tuple(tuple(row) for row in spawned), depth - 1)
            return expected / len(empty_cells)

        current = [list(row) for row in board]
        best_direction = actions[0]
        best_value = float("-inf")
        for action in DIRECTIONS:
            moved, _ = move_board(current, action)
            if moved == current:
                continue
            value = chance_value(tuple(tuple(row) for row in moved), self.depth)
            if value > best_value:
                best_direction, best_value = action, value
        return Suggestion(best_direction, provider=self.name)


class DemoAdvisor(ExpectimaxAdvisor):
    """No-download strategic advisor used for the ready-to-run demo."""


class LayaAdvisor:
    name = "laya + expectimax"

    def __init__(self) -> None:
        try:
            from laya import Router
        except ImportError as exc:
            raise RuntimeError("Laya is not installed. Install with: pip install -e '.[laya]'") from exc
        self.router = Router(default="english")
        self.strategy = ExpectimaxAdvisor()

    def suggest(self, board: Board, score: int) -> Suggestion:
        actions = legal_moves(board)
        if not actions:
            raise ValueError("No legal moves remain")
        criteria = {
            action: {
                "up": "Move tiles up.",
                "down": "Move tiles down.",
                "left": "Move tiles left.",
                "right": "Move tiles right.",
            }[action]
            for action in actions
        }
        state = (
            "Choose the best legal move in 2048. Equal adjacent tiles merge once; new 2 or 4 tiles appear randomly. "
            "Keep the largest tile in a corner, preserve empty cells, and arrange tiles in descending order.\n"
            f"Board rows, top to bottom: {board}\nScore: {score}\n"
            f"Only these moves are legal: {', '.join(actions)}."
        )
        result = self.router.predict(
            state,
            {
                "direction": {
                    "type": "choice",
                    "instructions": "Which legal move should be considered?",
                    "criteria": criteria,
                }
            },
        )
        answer = result["answers"]["direction"]
        chosen = answer.get("choice")
        confidence = answer.get("confidence")

        # Keep Laya in the decision loop, but don't let an untrained language
        # model override a move with a clearly better game-tree evaluation.
        strategic = self.strategy.suggest(board, score)
        if chosen in actions and chosen == strategic.direction:
            return Suggestion(chosen, provider=self.name, confidence=confidence)
        return Suggestion(strategic.direction, provider=self.name, confidence=confidence)


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
