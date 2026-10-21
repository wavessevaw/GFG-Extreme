"""GFG Extreme 3.0 service: one tick a second that ties everything together.

  engine status -> rates -> profile -> objective (Autopilot) -> point (pilot) -> policy
  (Coordinator, confirmed by the engine) -> TDP (Governor) -> HUD -> telemetry

Everything that touches the Deck is injected (engine control, TDP actuator, sensors,
battery), so the sandbox runs this same code against a virtual Deck.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from . import filters
from .autopilot import Autopilot
from .governor import PowerGovernor
from .kedavra import hud as hudmod
from .pilot import PointPilot
from .policy import Policy, PolicyCoordinator
from .session_stats import SessionStats

GAME_GRACE_S = 10.0   # the QAM or a loading screen does not end a game session
STEAM_APP = 769


class Service:
    def __init__(self, *, settings: Any, ctl: Any, actuator: Any, model: Any, sensors: Any,
                 battery: Callable[[], Dict[str, Any]], hud: Optional[Any] = None,
                 hud_path: str = "", clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None, telemetry: Optional[Any] = None) -> None:
        self.settings = settings
        self.ctl = ctl
        self.clock = clock
        self.journal = journal
        self.telemetry = telemetry
        self.sensors = sensors
        self.battery = battery
        self.hud = hud
        self.hud_path = hud_path
        self.coord = PolicyCoordinator(ctl, clock=clock, journal=self._j("policy"))
        self.pilot = PointPilot(clock=clock, journal=self._j("pilot"))
        self.autopilot = Autopilot(clock=clock)
        self.governor = PowerGovernor(actuator, model, clock=clock, journal=self._j("governor"))
        self.rates = hudmod.Rates()
        self.stats = SessionStats()
        self.last_game_at = -1e9
        self.app = 0
        self.last_policy: Optional[Policy] = None
        self.snapshot: Dict[str, Any] = {}
        self.ticks = 0

    def _j(self, source: str) -> Optional[Callable[..., None]]:
        if not self.journal:
            return None
        return lambda kind, **f: self.journal(source, kind, **f)

    # ------------------------------------------------------------------ tick
    def tick(self) -> Dict[str, Any]:
        now = self.clock()
        self.ticks += 1
        st = self.ctl.status() or {}
        fresh = bool(st.get("fresh"))
        rates = self.rates.update(st) if fresh else None
        if not fresh:
            self.rates.prev = None
        live = hudmod.live_for(st if fresh else {}, rates)
        app = int(st.get("app_id") or 0) if fresh else 0
        if app and app != STEAM_APP:
            if app != self.app:
                self._end_session("game-change")
                self.app = app
                self.stats.start(app, now)
            self.last_game_at = now
        game = bool(self.app) and now - self.last_game_at <= GAME_GRACE_S
        if not game and self.app:
            self._end_session("game-exit")
            self.app = 0

        data = self.settings.data
        profile_key, profile = self.settings.profile_for(self.app)
        sensors = self.sensors.sample() if self.sensors else {}
        power = self.battery() if self.battery else {}
        temp = sensors.get("temp_c")
        objective = profile["objective"]
        auto_reason = ""
        if objective == "autopilot":
            ap = self.autopilot.decide(data["autopilot"]["preference"], power, temp)
            objective, auto_reason = ap["objective"], ap["reason"]
        refresh = round(1e9 / st["refresh_ns"]) if fresh and st.get("refresh_ns") else 90

        confirmed = self.coord.engine_runs(self.last_policy, st)
        gov = self.governor
        req = self.pilot.tick({
            "fg": profile["fg"], "base_fps": profile["base_fps"], "objective": objective,
            "refresh": refresh, "game": game, "app": self.app, "engine": st,
            "real": live.get("real"), "pace": live.get("pace"), "confirmed": confirmed,
            "at_ceiling": gov.at_ceiling(),
        })
        policy = Policy(req["multiplier"], req["base_fps"], filters.to_post(profile["filters"]),
                        self.hud_path, req["auto_floor"], bool(data["engine"]["hdr"]))
        self.coord.want(policy)
        self.last_policy = policy
        coord = self.coord.tick(st)

        gov.enabled = bool(data["power"]["enabled"])
        locked = req["phase"] in ("locked", "fixed") and confirmed
        sample = {
            "game": game, "key": f"app:{self.app}|{refresh}", "objective": objective,
            "cap": req["point"] if locked else 0, "hold_ceiling": req["hold_ceiling"],
            "epoch": coord["epoch"], "real": live.get("real"), "pace": live.get("pace"),
            "over_budget": (rates or {}).get("over_budget", 0.0), "ring_miss": 0.0, "temp_c": temp,
        }
        if rates is not None and self.rates.prev is not None:
            sample["ring_miss"] = self._delta(st, "ring_miss")
            sample["over_budget"] = self._delta(st, "over_budget")
        g = gov.tick(sample)

        hud_cfg = data["hud"]
        if self.hud is not None:
            extra = {"tdp_w": g.get("tdp_w") if g.get("owned") else None, "draw_w": g.get("draw_w"),
                     "ceiling_w": g.get("ceiling_w"), "temp_c": temp, "managing": g.get("managing")}
            try:
                self.hud.tick(bool(hud_cfg["enabled"]) and game, st if fresh else None, extra,
                              hud_cfg["position"], hud_cfg["detail"])
            except OSError:
                pass
        if game:
            self.stats.add(now, output=live.get("fps"), real=live.get("real"), tdp=g.get("tdp_w"),
                           draw=g.get("draw_w"), reference_w=g.get("ceiling_w"), temp_c=temp,
                           stuttering=(live.get("pace") or 1.0) < 0.97, hot=(temp or 0) >= 85,
                           mode=objective)
        self.snapshot = {
            "time": now, "game": game, "app": self.app, "profile": profile_key, "profile_name": profile["name"],
            "fg": profile["fg"], "objective": objective, "objective_setting": profile["objective"],
            "autopilot_reason": auto_reason, "refresh": refresh, "engine": self._engine_view(st),
            "live": live, "pilot": req, "policy": coord, "governor": g, "sensors": sensors, "power": power,
            "filters": filters.summary(profile["filters"]),
        }
        if self.telemetry is not None and game:
            self.telemetry.sample({"t": round(time.time(), 1), "app": self.app, "fps": live.get("fps"),
                                   "real": live.get("real"), "pace": live.get("pace"), "point": req["point"],
                                   "phase": req["phase"], "objective": objective, "tdp": g.get("tdp_w"),
                                   "draw": g.get("draw_w"), "temp": temp, "policy": coord["state"]})
            self.telemetry.engine(st)
        return self.snapshot

    def _delta(self, st: Dict[str, Any], key: str) -> float:
        prev = getattr(self, "_prev_counters", {})
        value = st.get(key)
        out = 0.0
        if isinstance(value, (int, float)) and isinstance(prev.get(key), (int, float)) and value >= prev[key]:
            out = float(value - prev[key])
        prev[key] = value
        self._prev_counters = prev
        return out

    @staticmethod
    def _engine_view(st: Dict[str, Any]) -> Dict[str, Any]:
        keys = ("engine", "fresh", "state", "multiplier", "cap_fps", "base_fps", "auto", "auto_floor",
                "post", "post_active", "post_error", "gpu_us_avg", "gpu_post_us_avg", "last_problem",
                "steam_ui", "width", "height", "message", "trace", "transfer", "hdr_enabled", "post_hdr_limited")
        return {k: st.get(k) for k in keys if k in st}

    def _end_session(self, reason: str) -> None:
        summary = self.stats.finish()
        if summary and self.telemetry is not None:
            self.telemetry.session({"app": self.app, "reason": reason, "end": round(time.time()), **summary})
        if summary and self.journal:
            self.journal("service", "session-summary", app=self.app, **summary)

    def stop(self) -> None:
        """Plugin unload: TDP back to the player's, HUD hidden, generation left as the engine runs it."""
        self._end_session("unload")
        self.governor.stop("unload")
        if self.hud is not None:
            try:
                self.hud.tick(False, None)
            except OSError:
                pass
