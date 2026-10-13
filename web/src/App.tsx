import { useCallback, useEffect, useRef, useState } from "react";

type Direction = "up" | "down" | "left" | "right";
type Game = {
  id: string; board: number[][]; score: number; moves: number; max_tile: number;
  won: boolean; over: boolean; legal_moves: Direction[]; last_move: Direction | null;
  last_source: string | null; fallback_count: number;
  decision?: { direction: Direction; provider: string; fallback: boolean; confidence: number | null };
};

const arrows: Record<Direction, string> = { up: "↑", down: "↓", left: "←", right: "→" };
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [game, setGame] = useState<Game | null>(null);
  const [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("Dùng phím mũi tên hoặc để Laya tự chơi.");
  const autoRef = useRef(false);

  const start = useCallback(async () => {
    setAuto(false); autoRef.current = false; setError("");
    try { setGame(await request<Game>("/api/games", { method: "POST" })); }
    catch (e) { setError((e as Error).message); }
  }, []);

  const humanMove = useCallback(async (direction: Direction) => {
    if (!game || busy || game.over) return;
    setBusy(true); setError("");
    try { setGame(await request<Game>(`/api/games/${game.id}/move`, { method: "POST", body: JSON.stringify({ direction }) })); setNotice(`Bạn đã đi ${arrows[direction]}.`); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }, [game, busy]);

  const aiMove = useCallback(async () => {
    if (!game || busy || game.over) return false;
    setBusy(true); setError("");
    try {
      const result = await request<Game>(`/api/games/${game.id}/ai-move`, { method: "POST" });
      setGame(result);
      const decision = result.decision;
      setNotice(decision?.fallback
        ? `Fallback đã chọn ${arrows[result.last_move ?? "left"]}; không tính là quyết định của Laya.`
        : `${decision?.provider ?? "AI"} chọn ${arrows[result.last_move ?? "left"]}${decision?.confidence == null ? "" : ` · confidence ${decision.confidence.toFixed(2)}`}.`);
      return true;
    } catch (e) { setError((e as Error).message); return false; }
    finally { setBusy(false); }
  }, [game, busy]);

  useEffect(() => { void start(); }, [start]);
  useEffect(() => { autoRef.current = auto; }, [auto]);
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      const direction: Record<string, Direction> = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
      const selected = direction[event.key];
      if (selected) { event.preventDefault(); void humanMove(selected); }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [humanMove]);
  useEffect(() => {
    if (!auto) return;
    const timer = window.setInterval(() => { if (autoRef.current) void aiMove(); }, 700);
    return () => window.clearInterval(timer);
  }, [auto, aiMove]);

  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">L</span><span>Laya 2048 <i>LAB</i></span></div><span className="top-caption">TYPED DECISIONS · GAME EXPERIMENT</span></header>
    <section className="layout">
      <div className="intro">
        <p className="eyebrow">A SMALL DECISION, ONE MOVE AT A TIME</p>
        <h1>Can Laya<br/><em>reach 2048?</em></h1>
        <p className="lede">Laya reads the board and chooses one legal direction. You can take over whenever you like.</p>
        <div className="score-row"><div className="score-card"><span>SCORE</span><strong>{game?.score ?? 0}</strong></div><div className="score-card"><span>BEST TILE</span><strong>{game?.max_tile ?? 0}</strong></div></div>
        <div className="button-row"><button className="button primary" disabled={busy || !game || game.over} onClick={() => void aiMove()}>{busy ? "Thinking…" : "✦  Laya move"}</button><button className="button secondary" disabled={busy || !game || game.over} onClick={() => setAuto(v => !v)}>{auto ? "Ⅱ  Pause" : "▶  Autoplay"}</button></div>
        <button className="new-game" onClick={() => void start()}>↻ New game</button>
        <div className="decision-card"><div className="decision-heading"><span className="status-dot"/><span>LAST DECISION</span><span className="move-pill">{game?.last_move ? arrows[game.last_move] : "—"}</span></div><p>{notice}</p><div className="decision-meta"><span>{game?.moves ?? 0} moves</span><span>{game?.fallback_count ?? 0} fallback moves</span></div></div>
        {error && <div className="error">{error}</div>}
      </div>
      <div className="game-column">
        <div className="board-frame">
          <div className="board" role="grid" aria-label="2048 board">
            {(game?.board ?? Array.from({ length: 4 }, () => Array(4).fill(0))).flatMap((row, r) => row.map((value, c) => <div role="gridcell" key={`${r}-${c}`} className={`cell tile-${value || "empty"}`}>{value || ""}</div>))}
          </div>
          {game?.over && <div className="overlay"><b>Game over</b><span>Score {game.score}</span><button className="button primary" onClick={() => void start()}>Play again</button></div>}
          {game?.won && !game.over && <div className="win-badge">2048 reached · keep going!</div>}
        </div>
        <div className="board-footer"><span>MOVE {String(game?.moves ?? 0).padStart(3, "0")}</span><span>MODEL · {game?.last_source?.toUpperCase() ?? "READY"}</span></div>
        <div className="controls"><span>KEYBOARD</span>{(["up", "left", "down", "right"] as Direction[]).map(d => <button key={d} aria-label={d} onClick={() => void humanMove(d)}>{arrows[d]}</button>)}<small>ARROW KEYS</small></div>
        <p className="fineprint">Experimental agent · the game engine enforces legal moves. A valid move is not necessarily a good move.</p>
      </div>
    </section>
    <footer><span>BUILT FOR CURIOSITY</span><span>2048 × STRUCTURED DECISIONS</span></footer>
  </main>;
}
