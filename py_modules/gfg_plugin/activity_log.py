"""User-action journal: what was clicked, launched and changed, in order.

One JSON object per line in ``runtime-state/activity.jsonl``.  Writers are the
plugin (every UI call that changes something, with its result), the Governor
(state changes, TDP writes, game exit) and the launch wrapper (one line per
game launch, written by bash).  The log recorder exports it with every bundle,
so a field log shows the user's own sequence of actions next to the Governor's
decisions.
"""
from __future__ import annotations

import functools
import inspect
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

MAX_BYTES = 2 * 1024 * 1024
KEEP_LINES = 4000
_VALUE_LIMIT = 200

# Read-only calls the UI polls; logging them would bury the real actions.
_QUIET_PREFIXES = ("get_", "check_")


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _compact(v) for k, v in list(value.items())[:40]}
    if isinstance(value, (list, tuple)):
        return [_compact(v) for v in list(value)[:40]]
    if isinstance(value, str) and len(value) > _VALUE_LIMIT:
        return value[:_VALUE_LIMIT] + "…"
    if isinstance(value, (int, float, bool)) or value is None or isinstance(value, str):
        return value
    return str(value)[:_VALUE_LIMIT]


class ActivityLog:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.clock = clock
        self._lock = threading.Lock()

    def record(self, source: str, kind: str, **fields: Any) -> None:
        payload: Dict[str, Any] = {"ts": round(self.clock(), 3), "source": source, "kind": kind}
        payload.update({k: _compact(v) for k, v in fields.items()})
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                if self.path.stat().st_size > MAX_BYTES:
                    lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()[-KEEP_LINES:]
                    temp = self.path.with_suffix(".tmp")
                    temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    temp.replace(self.path)
            except OSError:
                pass

    def since(self, ts: float) -> list[str]:
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        out = []
        for line in text.splitlines():
            try:
                if float(json.loads(line).get("ts", 0)) >= ts:
                    out.append(line)
            except (ValueError, TypeError, AttributeError):
                continue
        return out


def _result_summary(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        summary: Dict[str, Any] = {}
        if "success" in result:
            summary["success"] = bool(result.get("success"))
        for key in ("error", "message", "state", "reason", "enabled", "file"):
            if result.get(key) not in (None, ""):
                summary[key] = result.get(key)
        return summary
    return {"result": result}


def journal_ui_calls(cls: type, get_log: Callable[[Any], Optional[ActivityLog]]) -> type:
    """Wrap every public coroutine of the Decky plugin class that is not a poll."""
    for name, function in list(vars(cls).items()):
        if name.startswith("_") or name.startswith(_QUIET_PREFIXES) or not inspect.iscoroutinefunction(function):
            continue

        def wrap(fn: Callable[..., Any], method: str) -> Callable[..., Any]:
            parameters = list(inspect.signature(fn).parameters)[1:]

            @functools.wraps(fn)
            async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                log = get_log(self)
                arguments = dict(zip(parameters, args))
                arguments.update(kwargs)
                try:
                    result = await fn(self, *args, **kwargs)
                except Exception as error:
                    if log is not None:
                        log.record("ui", method, args=arguments, success=False, error=str(error))
                    raise
                if log is not None:
                    log.record("ui", method, args=arguments, **_result_summary(result))
                return result

            return wrapper

        setattr(cls, name, wrap(function, name))
    return cls
