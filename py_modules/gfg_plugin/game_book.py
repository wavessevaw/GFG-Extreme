"""What GFG Extreme knows about each game (user, 3.1.0): a starting hint from a list of well-known
titles, then what the Deck measured, kept per game so a known game is not measured again.

A profile is kept per game, refresh rate and display (handheld or dock):
  class        light / medium / heavy: measured on this Deck when known, else the list's hint
  point        the base frame cap the game held last time (a launch starts there, no full-power
               measurement; the pilot's guard still corrects it)
  medians      of the last sessions: real fps, TDP, APU draw (the player sees them, the next
               launch starts from them)

Classes (user): light games (DuckTales, Terraria) run well at 4-7 W and want no multiplier above
x2; heavy ones (The Witcher 3 next-gen, Death Stranding) start at the 15 W ceiling.
"""
from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

LIST_PATH = Path(__file__).resolve().parent / "data" / "games.json"
CLASSES = ("light", "medium", "heavy")
START_W = {"light": 7.0, "heavy": 15.0}
LIGHT_MAX_W = 7.5        # median TDP at the top point (x2) at or under this: a light game
KEEP_SESSIONS = 9
MIN_SESSION_MIN = 2.0
MAX_ENTRIES = 300


def load_list(path: Path = LIST_PATH) -> Dict[str, Dict[str, str]]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        games = raw.get("games", {})
        return {str(k): v for k, v in games.items() if isinstance(v, dict) and v.get("class") in CLASSES}
    except (OSError, ValueError, AttributeError):
        return {}


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


class GameBook:
    def __init__(self, path: Optional[Path], list_path: Path = LIST_PATH,
                 clock: Callable[[], float] = time.time, save: Optional[Callable[[Path, Any], None]] = None) -> None:
        self.path = Path(path) if path else None
        self.clock = clock
        self.save_fn = save
        self.known = load_list(list_path)
        self.entries: Dict[str, Dict[str, Any]] = {}
        if self.path:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and isinstance(raw.get("games"), dict):
                    self.entries = {k: v for k, v in raw["games"].items() if isinstance(v, dict)}
            except (OSError, ValueError):
                pass  # a damaged book never stops a game; it is rebuilt by playing

    @staticmethod
    def key(app: int, refresh: int, dock: bool) -> str:
        return f"app:{int(app)}|{int(refresh)}|{'dock' if dock else 'hand'}"

    def hint(self, app: int) -> Optional[Dict[str, str]]:
        return self.known.get(str(int(app or 0)))

    def profile(self, app: int, refresh: int, dock: bool) -> Dict[str, Any]:
        """The game as GFG knows it: class and where it comes from, the known point, the medians."""
        if not app:
            return {"class": None, "source": None}
        e = self.entries.get(self.key(app, refresh, dock), {})
        hint = self.hint(app)
        cls, source = e.get("class"), "measured"
        if cls not in CLASSES:
            cls, source = (hint["class"], "list") if hint else (None, None)
        out = {"class": cls, "source": source, "name": (hint or {}).get("name"),
               "point": e.get("point"), "sessions": len(e.get("sessions", []))}
        out.update(self.medians(e))
        return out

    @staticmethod
    def medians(e: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        sessions = e.get("sessions", [])
        for name in ("real", "tdp", "draw"):
            vals = [s[name] for s in sessions if _num(s.get(name)) is not None]
            out[f"median_{name}"] = round(statistics.median(vals), 1) if vals else None
        return out

    def _entry(self, app: int, refresh: int, dock: bool) -> Dict[str, Any]:
        k = self.key(app, refresh, dock)
        e = self.entries.setdefault(k, {"sessions": []})
        e["updated"] = self.clock()
        return e

    def note_point(self, app: int, refresh: int, dock: bool, point: int, tdp_w: Optional[float], top: int) -> None:
        """A point the Governor locked as stable: the next launch starts there. A game that holds
        the top point (x2) at light watts is a light game."""
        if not app or not point:
            return
        e = self._entry(app, refresh, dock)
        e["point"] = int(point)
        t = _num(tdp_w)
        if t is not None:
            e["point_tdp"] = round(t, 1)
            if point >= top and t <= LIGHT_MAX_W:
                e["class"] = "light"
            elif e.get("class") == "light" and (point < top or t > LIGHT_MAX_W + 2.0):
                e["class"] = "medium"
        self._save()

    def note_measure(self, app: int, refresh: int, dock: bool, held: int, steps: List[int]) -> None:
        """Full power held only x3 or less: a heavy game (unless already measured light)."""
        if not app or not held or len(steps) < 2:
            return
        e = self._entry(app, refresh, dock)
        if held <= steps[1]:
            e["class"] = "heavy"
        elif e.get("class") == "heavy":
            e["class"] = "medium"
        self._save()

    def not_light(self, app: int, refresh: int, dock: bool) -> None:
        """The list said light, the Deck could not hold x2 at full power: medium from now on."""
        if not app:
            return
        e = self._entry(app, refresh, dock)
        e["class"] = "medium"
        e.pop("point", None)
        self._save()

    def end_session(self, app: int, refresh: int, dock: bool, summary: Dict[str, Any]) -> None:
        if not app or (_num(summary.get("minutes")) or 0.0) < MIN_SESSION_MIN:
            return
        e = self._entry(app, refresh, dock)
        e.setdefault("sessions", []).append({
            "end": round(self.clock()), "minutes": summary.get("minutes"), "mode": summary.get("mode"),
            "real": _num(summary.get("avg_real_fps")), "tdp": _num(summary.get("avg_tdp_w")),
            "draw": _num(summary.get("avg_draw_w"))})
        e["sessions"] = e["sessions"][-KEEP_SESSIONS:]
        self._save()

    def _save(self) -> None:
        if not self.path:
            return
        if len(self.entries) > MAX_ENTRIES:
            for k in sorted(self.entries, key=lambda k: self.entries[k].get("updated", 0))[:len(self.entries) - MAX_ENTRIES]:
                del self.entries[k]
        data = {"version": 1, "games": self.entries}
        try:
            if self.save_fn:
                self.save_fn(self.path, data)
            else:
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, indent=1))
                tmp.replace(self.path)
        except OSError:
            pass
