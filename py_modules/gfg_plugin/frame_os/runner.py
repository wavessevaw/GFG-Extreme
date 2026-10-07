"""Frame OS supervisor loop: 10 Hz, between the Governor (1 Hz) and the gfg-pacer layer (per frame).

Each tick: read the gamepad, read the layer's telemetry, detect scene changes, let the injection
policy decide (calm / boost / rest), and publish the layer policy.

Rollout gates (docs/GFG_FRAME_OS.md): the mode decides what the layer is allowed to do.
* ``observe`` — the layer only measures; decisions are computed and reported as "would".
* ``shadow``  — the layer runs its scheduler without sleeping; decisions still "would".
* ``act``     — the layer paces/tick-shapes; boosts change the real cadence and the TDP offset.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional

from .control_channel import ControlChannel
from .input_sensor import EvdevReader, InputState, gamepad_nodes
from .policy import EnergyBroker, InjectionPolicy
from .scene import SceneChangeDetector

MODES = ("observe", "shadow", "act")


class FrameOsRunner:
    TICK_S = 0.1

    def __init__(self, channel: Optional[ControlChannel] = None, clock: Callable[[], float] = time.monotonic,
                 reader_factory: Optional[Callable[[], Any]] = None) -> None:
        self.channel = channel or ControlChannel()
        self.clock = clock
        self._reader_factory = reader_factory or (lambda: EvdevReader(gamepad_nodes()))
        self.reader: Any = None
        self.mode = "observe"
        self.enabled = False
        self.policy: Optional[InjectionPolicy] = None
        self.scene = SceneChangeDetector()
        self.generation = 0
        self._published: Optional[tuple] = None
        self.last: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None
        self.draw_w: Optional[float] = None

    # ---------------------------------------------------------- Governor side (1 Hz)
    def configure(self, *, enabled: bool, mode: str, output_hz: float, calm_real_hz: float,
                  max_multiplier: float, calm_w: Optional[float]) -> None:
        mode = mode if mode in MODES else "observe"
        self.enabled, self.mode = bool(enabled), mode
        if not self.enabled:
            return
        same = (self.policy is not None and self.policy.output_hz == output_hz
                and self.policy.calm_real_hz == calm_real_hz and self.policy.max_multiplier == max_multiplier)
        if not same:
            broker = EnergyBroker(calm_w=float(calm_w)) if calm_w else None
            self.policy = InjectionPolicy(output_hz=output_hz, calm_real_hz=calm_real_hz,
                                          max_multiplier=max_multiplier, broker=broker)
        elif self.policy.broker is not None and calm_w:
            self.policy.broker.calm_w = float(calm_w)   # the Governor moved the calm cap

    @property
    def tdp_offset_w(self) -> float:
        """Watts to add to the Governor's cap for the current level (act mode only)."""
        if not (self.enabled and self.mode == "act" and self.policy and self.policy.broker):
            return 0.0
        decision = self.last.get("decision") or {}
        tdp = decision.get("tdp_w")
        return round(float(tdp) - self.policy.broker.calm_w, 1) if tdp is not None else 0.0

    # ---------------------------------------------------------- 10 Hz tick
    def tick(self, now: Optional[float] = None) -> Dict[str, Any]:
        now = self.clock() if now is None else now
        if not self.enabled or self.policy is None:
            if self._published is not None:
                self.channel.write_policy(enabled=False, real_hz=0.0, generation=self._bump())
                self._published = None
            self.last = {"enabled": False}
            return self.last
        if self.reader is None:
            self.reader = self._reader_factory()
        state: InputState = self.reader.state
        self.reader.poll()
        inp = state.snapshot(time.time() if self.reader.available else now)
        telemetry = self.channel.read_telemetry() or {}
        cost = telemetry.get("cost_p50_ms") or None
        cut = self.scene.tick(now, cost)
        decision = self.policy.tick(now, inp, scene_change=cut, draw_w=self.draw_w)
        acting = self.mode == "act"
        real_hz = decision.real_hz if acting else self.policy.calm_real_hz
        wanted = (self.mode, round(real_hz, 3))
        if wanted != self._published:
            self.channel.write_policy(enabled=True, real_hz=real_hz, mode=self.mode,
                                      tick_shaping=True, pacing=True, generation=self._bump())
            self._published = wanted
        self.last = {
            "enabled": True, "mode": self.mode, "input": inp, "scene_change": cut,
            "decision": decision.to_dict(), "acting": acting, "published_real_hz": real_hz,
            "generation": self.generation, "telemetry": telemetry,
            "acknowledged": telemetry.get("applied_generation") == self.generation if telemetry else False,
        }
        return self.last

    def _bump(self) -> int:
        self.generation = (self.generation + 1) & 0xFFFFFFFF
        return self.generation

    # ---------------------------------------------------------- lifecycle
    async def run(self) -> None:
        try:
            while True:
                try:
                    self.tick()
                except Exception as error:  # the supervisor never takes the game down
                    self.last = {"enabled": self.enabled, "error": str(error)}
                await asyncio.sleep(self.TICK_S)
        finally:
            self.close()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self.run())

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self.close()

    def close(self) -> None:
        try:
            self.channel.write_policy(enabled=False, real_hz=0.0, generation=self._bump())
        except Exception:
            pass
        if self.reader is not None:
            try:
                self.reader.close()
            except Exception:
                pass
            self.reader = None
        self._published = None
