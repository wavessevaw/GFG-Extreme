"""Bounded, append-only configuration history for GFG Extreme."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class ConfigJournal:
    """Store small profile diffs without turning the config file into a database."""

    SCHEMA = 1
    MAX_ENTRIES = 500
    MAX_BYTES = 2 * 1024 * 1024

    def __init__(self, config_dir: Path, logger: Any):
        self.path = config_dir / "gfg-extreme-config-journal.jsonl"
        self.log = logger

    @staticmethod
    def _changed(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        changed: Dict[str, Dict[str, Any]] = {}
        for key in sorted(set(before) | set(after)):
            old = before.get(key)
            new = after.get(key)
            if old != new:
                changed[key] = {"before": old, "after": new}
        return changed

    def append(
        self,
        profile: str,
        before: Dict[str, Any],
        after: Dict[str, Any],
        actor: str = "system",
        reason: str = "",
    ) -> Optional[Dict[str, Any]]:
        changes = self._changed(before, after)
        if not changes:
            return None
        now_ns = time.time_ns()
        entry: Dict[str, Any] = {
            "schema": self.SCHEMA,
            "id": f"{now_ns:x}-{os.getpid():x}",
            "timestamp": now_ns / 1_000_000_000,
            "profile": profile,
            "actor": str(actor or "system")[:32],
            "reason": str(reason or "")[:240],
            "changed_fields": list(changes),
            "changes": changes,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entries = self.list_entries(limit=self.MAX_ENTRIES - 1, newest_first=True)
        entries.reverse()
        entries.append(entry)
        payload = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in entries[-self.MAX_ENTRIES:])
        # Defensive size cap. Keep the newest complete records.
        encoded = payload.encode("utf-8")
        if len(encoded) > self.MAX_BYTES:
            kept: list[str] = []
            used = 0
            for item in reversed(entries):
                line = json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                size = len(line.encode("utf-8"))
                if kept and used + size > self.MAX_BYTES:
                    break
                kept.append(line)
                used += size
            payload = "".join(reversed(kept))
        temp = self.path.with_suffix(".jsonl.tmp")
        with open(temp, "w", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        temp.replace(self.path)
        return entry

    def list_entries(
        self,
        profile: str = "",
        limit: int = 20,
        newest_first: bool = True,
    ) -> list[Dict[str, Any]]:
        try:
            raw = self.path.read_bytes()
        except OSError:
            return []
        if len(raw) > self.MAX_BYTES:
            raw = raw[-self.MAX_BYTES:]
            newline = raw.find(b"\n")
            if newline >= 0:
                raw = raw[newline + 1:]
        values: list[Dict[str, Any]] = []
        for line in raw.decode("utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(item, dict) or item.get("schema") != self.SCHEMA:
                continue
            if profile and item.get("profile") != profile:
                continue
            if not isinstance(item.get("id"), str) or not isinstance(item.get("changes"), dict):
                continue
            values.append(item)
        if newest_first:
            values.reverse()
        return values[:max(0, min(int(limit), 100))]

    def find(self, entry_id: str) -> Optional[Dict[str, Any]]:
        for item in self.list_entries(limit=self.MAX_ENTRIES, newest_first=True):
            if item.get("id") == entry_id:
                return item
        return None
