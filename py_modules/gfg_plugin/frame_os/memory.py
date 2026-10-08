"""Frame OS learns per game: A/B results carried across sessions, and the effects they rule out.

The A/B proof (``proof.py``) measures each Act effect in the player's own game.  One session's
pairs are few; a game's pairs over many sessions settle the question.  This memory keeps the most
recent pairs per game and turns them into a verdict per effect:

* ``helps``   — the 95 % interval is above zero;
* ``hurts``   — clearly worse: the 99 % interval's top under ``-HARM_PCT``;
* ``unclear`` — not enough pairs yet, or the interval spans zero.

Frames has one more verdict, ``useless``: boosts measured at less than ``USELESS_GAIN_PCT`` with the
99 % interval's top under 1.5 times that.  The GPU cannot feed more real frames here, so a boost would
only spend watts.

Switching an effect off is decided **once per session, at its start** (never after every new pair:
re-testing a growing sample would switch off harmless effects by chance), and only on at least
``MIN_OFF_PAIRS`` pairs from at least two sessions (review 1.3.0: three pairs and a re-check per pair
switched a 0 % effect off in 15-44 % of games).  A ruled-out effect is re-checked after
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
MIN_OFF_PAIRS = 8
HARM_PCT = 2.0
USELESS_GAIN_PCT = 5.0
RECHECK_SESSIONS = 8
EFFECTS = {"response": "shaping", "frames": "boost", "energy": "rest"}


def verdict(metric: str, values: List[float]) -> str:
    s = stats(values)
    if not s["measured"] or s["low"] is None:
        return "unclear"
    strict = stats(values, confidence=0.99)
    if strict["high"] < -HARM_PCT:
        return "hurts"
    if metric == "frames" and s["mean"] < USELESS_GAIN_PCT and strict["high"] < 1.5 * USELESS_GAIN_PCT:
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
        # how many sessions contributed pairs per metric (records from 1.3.0 have no count: 1)
        seen = record.get("pair_sessions") if isinstance(record.get("pair_sessions"), dict) else {}
        self.pair_sessions: Dict[str, int] = {
            m: int(seen.get(m) or (1 if self.pairs[m] else 0)) for m in METRICS}
        self._added: set = set()        # metrics with pairs from the current session
        self.sessions = int(record.get("sessions") or 0)
        off = record.get("off") if isinstance(record.get("off"), dict) else {}
        self.off: Dict[str, int] = {k: int(v) for k, v in off.items() if k in EFFECTS.values()
                                    and isinstance(v, (int, float))}
        self.updated = float(record.get("updated") or 0.0)
        self.ruled_out: Dict[str, str] = {}      # switched off at this session's start

    # -------------------------------------------------------------- what Act may do here
    def disabled(self) -> Dict[str, bool]:
        """Effects ruled out for this game (and not yet due for a re-check)."""
        return {effect: effect in self.off and self.sessions - self.off[effect] < RECHECK_SESSIONS
                for effect in EFFECTS.values()}

    def verdicts(self) -> Dict[str, str]:
        return {m: verdict(m, self.pairs[m]) for m in METRICS}

    # -------------------------------------------------------------- session in, session out
    def start_session(self) -> Dict[str, bool]:
        """A new game session: decide switch-offs from everything measured so far (once per
        session), and re-check effects whose ban is old enough (their old pairs go, so the
        re-check is not outvoted by the evidence that banned them)."""
        self.ruled_out = {}
        for metric in METRICS:
            effect = EFFECTS[metric]
            values = self.pairs[metric]
            if (effect not in self.off and len(values) >= MIN_OFF_PAIRS and self.pair_sessions[metric] >= 2):
                v = verdict(metric, values)
                if v in ("hurts", "useless"):
                    self.off[effect] = self.sessions + 1
                    self.ruled_out[effect] = v
        self.sessions += 1
        self._added = set()
        for effect, since in list(self.off.items()):
            if self.sessions - since >= RECHECK_SESSIONS:
                del self.off[effect]
                metric = next(m for m, e in EFFECTS.items() if e == effect)
                self.pairs[metric] = []
                self.pair_sessions[metric] = 0
        return self.disabled()

    def add_pairs(self, new_pairs: Dict[str, List[float]]) -> Dict[str, str]:
        """Store this session's new pairs.  Nothing is switched off here: that waits for the next
        session's start.  Returns {} (kept for callers that react to switch-offs)."""
        for metric in METRICS:
            values = [float(v) for v in new_pairs.get(metric) or [] if isinstance(v, (int, float))]
            if not values:
                continue
            self.pairs[metric] = (self.pairs[metric] + values)[-KEEP_PAIRS:]
            if metric not in self._added:
                self._added.add(metric)
                self.pair_sessions[metric] += 1
        self.updated = time.time()
        return {}

    def summary(self) -> Dict[str, Any]:
        return {"sessions": self.sessions, "verdicts": self.verdicts(), "disabled": self.disabled(),
                **{m: stats(self.pairs[m]) for m in METRICS}}

    def to_record(self) -> Dict[str, Any]:
        return {"pairs": {m: [round(v, 2) for v in self.pairs[m]] for m in METRICS},
                "pair_sessions": dict(self.pair_sessions),
                "sessions": self.sessions, "off": dict(self.off), "updated": round(self.updated)}


def seed_pairs(memory: GameMemory) -> Dict[str, List[float]]:
    """Earlier sessions' pairs, so the rings start measured when the game is already known."""
    return {m: list(memory.pairs[m]) for m in METRICS if len(memory.pairs[m]) >= MIN_PAIRS}
