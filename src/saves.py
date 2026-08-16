"""Save / load system: JSON slots + autosave."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from .config import MAX_SAVE_SLOTS, SAVES_DIR
from .game.gamestate import GameState
from .game.time import fmt_clock, fmt_date_short

SLOT_FILES = [SAVES_DIR / f"slot_{i}.json" for i in range(1, MAX_SAVE_SLOTS + 1)]
AUTOSAVE_FILE = SAVES_DIR / "autosave.json"
SAVE_VERSION = 1


def _meta(state: GameState) -> dict:
    from .game.time import game_date
    d = game_date(state.day)
    return {
        "day": state.day,
        "date": fmt_date_short(d, "ru"),
        "time": fmt_clock(state.minutes),
        "money": round(state.money, 2),
        "play_min": int(state.play_seconds // 60),
        "saved_at": time.strftime("%d.%m.%Y %H:%M"),
        "stage": state.plot_stage,
        "solved": state.ending,
    }


def _write(path: Path, state: GameState) -> bool:
    try:
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "version": SAVE_VERSION,
            "meta": _meta(state),
            "state": asdict(state),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return True
    except Exception:
        return False


def save_slot(state: GameState, slot: int) -> bool:
    if not 1 <= slot <= MAX_SAVE_SLOTS:
        return False
    return _write(SLOT_FILES[slot - 1], state)


def autosave(state: GameState) -> bool:
    return _write(AUTOSAVE_FILE, state)


def read_meta(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("meta")
    except Exception:
        return None


def list_saves() -> list[dict]:
    """Returns save entries: autosave first, then slots."""
    out = []
    if AUTOSAVE_FILE.exists():
        meta = read_meta(AUTOSAVE_FILE)
        if meta:
            out.append({"path": AUTOSAVE_FILE, "slot": 0, "meta": meta, "autosave": True})
    for i, p in enumerate(SLOT_FILES, start=1):
        if p.exists():
            meta = read_meta(p)
            if meta:
                out.append({"path": p, "slot": i, "meta": meta, "autosave": False})
    return out


def load_game(path: Path) -> GameState | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data["state"]
        known = {f for f in GameState.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in raw.items() if k in known}
        st = GameState(**filtered)
        st.new_game = False
        return st
    except Exception:
        return None


def delete_save(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
