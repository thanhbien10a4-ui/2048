from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .advisor import ExpectimaxAdvisor, get_advisor
from .game import Direction, Game, legal_moves

app = FastAPI(title="Laya 2048 Lab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

games: dict[str, Game] = {}
logger = logging.getLogger(__name__)


class MoveRequest(BaseModel):
    direction: Direction


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "provider": os.getenv("AI_PROVIDER", "demo")}


@app.post("/api/games")
def create_game() -> dict:
    game = Game()
    games[game.game_id] = game
    return game.as_dict()


def _get_game(game_id: str) -> Game:
    game = games.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.get("/api/games/{game_id}")
def read_game(game_id: str) -> dict:
    return _get_game(game_id).as_dict()


@app.post("/api/games/{game_id}/move")
def human_move(game_id: str, request: MoveRequest) -> dict:
    game = _get_game(game_id)
    if not game.apply(request.direction, source="human"):
        raise HTTPException(status_code=409, detail="That move is not available")
    return game.as_dict()


@app.post("/api/games/{game_id}/ai-move")
def ai_move(game_id: str) -> dict:
    game = _get_game(game_id)
    if game.over:
        raise HTTPException(status_code=409, detail="Game is over")
    fallback_used = False
    try:
        suggestion = get_advisor().suggest(game.board, game.score)
        source = suggestion.provider
        direction = suggestion.direction
        if not game.apply(direction, source=source):
            raise ValueError("Advisor suggested an illegal move")
    except Exception:
        fallback_used = True
        logger.exception("AI move failed; applying a visible safe fallback")
        options = legal_moves(game.board)
        if not options:
            game.over = True
            return game.as_dict()
        try:
            direction = ExpectimaxAdvisor().suggest(game.board, game.score).direction
        except Exception:
            direction = options[0]
        game.apply(direction, source="expectimax fallback")
        game.fallback_count += 1
    response = game.as_dict()
    response["decision"] = {
        "direction": game.last_move,
        "provider": game.last_source,
        "fallback": fallback_used,
        "confidence": getattr(locals().get("suggestion"), "confidence", None),
    }
    return response
