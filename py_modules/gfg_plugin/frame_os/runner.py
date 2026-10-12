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
import math
import time
from typing import Any, Callable, Dict, Optional

from .benefit import BenefitMeter
from .burst import BurstCadence
from .control_channel import ControlChannel
from . import input_relay
from .input_sensor import EvdevReader, InputState
from .policy import Decision, EnergyBroker, InjectionPolicy
from .memory import EFFECTS
from .proof import ProofMeter
from .scene import SceneChangeDetector

MODES = ("observe", "shadow", "act")


def default_reader() -> EvdevReader:
    """The root relay's pipe when the plugin has one (shared, never closed here), else direct nodes."""
    fd = input_relay.relay_fd()
    if fd is not None:
        return EvdevReader(fds=[fd], owned=False, source="relay")
    return EvdevReader(fds=input_relay.direct_fds(), source="direct")


class FrameOsRunner:
    TICK_S = 0.1
    READER_RETRY_S = 5.0

    def __init__(self, channel: Optional[ControlChannel] = None, clock: Callable[[], float] = time.monotonic,
                 reader_factory: Optional[Callable[[], Any]] = None) -> None:
        self.channel = channel or ControlChannel()
        self.clock = clock
        self._reader_factory = reader_factory or default_reader
        self.reader: Any = None
        self._reader_at = 0.0
        self.mode = "observe"
        self.enabled = False
        self.policy: Optional[InjectionPolicy] = None
        self.scene = SceneChangeDetector()
        self.generation = 0
        self._published: Optional[tuple] = None
        self.last: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None
        self.draw_w: Optional[float] = None
        self.focused: Optional[bool] = None   # Gamescope focus from the renderer (Governor sets it)
        # The Governor's executor (adaptive overlay) is in place: only then may Act move the real
        # cadence and the watts; otherwise act paces at the point's own cadence.
        self.executor_active = False
        self.benefit = BenefitMeter()
        # A/B proof: rare short control windows turn the benefit estimates into measurements.
        self.proof = ProofMeter()
        self.ab_control: Optional[str] = None
        # per game (Frame OS memory): Act effects the A/B proof ruled out in this game
        self.latency_enabled = True
        self.stall_shield_enabled = False
        self.game_disabled: Dict[str, bool] = {"shaping": False, "boost": False, "rest": False}
        self.boost_enabled = True
        self.burst_cadence = BurstCadence()
        self.burst_observations = {"windows":0,"accelerated_windows":0,"seconds":0.0,"peak_real_hz":None}

    # ---------------------------------------------------------- Governor side (1 Hz)
    def configure(self, *, enabled: bool, mode: str, output_hz: float, calm_real_hz: float,
                  max_multiplier: float, calm_w: Optional[float],
                  latency_enabled: bool = True, stall_shield_enabled: bool = False,
                  touch_boost_enabled: bool = False, boost_enabled: bool = True) -> None:
        mode = mode if mode in MODES else "observe"
        was_enabled = self.enabled
        self.enabled, self.mode = bool(enabled), mode
        self.latency_enabled, self.stall_shield_enabled = bool(latency_enabled), bool(stall_shield_enabled)
        if self.boost_enabled and not boost_enabled:
            self.cancel_boost()
        self.boost_enabled = boost_enabled is True
        if not self.enabled:
            return
        if not was_enabled:
            # Fresh file per enable: the previous session's telemetry must not read as this one's.
            self.channel.reset()
            self._published = None
            self.benefit.reset()            # the rings are per game session
            self.proof.reset()
            self.ab_control = None
            self.policy = None              # no bank/backoff from the previous session
            self.burst_cadence = BurstCadence()
            self.burst_observations = {"windows":0,"accelerated_windows":0,"seconds":0.0,"peak_real_hz":None}
            self.scene = SceneChangeDetector()
            self.last = {}
            if self.reader is not None:
                self.reader.close()
                self.reader = None
        same = (self.policy is not None and self.policy.output_hz == output_hz
                and self.policy.calm_real_hz == calm_real_hz and self.policy.max_multiplier == max_multiplier)
        if not same:
            broker = EnergyBroker(calm_w=float(calm_w)) if calm_w else None
            self.policy = InjectionPolicy(output_hz=output_hz, calm_real_hz=calm_real_hz,
                                          max_multiplier=max_multiplier, broker=broker)
            self._apply_game_flags()
        elif calm_w:
            if self.policy.broker is None:
                self.policy.broker = EnergyBroker(calm_w=float(calm_w))
            else:
                self.policy.broker.calm_w = float(calm_w)   # the Governor moved the calm cap
        else:
            self.policy.broker = None  # power ownership was released
        self.policy.configure_touch_boost(touch_boost_enabled is True)
        self._apply_game_flags()
        self.proof.skip.add("frames")  # long A/B windows cannot measure these bounded pulses

    def apply_memory(self, disabled: Dict[str, bool], prior: Dict[str, Any]) -> None:
        """This game's memory: effects off here, and the A/B pairs earlier sessions measured."""
        self.game_disabled = {effect: bool((disabled or {}).get(effect)) for effect in self.game_disabled}
        self.proof.load({**(prior or {}), "frames": []}, skip={"frames"} | {m for m, e in EFFECTS.items() if self.game_disabled[e]})
        self._apply_game_flags()

    def set_disabled(self, disabled: Dict[str, bool]) -> None:
        """Effects newly ruled out mid-session: switch them off, keep this session's pairs."""
        self.game_disabled = {effect: bool((disabled or {}).get(effect)) for effect in self.game_disabled}
        self.proof.skip = {"frames"} | {m for m, e in EFFECTS.items() if self.game_disabled[e]}
        self._apply_game_flags()

    def _apply_game_flags(self) -> None:
        if self.policy is not None:
            self.policy.boost_allowed = self.boost_enabled and not self.game_disabled["boost"]
            self.policy.rest_allowed = not self.game_disabled["rest"]

    def cancel_boost(self) -> None:
        if self.policy is not None:
            self.policy.cancel_boost()
            broker = self.policy.broker
            self.last["decision"] = Decision("calm", self.policy.calm_real_hz, self.policy.output_hz,
                                             broker.calm_w if broker else None, "autopilot-scope-exit").to_dict()

    @property
    def injection(self) -> Optional[tuple]:
        """(boost_real_hz, rest_real_hz) while Act may move the real cadence, else None."""
        if not (self.enabled and self.mode == "act" and self.policy is not None):
            return None
        return self.policy.boost_real_hz, self.policy.rest_real_hz

    @property
    def tdp_offset_w(self) -> float:
        """Watts to add to the Governor's cap for the current level (act mode only)."""
        if not (self.enabled and self.mode == "act" and self.executor_active and self.policy and self.policy.broker):
            return 0.0
        return self._offset_for(self.last.get("decision") or {})

    def _offset_for(self, decision: Dict[str, Any]) -> float:
        if not (self.enabled and self.mode == "act" and self.executor_active and self.policy and self.policy.broker):
            return 0.0
        tdp = decision.get("tdp_w")
        deadline = decision.get("boost_until")
        if decision.get("level") == "boost" and isinstance(deadline, (int, float)) and self.clock() >= deadline:
            return 0.0
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
        if self.reader is None or (not self.reader.available and now - self._reader_at > self.READER_RETRY_S):
            if self.reader is not None:
                self.reader.close()
            self.reader = self._reader_factory()   # retried: Steam's virtual pad appears with the game
            self._reader_at = now
        state: InputState = self.reader.state
        self.reader.poll()
        inp = state.snapshot(time.time() if self.reader.available else now)
        telemetry = self.channel.read_telemetry() or {}
        burst_real_hz = self.burst_cadence.sample(telemetry)
        cost = telemetry.get("cost_p50_ms") or None
        cut = self.scene.tick(now, cost)
        decision = self.policy.tick(now, inp, scene_change=cut, draw_w=self.draw_w, focused=self.focused)
        acting = self.mode == "act"
        # A/B proof: what the game did under last tick's control, then this tick's control.
        self.proof.observe(now, eligible=acting and self.executor_active and bool(telemetry.get("live")),
                           level=decision.level, telemetry=telemetry, draw_w=self.draw_w)
        control = self.proof.control(now, decision.level) if acting and self.executor_active else None
        self.ab_control = control
        if control == "hold-calm":
            # The policy keeps its own level (the moment is unchanged); only the output is calm.
            broker = self.policy.broker
            decision = Decision("calm", self.policy.calm_real_hz, self.policy.output_hz,
                                broker.calm_w if broker is not None else None, "ab-control")
        if control == "hold-calm":
            # a held boost is not an ineffective one: never let a control window (or the calm
            # cadence it leaves in the pacer's interval ring) back boosts off
            self.policy._boost_since = None
            self.policy._delivery_at = now
        elif acting and self.executor_active and telemetry.get("live"):
            # without the executor the pacer gets the calm cadence: no boost can be delivered yet
            acknowledged_boost = ((self.last.get("decision") or {}).get("level") == "boost"
                                  and telemetry.get("applied_generation") == self.generation)
            if acknowledged_boost and burst_real_hz is not None:
                previous=self.last.get("decision") or {}
                window=self.burst_cadence.last
                start=max(window["start_monotonic_s"],previous.get("boost_since",window["start_monotonic_s"]))
                end=min(window["end_monotonic_s"],previous.get("boost_until",window["end_monotonic_s"]))
                exposure=max(0.0,end-start)
                if exposure>0:
                    self.policy.note_delivered(now, burst_real_hz, short_window=True,exposure_s=exposure)
                    self.burst_observations["windows"]+=1
                    self.burst_observations["seconds"]+=exposure
                    self.burst_observations["accelerated_windows"]+=burst_real_hz>=self.policy.calm_real_hz+max(1,self.policy.calm_real_hz*.05)
                    self.burst_observations["peak_real_hz"]=max(self.burst_observations["peak_real_hz"] or 0,burst_real_hz)
        real_hz = decision.real_hz if acting and self.executor_active else self.policy.calm_real_hz
        shaping = self.latency_enabled and control != "no-shaping" and not self.game_disabled["shaping"]
        wanted = (self.mode, round(real_hz, 3), shaping, self.stall_shield_enabled)
        if wanted != self._published:
            # Tick shaping must be able to move a frame start through most of a real-frame slot:
            # at 30 real a one-refresh cap (11 ms) leaves two thirds of the queueing in place.
            published = self.channel.write_policy(enabled=True, real_hz=real_hz, mode=self.mode,
                                      tick_shaping=shaping, pacing=True, generation=self._bump(),
                                      stall_shield=self.stall_shield_enabled,
                                      max_wait_ms=round(0.8 * 1000.0 / real_hz, 2) if real_hz > 0 else 0.0)
            self._published = wanted if published else None
        else:
            if not self.channel.heartbeat():
                self._published = None  # retry the full policy on the next tick
        # built in full, then published once: worker threads read ``last`` (review 1.3.0)
        last = {
            "enabled": True, "mode": self.mode, "input": inp, "scene_change": cut,
            "decision": decision.to_dict(), "acting": acting, "published_real_hz": real_hz,
            "generation": self.generation, "telemetry": telemetry,
            "latency_enabled": self.latency_enabled, "stall_shield_enabled": self.stall_shield_enabled,
            "acknowledged": self._published is not None and bool(telemetry.get("live"))
                            and telemetry.get("applied_generation") == self.generation,
            "input_sensor": self._sensor_status(inp), "ab_control": control,
            "game_disabled": dict(self.game_disabled),
            "boost_enabled": self.boost_enabled,
            "burst_cadence": dict(self.burst_cadence.last),
            "burst_observations":{**self.burst_observations,"seconds":round(self.burst_observations["seconds"],3),"gain_measured":False},
        }
        if decision.level == "boost" and self.policy._burst_started is not None:
            last["decision"]["boost_since"] = self.policy._burst_started
            last["decision"]["boost_until"] = min(max(self.policy._boost_until, self.policy._touch_until),
                                                    self.policy._burst_started + 1.5)
        requested = self.policy.touch_intent and decision.level == "boost"
        if not self.policy.touch_boost_enabled:
            touch_state = "off"
        elif not inp.get("touch_signal_fresh"):
            touch_state = "sensor-unavailable"
        elif self.focused is False:
            touch_state = "menu"
        elif not acting:
            touch_state = "observe-only"
        elif not self.executor_active:
            touch_state = "executor-unavailable"
        elif requested:
            touch_state = "submitted" if last["acknowledged"] else "requested"
        elif decision.reason in ("boost-ineffective", "boost-off-for-game", "energy-bank-empty", "ab-control"):
            touch_state = decision.reason
        else:
            touch_state = "armed"
        interval = telemetry.get("present_interval_p50_ms")
        last["touch_boost"] = {"enabled": self.policy.touch_boost_enabled, "state": touch_state,
            "touch_requests": self.policy.touch_requests, "intent": self.policy.touch_intent,
            "requested": requested, "submitted": bool(requested and acting and self.executor_active and last["acknowledged"]),
            "right_stick_touch": inp.get("right_stick_touch"), "signal_fresh": inp.get("touch_signal_fresh") is True,
            "target_real_hz": self.policy.boost_real_hz, "published_real_hz": real_hz,
            "observed_real_hz": 1000.0 / interval if type(interval) in (int, float) and math.isfinite(interval) and interval > 0 and telemetry.get("live") else None,
            "gain_measured": False}
        broker = self.policy.broker
        calm_w = broker.calm_w if broker is not None else None
        self.benefit.add(now, acting=acting, level=decision.level, telemetry=telemetry,
                         output_hz=self.policy.output_hz, calm_real_hz=self.policy.calm_real_hz,
                         boost_real_hz=self.policy.boost_real_hz, calm_w=calm_w,
                         tdp_w=(calm_w + self._offset_for(last["decision"])) if acting and calm_w else decision.tdp_w,
                         counted=control is None)
        proof = self.proof.summary()
        last["proof"] = proof
        last["benefit"] = apply_proof(self.benefit.summary(), proof)
        self.last = last
        return last

    def _sensor_status(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        status = dict(self.reader.status()) if hasattr(self.reader, "status") else {}
        idle = inp.get("idle_s")
        status.update(camera=inp.get("camera"), action=inp.get("action"),
                      idle_s=idle if isinstance(idle, (int, float)) and idle != float("inf") else None,
                      right_stick_touch=inp.get("right_stick_touch"), touch_signal_fresh=inp.get("touch_signal_fresh"),
                      gyro_dps=inp.get("gyro_dps"), touch_generation=inp.get("touch_generation"))
        return status

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
        if self._published is not None or getattr(self.channel, "_map", None) is not None:
            try:  # only a channel this runner used: never create the file just to say "off"
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
        self.enabled = False
        self.policy = None
        self.last = {"enabled": False}
        if hasattr(self.channel, "close"):
            self.channel.close()


def apply_proof(benefit: Dict[str, Any], proof: Dict[str, Any]) -> Dict[str, Any]:
    """Measured A/B means replace the model's numbers metric by metric; ``measured`` says which."""
    out = dict(benefit)
    measured = {}
    for metric, key in (("response", "response_pct"), ("frames", "frames_pct"), ("energy", "energy_pct")):
        combined = proof.get(metric) or {}
        # Earlier sessions/backends remain visible in proof.historical, but
        # only this session's controlled pairs can label a live ring measured.
        result = combined.get("session") if "session" in combined else combined
        result = result or {}
        measured[metric] = bool(result.get("measured"))
        if measured[metric]:
            out[key] = result.get("mean")
    out["measured"] = measured
    out["provenance"] = {metric: ("session-ab" if measured[metric] else "model-or-telemetry") for metric in measured}
    if any(measured.values()):
        out["ready"] = True
    return out
