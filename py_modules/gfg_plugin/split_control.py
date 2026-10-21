"""Power Split in GFG Extreme 3.0: the 2.x CPU clock cap (``power_split``) on a KEDAVRA point.

On the Steam Deck CPU and GPU share one power limit. In a GPU-bound game the CPU's boost clock
takes watts the GPU could use; ``PowerSplit`` lowers the CPU's maximum clock a level at a time
(100, 85, 70, 60, 50 %, never under 1.6 GHz), lifts it at once when real frames dip or the
busiest core nears its limit, and proves the effect with A/B/A windows. 2.x rules unchanged.

What 3.0 adds is when it may run, so it never mixes into another experiment:

* only on a locked, engine-confirmed point (not while the pilot measures or tries a point up);
* only while the Governor is settled (no TDP step in the last windows) and owns the TDP;
* not in Steam's menus, not without a game;
* every cap change restarts the Governor's and the pilot's measurement windows (``changes``),
  and while a level is on trial the pilot does not judge the point (``settling``).

Per-game memory (``SplitMemory``: pairs, the level that proved itself, "off" for games where it
measurably does nothing) is kept in its own file next to the settings.
"""
from __future__ import annotations

import statistics
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Optional, Tuple

from .power_split import PROBE_SETTLE_S, PowerSplit, Sample, SplitMemory, levels_khz
from .user_files import read_json, write_json_atomic

REAL_WINDOW_S = 5


class SplitControl:
    def __init__(self, cpu: Any, store: Optional[Path] = None, owner: Optional[Tuple[int, int]] = None,
                 clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.cpu = cpu
        self.store = Path(store) if store else None
        self.owner = owner
        self.clock = clock
        self.journal = journal
        self.games: Dict[str, Any] = read_json(self.store, {}) if self.store else {}
        if not isinstance(self.games, dict):
            self.games = {}
        self.split: Optional[PowerSplit] = None
        self.memory: Optional[SplitMemory] = None
        self.key: Optional[str] = None
        self.reals: Deque[float] = deque(maxlen=REAL_WINDOW_S)
        self.game_off = False
        self.changes = 0          # cap changes: measurement windows restart on each
        self.changed_at = -1e9
        self.status: Dict[str, Any] = {"phase": "off", "available": False}

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def _save(self) -> None:
        if self.store is None:
            return
        try:
            write_json_atomic(self.store, self.games, self.owner)
        except OSError:
            pass

    def _end(self) -> None:
        if self.split is not None and self.memory is not None and self.key:
            if self.memory.record(self.split):
                self.games[self.key] = self.memory.to_record()
                self._save()
        self.split = self.memory = None
        self.key = None
        self.reals.clear()
        if self.cpu.owned or getattr(self.cpu, "restore_pending", False):
            if self.cpu.restore():
                self._changed()

    def _changed(self) -> None:
        self.changes += 1
        self.changed_at = self.clock()

    def settling(self) -> bool:
        """A level is on trial or just changed: real frames say nothing about the point now."""
        s = self.split
        if s is None:
            return False
        return s.phase == "probe" or s.ab_phase is not None or self.clock() - self.changed_at < PROBE_SETTLE_S

    def tick(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """ctx: enabled, game, app (game key), steady (locked point, Governor settled, TDP owned),
        menu, point (base cap), real, sensors, draw_w, tdp_w."""
        now = self.clock()
        available = bool(self.cpu.discover())
        if getattr(self.cpu, "restore_pending", False):
            self.cpu.restore()
        if not ctx.get("game") or not available:
            self._end()
            self.status = {"enabled": bool(ctx.get("enabled")), "phase": "off", "available": available,
                           "reason": "no-game" if available else "no-cpufreq"}
            return self.status
        key = str(ctx.get("app") or "")
        if key != self.key:
            self._end()
            memory = SplitMemory(self.games.get(key))
            off = memory.start_session()
            split = PowerSplit(levels_khz(self.cpu.max_khz, self.cpu.min_khz))
            split.start_level = memory.level
            split.prior_pairs = list(memory.pairs)
            self.split, self.memory, self.key = split, memory, key
            self.game_off = off
            self.cpu.release_external()
            self.games[key] = memory.to_record()
            self._save()
            if memory.ruled_out:
                self._note("power-split-off", reason="no-measured-benefit", game=key, pairs=len(memory.pairs))
        split = self.split
        assert split is not None and self.memory is not None
        split.enabled = bool(ctx.get("enabled")) and not self.game_off
        if ctx.get("real") is not None:
            self.reals.append(float(ctx["real"]))
        sensors = ctx.get("sensors") or {}
        eligible = bool(ctx.get("steady") and not ctx.get("menu") and not self.cpu.external_change
                        and not getattr(self.cpu, "restore_pending", False))
        real = statistics.median(self.reals) if self.reals else None
        point = float(ctx.get("point") or 0)
        pairs_before = len(split.pairs)
        cap = split.step(now, eligible, Sample(
            real_fps=real, target_real=point, top_core_pct=sensors.get("cpu_top_core_pct"),
            gpu_busy_pct=sensors.get("gpu_busy_pct"), gpu_mhz=sensors.get("gpu_clock_mhz"),
            draw_w=ctx.get("draw_w"), tdp_w=ctx.get("tdp_w"), steady=bool(ctx.get("steady"))))
        # Claim the CPU clock only right before the first real cap, so the saved original is
        # the player's latest value.
        if cap is not None and not self.cpu.owned:
            if not self.cpu.claim():
                split.step(now, False, Sample(None, point, None, None, None, None, None))
                cap = None
        if self.cpu.owned:
            if cap is None and split.level == 0 and split.ab_phase is None:
                if self.cpu.restore():
                    self._changed()
            elif self.cpu.cap_khz != cap:
                if self.cpu.set_cap_khz(cap):
                    self._changed()
                else:
                    split.step(now, False, Sample(None, point, None, None, None, None, None))
                    self.cpu.restore()   # a partial write is undone from the actuator's journal
                    self._changed()
        change = split.last_change
        if change is not None:
            self._note("power-split", reason=change["reason"], cpu_khz=change["to_khz"],
                       before_khz=change["from_khz"], level=change["level"], tdp_w=ctx.get("tdp_w"), real=real,
                       top_core=sensors.get("cpu_top_core_pct"), gpu_busy=sensors.get("gpu_busy_pct"))
        if len(split.pairs) > pairs_before:
            self._note("power-split-ab", **split.pairs[-1])
            if self.memory.record(split):
                self.games[self.key] = self.memory.to_record()
                self._save()
        self.status = {**split.summary(), "available": True, "game_off": self.game_off,
                       "control": self.cpu.status()}
        return self.status

    def stop(self) -> None:
        """Plugin unload: the player's CPU clock limits come back."""
        self._end()
        try:
            self.cpu.shutdown()
        except Exception:
            pass
