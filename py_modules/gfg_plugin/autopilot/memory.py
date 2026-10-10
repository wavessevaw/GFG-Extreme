"""Bounded per-game lessons. Inconclusive trials are not stored.

The file is only this store. Reset deletes one game here and does not open
Frame OS memory or the existing game-model file.
"""
import json
import os
from hashlib import sha256

from .coordinator import MemoryView
from .experiments import TrialResult


SCHEMA = 1
MAX_GAMES = 24
MAX_LESSONS = 4
MAX_BLOCKS = 8


class AutopilotMemory:
    def __init__(self, path):
        self.path = path
        self.games = {}
        self.session = set()
        self._load()

    def record(self, identity, result, now, stale=False):
        if stale or not isinstance(result, TrialResult):
            return "stale"
        if result.verdict != "ACCEPT" or not result.learned or result.confidence is None:
            return "not-learned"
        if result.baseline_a1 is None or result.treatment_b is None or result.baseline_a2 is None:
            return "not-learned"
        key = _key(identity)
        if key is None:
            return "identity-missing"
        game = self.games.setdefault(key, {"lessons": [], "blocks": []})
        game["lessons"].append({
            "knob": identity["knob"], "value": identity["value"], "at": now,
            "context": identity["context"], "verified": False,
            "real_gain": result.treatment_b.get("real"),
        })
        game["lessons"] = game["lessons"][-MAX_LESSONS:]
        self._trim()
        self._save()
        return None

    def block(self, identity, now, seconds):
        key = _key(identity)
        if key is None:
            return "identity-missing"
        game = self.games.setdefault(key, {"lessons": [], "blocks": []})
        game["blocks"].append({
            "knob": identity["knob"], "value": identity["value"],
            "context": identity["context"], "until": now + seconds,
        })
        game["blocks"] = game["blocks"][-MAX_BLOCKS:]
        self._trim()
        self._save()
        return None

    def warm(self, identity):
        game = self.games.get(_key(identity)) or {}
        return tuple(dict(lesson, verified=False) for lesson in game.get("lessons") or [])

    def confirm(self, identity, knob, value, fresh):
        if not fresh:
            return False
        game = self.games.get(_key(identity))
        if not game:
            return False
        for lesson in game["lessons"]:
            if lesson["knob"] == knob and lesson["value"] == value:
                self.session.add((_key(identity), knob, value))
                return True
        return False

    def verified_now(self, identity, knob, value):
        return (_key(identity), knob, value) in self.session

    def view(self, identity, now, context):
        game = self.games.get(_key(identity)) or {}
        blocked = tuple((item["knob"], item["value"]) for item in game.get("blocks") or []
                        if item.get("context") == context and item.get("until", 0) > now)
        return MemoryView(blocked=blocked)

    def reset(self, identity):
        self.games.pop(_key(identity), None)
        self._save()

    def _trim(self):
        if len(self.games) <= MAX_GAMES:
            return
        for key in list(self.games)[:-MAX_GAMES]:
            self.games.pop(key, None)

    def _load(self):
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError, UnicodeError):
            self.games = {}
            return
        if not isinstance(raw, dict):
            self.games = {}
            return
        schema = raw.get("schema", 0)
        games = raw.get("games") if isinstance(raw.get("games"), dict) else {}
        if schema != SCHEMA:
            games = _migrate(games)
            self.games = games
            self._save()
            return
        self.games = games

    def _save(self):
        payload = json.dumps({"schema": SCHEMA, "games": self.games}, sort_keys=True, separators=(",", ":"))
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(payload)
        os.replace(temporary, self.path)


def _key(identity):
    if not isinstance(identity, dict):
        return None
    app = identity.get("app_id") or identity.get("profile")
    if not isinstance(app, str) or not app:
        return None
    body = {name: identity.get(name) for name in ("panel", "hz", "gpu", "backend")}
    body["app"] = app
    if any(value in (None, "") for value in body.values()):
        return None
    return sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _migrate(games):
    kept = {}
    for key, game in games.items():
        if not isinstance(game, dict):
            continue
        lessons = [lesson for lesson in game.get("lessons") or []
                   if isinstance(lesson, dict) and lesson.get("verdict") == "ACCEPT" and lesson.get("learned") is True]
        for lesson in lessons:
            lesson["verified"] = False
        kept[key] = {"lessons": lessons[-MAX_LESSONS:], "blocks": []}
    return kept
