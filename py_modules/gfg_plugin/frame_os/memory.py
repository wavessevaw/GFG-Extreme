"""Frame OS learns per game: A/B results carried across sessions, and the effects they rule out.

The A/B proof (``proof.py``) measures each Act effect in the player's own game.  One session's
pairs are few; a game's pairs over many sessions settle the question.  This memory keeps the most
recent pairs per game and turns them into a verdict per effect:

* ``helps``   — the 95 % interval is above zero;
* ``hurts``   — the interval is below zero: Act switches that effect off **for this game**;
* ``unclear`` — not enough pairs yet, or the interval spans zero.

Frames has one more verdict, ``useless``: boosts measured at less than ``USELESS_GAIN_PCT`` with the
interval's top under twice that.  The GPU cannot feed more real frames here, so a boost would
only spend watts; Act stops boosting in this game.  A ruled-out effect is re-checked after
``RECHECK_SESSIONS`` sessions (a patch or new settings can change the game), so a verdict never
locks forever.

Stored in the Governor's settings under ``frame_os_games``: plain JSON, per game prefix
(``game_model.game_prefix``), forgotten together with the Governor's game model.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .proof import METRICS, MIN_PAIRS, stats

KEEP_PAIRS = 40
USELESS_GAIN_PCT = 5.0
RECHECK_SESSIONS = 8
EFFECTS = {"response": "shaping", "frames": "boost", "energy": "rest"}


def verdict(metric: str, values: List[float]) -> str:
    s = stats(values)
    if not s["measured"] or s["low"] is None:
        return "unclear"
    if s["high"] < 0:
        return "hurts"
    if metric == "frames" and s["mean"] < USELESS_GAIN_PCT and s["high"] < 2 * USELESS_GAIN_PCT:
        return "useless"
    if s["low"] > 0:
        return "helps"
    return "unclear"


class GameMemory:
    """One game's record: ``{"pairs": {metric: [...]}, "sessions": n, "off": {effect: session}}``."""

    def __init__(self, record: Optional[Dict[str, Any]] = None) -> None:
        record = record if isinstance(record, dict) else {}
        pairs = record.get("pairs") if isinstance(record.get("pairs"), dict) else {}
        self.pairs: Dict[str, List[float]] = {
            m: [float(v) for v in (pairs.get(m) or []) if isinstance(v, (int, float))][-KEEP_PAIRS:]
            for m in METRICS}
        self.sessions = int(record.get("sessions") or 0)
        off = record.get("off") if isinstance(record.get("off"), dict) else {}
        self.off: Dict[str, int] = {k: int(v) for k, v in off.items() if k in EFFECTS.values()
                                    and isinstance(v, (int, float))}
        self.updated = float(record.get("updated") or 0.0)

    # -------------------------------------------------------------- what Act may do here
    def disabled(self) -> Dict[str, bool]:
        """Effects ruled out for this game (and not yet due for a re-check)."""
        return {effect: effect in self.off and self.sessions - self.off[effect] < RECHECK_SESSIONS
                for effect in EFFECTS.values()}

    def verdicts(self) -> Dict[str, str]:
        return {m: verdict(m, self.pairs[m]) for m in METRICS}

    # -------------------------------------------------------------- session in, session out
    def start_session(self) -> Dict[str, bool]:
        """A new game session: re-check effects whose ban is old enough (their old pairs go, so the
        re-check is not outvoted by the evidence that banned them)."""
        self.sessions += 1
        for effect, since in list(self.off.items()):
            if self.sessions - since >= RECHECK_SESSIONS:
                del self.off[effect]
                metric = next(m for m, e in EFFECTS.items() if e == effect)
                self.pairs[metric] = []
        return self.disabled()

    def add_pairs(self, new_pairs: Dict[str, List[float]]) -> Dict[str, str]:
        """Merge this session's new pairs; returns effects newly ruled out ({effect: verdict})."""
        changed: Dict[str, str] = {}
        for metric in METRICS:
            values = [float(v) for v in new_pairs.get(metric) or [] if isinstance(v, (int, float))]
            if not values:
                continue
            self.pairs[metric] = (self.pairs[metric] + values)[-KEEP_PAIRS:]
            v = verdict(metric, self.pairs[metric])
            effect = EFFECTS[metric]
            if v in ("hurts", "useless") and effect not in self.off:
                self.off[effect] = self.sessions
                changed[effect] = v
        self.updated = time.time()
        return changed

    def summary(self) -> Dict[str, Any]:
        return {"sessions": self.sessions, "verdicts": self.verdicts(), "disabled": self.disabled(),
                **{m: stats(self.pairs[m]) for m in METRICS}}

    def to_record(self) -> Dict[str, Any]:
        return {"pairs": {m: [round(v, 2) for v in self.pairs[m]] for m in METRICS},
                "sessions": self.sessions, "off": dict(self.off), "updated": round(self.updated)}


def seed_pairs(memory: GameMemory) -> Dict[str, List[float]]:
    """Earlier sessions' pairs, so the rings start measured when the game is already known."""
    return {m: list(memory.pairs[m]) for m in METRICS if len(memory.pairs[m]) >= MIN_PAIRS}
