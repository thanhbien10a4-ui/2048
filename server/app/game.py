from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol, Sequence, TypeVar

Direction = Literal["up", "down", "left", "right"]
DIRECTIONS: tuple[Direction, ...] = ("up", "down", "left", "right")
Board = list[list[int]]
T = TypeVar("T")


class RandomSource(Protocol):
    def choice(self, values: Sequence[T]) -> T: ...
    def random(self) -> float: ...


def _transpose(board: Board) -> Board:
    return [list(column) for column in zip(*board)]


def _merge_left(row: list[int]) -> tuple[list[int], int]:
    values = [value for value in row if value]
    merged: list[int] = []
    gained = 0
    index = 0
    while index < len(values):
        if index + 1 < len(values) and values[index] == values[index + 1]:
            value = values[index] * 2
            merged.append(value)
            gained += value
            index += 2
        else:
            merged.append(values[index])
            index += 1
    return merged + [0] * (len(row) - len(merged)), gained


def move_board(board: Board, direction: Direction) -> tuple[Board, int]:
    """Return a moved board and score gained without mutating the input."""
    if direction in ("up", "down"):
        transformed = _transpose(board)
        horizontal_direction: Direction = "left" if direction == "up" else "right"
        moved, gained = move_board(transformed, horizontal_direction)
        return _transpose(moved), gained

    output: Board = []
    total_gained = 0
    for original in board:
        row = original if direction == "left" else list(reversed(original))
        merged, gained = _merge_left(row)
        output.append(merged if direction == "left" else list(reversed(merged)))
        total_gained += gained
    return output, total_gained


def legal_moves(board: Board) -> list[Direction]:
    return [direction for direction in DIRECTIONS if move_board(board, direction)[0] != board]


def spawn_tile(board: Board, rng: RandomSource | None = None) -> Board:
    """Place a 2 (90%) or 4 (10%) in an empty cell, returning a copied board."""
    source = rng or random
    empty = [(r, c) for r, row in enumerate(board) for c, value in enumerate(row) if value == 0]
    copied = [row[:] for row in board]
    if empty:
        r, c = source.choice(empty)
        copied[r][c] = 4 if source.random() < 0.1 else 2
    return copied


def new_board(rng: RandomSource | None = None) -> Board:
    board = [[0] * 4 for _ in range(4)]
    return spawn_tile(spawn_tile(board, rng), rng)


@dataclass
class Game:
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    board: Board = field(default_factory=new_board)
    score: int = 0
    moves: int = 0
    won: bool = False
    over: bool = False
    last_move: Direction | None = None
    last_source: str | None = None
    fallback_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def max_tile(self) -> int:
        return max(max(row) for row in self.board)

    def as_dict(self) -> dict:
        return {
            "id": self.game_id,
            "board": self.board,
            "score": self.score,
            "moves": self.moves,
            "max_tile": self.max_tile,
            "won": self.won,
            "over": self.over,
            "legal_moves": legal_moves(self.board),
            "last_move": self.last_move,
            "last_source": self.last_source,
            "fallback_count": self.fallback_count,
            "created_at": self.created_at,
        }

    def apply(self, direction: Direction, source: str) -> bool:
        if self.over:
            return False
        moved, gained = move_board(self.board, direction)
        if moved == self.board:
            return False
        self.board = spawn_tile(moved)
        self.score += gained
        self.moves += 1
        self.won = self.won or any(value >= 2048 for row in self.board for value in row)
        self.over = not legal_moves(self.board)
        self.last_move = direction
        self.last_source = source
        return True
