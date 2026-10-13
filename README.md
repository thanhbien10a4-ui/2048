# Laya 2048 Lab

A web 2048 game with a human mode, an autonomous move button, and autoplay. The backend owns the game rules and asks Laya to choose among legal moves. A safe fallback keeps the game moving if the model is unavailable or returns an invalid answer.

## What this project demonstrates

- React + TypeScript game UI with keyboard controls and autoplay.
- FastAPI endpoints for game creation, moves, and AI decisions.
- A replaceable decision-engine interface: a no-download demo advisor or Laya's upstream PyTorch runtime.
- Basic measurements in the UI: score, moves, largest tile, chosen move, and whether fallback was used.

## Repository layout

```text
server/
  app/game.py       # deterministic 2048 rules and state
  app/advisor.py    # demo advisor and optional Laya adapter
  app/main.py       # FastAPI endpoints and in-memory game sessions
  tests/            # game-rule tests; no checkpoint download required
web/
  src/App.tsx       # board, controls, autoplay, decision status
  src/style.css     # responsive visual design
```

The browser owns presentation and input. The backend owns the authoritative board, score, legal-move checks, and AI provider. `advisor.py` is isolated so a later heuristic or benchmark agent can be added without changing the API or UI.

Laya is not trained specifically for 2048. This project is an experiment in structured decision making, not a claim that the model is a strong 2048 player. Game rules reject illegal moves; they do not prove that a legal move is strategically good.

## Requirements

- Python 3.11+
- Node.js 20+
- Windows, macOS, or Linux for the application shell.
- To run real Laya inference, install the upstream `laya` package. PyTorch supports CPU builds; CUDA requires a compatible NVIDIA GPU and driver. The `laya-mlx` runtime is a separate Mac Apple Silicon option.

## Run on Windows (PowerShell)

From the repository root, start the backend:

```powershell
cd server
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

In another terminal, start the frontend:

```powershell
cd web
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`. The backend starts with `AI_PROVIDER=demo`, so the app works without downloading model weights.

## Enable Laya

Install Laya into the backend environment and select it before starting FastAPI:

```powershell
cd server
python -m pip install -e ".[laya]"
$env:AI_PROVIDER = "laya"
uvicorn app.main:app --reload
```

The first real prediction downloads the selected checkpoint from Hugging Face. Ensure the machine has enough memory and network access for that download. If you want to use a CUDA build, install the PyTorch build matching your GPU before installing Laya; see [PyTorch's installer](https://pytorch.org/get-started/locally/).

## Game loop

1. The browser sends the current board and score to `POST /api/games/{id}/ai-move`.
2. FastAPI calculates legal directions and formats a compact state for Laya.
3. Laya returns one typed `choice` from the legal directions.
4. The game engine applies the move, merges tiles once per turn, adds a new tile, and returns the updated state.
5. If inference fails or produces an unusable direction, the backend picks the first legal direction and marks the turn as a fallback.

The fallback is deliberately visible. It is not presented as a Laya decision.

The starter keeps sessions in memory; restarting FastAPI clears them. That is intentional for a local demo. SQLite, authentication, deployment, and long-running background autoplay are follow-up work rather than hidden promises of this starter.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Provider status |
| `POST` | `/api/games` | Start a game |
| `GET` | `/api/games/{game_id}` | Read a game |
| `POST` | `/api/games/{game_id}/move` | Apply a human move |
| `POST` | `/api/games/{game_id}/ai-move` | Ask the configured advisor for a move |

Interactive API docs are at `http://localhost:8000/docs`.

## Tests

```powershell
cd server
python -m pip install -e ".[dev]"
pytest
```

Tests cover merge-once behavior, scoring, legal moves, and game-over detection. They do not load model weights. Add a labeled set of board states and compare Laya with random and heuristic baselines before making any claim about playing strength.

## Next steps

- Persist sessions and decision traces in SQLite.
- Add a heuristic/expectimax benchmark baseline.
- Add a seeded replay mode so model choices can be compared on identical boards.
- Measure model latency and invalid-answer/fallback rates over a fixed evaluation set.

## Attribution

The optional Laya backend uses the upstream [Laya project](https://github.com/NandhaKishorM/laya). The MLX-specific [laya-mlx project](https://github.com/mizorewww/laya-mlx) is not required and is not the backend used on Windows.
