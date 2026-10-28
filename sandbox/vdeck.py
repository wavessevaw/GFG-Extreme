"""A virtual Steam Deck for the GFG Extreme 3.0 sandbox.

Modelled, not measured: these are plausible shapes (fps against watts, temperature against
draw, Kedavra Auto's cap steps), good enough to show that the controllers take the right
steps in the right order and do not fight. Hardware numbers come only from the Deck.

  VGame      fps the game can render: base fps at 15 W x scene load x ((TDP - 2.5) / 12.5)^0.55,
             8 % slower while generation runs, +-2 % noise per second
  VEngine    the KEDAVRA Gamescope as GFG sees it: convars (set by gamescopectl), the status
             file once a second (policy echo, counters, Auto's cap), Auto's cap steps with the
             x3.75 floor, restarts, stale status, a rival tool changing convars
  VPower     slowPPT/fastPPT with the actuator API of governor_power, draw from the game's
             load, Steam's slider (an outside change)
  VSensors   APU temperature (first order, 60 s), battery percent from draw, busiest CPU core,
             GPU busy and clock
  VCpu       cpufreq sysfs in a temp directory, so Power Split runs the real CpuFreqActuator;
             a lower CPU clock frees up to CPU_BOOST_W for the GPU (CPU and GPU share the
             TDP) and lowers what the CPU can feed (cpu_fps x clock share)
"""
from __future__ import annotations

import math
import random
import statistics
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

CPU_BOOST_W = 3.0      # what the CPU's boost takes from the shared budget at full clock
CPU_MAX_KHZ = 3_500_000
CPU_MIN_KHZ = 1_400_000


class VCpu:
    """Four cpufreq policies under a temp root; ``share`` is the clock the game runs at."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="gfg-vcpu-")
        self.root = Path(self.tmp.name)
        for i in range(4):
            d = self.root / f"policy{i}"
            d.mkdir()
            (d / "cpuinfo_max_freq").write_text(f"{CPU_MAX_KHZ}\n")
            (d / "cpuinfo_min_freq").write_text(f"{CPU_MIN_KHZ}\n")
            (d / "scaling_max_freq").write_text(f"{CPU_MAX_KHZ}\n")

    @property
    def share(self) -> float:
        try:
            return int((self.root / "policy0" / "scaling_max_freq").read_text()) / CPU_MAX_KHZ
        except (OSError, ValueError):
            return 1.0

    def actuator(self):
        from gfg_plugin.cpu_freq import CpuFreqActuator
        return CpuFreqActuator(root=self.root, helper=lambda: None, access=lambda p, m: True,
                               marker=self.root / "cpu-cap.json")


class VClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class VGame:
    def __init__(self, name: str, fps15: float, load: Optional[Callable[[float], float]] = None,
                 app_id: int = 1245620, noise: float = 0.02, seed: int = 1, cpu_fps: float = 200.0) -> None:
        self.name, self.fps15, self.app_id = name, fps15, app_id
        self.cpu_fps = cpu_fps   # what the CPU can feed at full clock (high = GPU-bound game)
        self.load = load or (lambda t: 1.0)
        self.noise = noise
        self.rng = random.Random(seed)
        self.gen_factor = 0.92   # what generation leaves the game (VEngine.gen_cost sets it per second)

    def capability(self, tdp: float, t: float, generating: bool) -> float:
        f = self.fps15 * self.load(t) * (max(tdp - 2.5, 0.1) / 12.5) ** 0.55
        if generating:
            f *= self.gen_factor
        return f * (1.0 + self.noise * (2 * self.rng.random() - 1))

    def watts_for(self, fps: float, t: float, generating: bool) -> float:
        """APU watts needed to render fps (plus 2.5 W for the rest of the Deck's APU)."""
        full = self.fps15 * self.load(t) * (self.gen_factor if generating else 1.0)
        return 2.5 + 12.5 * (max(fps, 0.0) / max(full, 1e-6)) ** (1 / 0.55)


def ladder_floor(refresh: int, floor: int) -> List[int]:
    lo, hi = -(-refresh // 3), refresh // 2
    out = []
    if floor:
        mf = max(20, -(-refresh * 4 // 15))
        floor = max(floor, mf)
        if floor < lo:
            out.append(floor)
    out.append(lo)
    c = (lo // 5 + 1) * 5
    while c < hi:
        out.append(c)
        c += 5
    if hi > lo:
        out.append(hi)
    return out


class VAuto:
    """Kedavra Auto per second: climbs one cap per clean second after its wait, drops at once to
    the highest cap the game's median holds, failed trials double the wait (8 s .. 32 s)."""

    def __init__(self, refresh: int, floor: int) -> None:
        self.levels = ladder_floor(refresh, floor)
        self.level = 0
        self.wait = 8.0
        self.backoff = 1
        self.probe_at = 0.0
        self.trial = False
        self.hist: List[float] = []
        self.switches = 0

    @property
    def cap(self) -> int:
        return self.levels[self.level]

    def step(self, t: float, capability: float) -> None:
        rate = min(capability, self.cap)
        self.hist = (self.hist + [rate])[-5:]
        bad = capability < 0.985 * self.cap
        before = self.level
        if bad and self.level > 0:
            med = statistics.median(self.hist)
            lvl = self.level - 1
            while lvl > 0 and 0.97 * self.levels[lvl] > med:
                lvl -= 1
            self.level = lvl
            if self.trial and self.backoff < 4:
                self.backoff *= 2
            self.trial = False
            self.probe_at = t + self.wait * self.backoff
        elif not bad and self.trial:
            self.trial = False
            self.backoff = 1
            self.probe_at = t
        elif not bad and t >= self.probe_at and self.level + 1 < len(self.levels):
            self.level += 1
            self.trial = True
        if self.level != before:
            self.switches += 1


class VEngine:
    DEFAULTS = {"kfg_multiplier": "0", "kfg_base_fps": "0", "kfg_auto_floor": "0", "kfg_post": "",
                "kfg_hud": "", "kfg_policy": "0", "kfg_trace": "", "kfg_hdr": "1",
                "kfg_strict": "1"}

    def __init__(self, clock: VClock, game: VGame, power: "VPower", refresh: int = 90) -> None:
        self.clock, self.game, self.power = clock, game, power
        self.refresh = refresh
        self.vars = dict(self.DEFAULTS)
        self.running = True
        self.stale_until = -1.0
        self.old_engine = False
        self.steam_ui = False
        self.app_id = game.app_id
        self.auto: Optional[VAuto] = None
        self.auto_floor_built = None
        self.counters = {k: 0 for k in ("flips", "sources", "real", "gen", "repeat", "over_budget", "ring_miss", "paints")}
        self.sends = 0
        self.last: Dict[str, Any] = {}
        self.rival: Optional[Callable[["VEngine"], None]] = None
        self.capability = 0.0
        self.rate = 0.0
        self.cap = 0
        self.gpu_us = 1700.0
        self.over_budget_per_s = 0.0
        self.cpu: Optional[VCpu] = None
        self.gpu_backend: Any = None   # gpu_clock.MemoryBackend: SteamOSManager's manual GPU clock
        self.cpu_share = 1.0
        self.gpu_capability = 0.0
        # A GSF 1.5 engine (strict multiplier): status "strict" (kfg_strict 0 fill, 1 stretch =
        # default, 2 hold, 3 real). With kfg_strict >= 1 it draws exactly N-1 intermediates per
        # real frame for N >= 2; in every mode at most two per real frame, and Auto and a base
        # stay at refresh / 3 or above (x3.75's (1, 24) runs as base 30).
        self.strict = False
        # Generation's cost to the game: None keeps the flat 8 %; a number is the share lost per
        # 60 generated frames a second (0.08: 8 % at x3 on 90 Hz, less for fewer intermediates).
        self.gen_cost: Optional[float] = None
        self.gen_rate = 60.0
        self.out_rate = 0.0

    # gamescopectl
    def set_var(self, name: str, value: Any) -> None:
        if not self.running:
            raise RuntimeError("gamescopectl: no Gamescope")
        self.sends += 1
        self.vars[name] = str(value)

    def restart(self) -> None:
        """Gamescope restarted: every convar back to its default, policy 0."""
        self.vars = dict(self.DEFAULTS)
        self.auto = None

    def _int(self, name: str) -> int:
        try:
            return int(self.vars.get(name) or 0)
        except ValueError:
            return 0

    def step(self) -> None:
        """One second of the engine and the game."""
        t = self.clock()
        if self.rival:
            self.rival(self)
        mult, base, floor = self._int("kfg_multiplier"), self._int("kfg_base_fps"), self._int("kfg_auto_floor")
        if self.strict:
            third = -(-self.refresh // 3)
            base = max(third, base) if base else 0
            floor = max(third, floor) if floor else 0
        generating = mult != 0 and self.app_id not in (0, 769)
        # CPU and GPU share the TDP: a capped CPU clock gives part of its boost back to the GPU
        # and limits how many frames the CPU can prepare.
        if self.gen_cost is not None:
            self.game.gen_factor = max(0.5, 1.0 - self.gen_cost * self.gen_rate / 60.0)
        share = self.cpu.share if self.cpu else 1.0
        freed = CPU_BOOST_W * (1.0 - share * share)
        cap_power = self.power.tdp + 0.6 * freed
        self.cpu_share = share
        self.gpu_capability = self.game.capability(cap_power, t, generating)
        # A manual GPU clock (the QAM slider) caps what the GPU can render and stops it boosting
        # past what the frame needs.
        gb = self.gpu_backend
        gshare = gb.maximum / 1600.0 if gb is not None and gb.level == "manual" else 1.0
        self.gpu_share = gshare
        self.gpu_capability *= gshare ** 0.9
        capability = min(self.gpu_capability, self.game.cpu_fps * share)
        if mult == 0:
            cap = 0
            self.auto = None
        elif base:
            minimum = max(20, -(-self.refresh // 4))
            cap = min(self.refresh, max(minimum, base))
            self.auto = None
        elif mult == 1:
            if self.auto is None or self.auto_floor_built != floor:
                self.auto = VAuto(self.refresh, floor)
                self.auto_floor_built = floor
            self.auto.step(t, capability)
            cap = self.auto.cap
        else:
            cap = self.refresh // mult
            self.auto = None
        strict = self.strict and self._int("kfg_strict") >= 1 and mult >= 2 and generating
        if strict and base:
            cap = min(self.refresh // mult, max(20, base))
        rate = min(capability, cap) if cap else min(capability, self.refresh)
        self.capability, self.rate, self.cap = capability, rate, cap
        need = max(2.5, self.game.watts_for(rate, t, generating) * (0.85 + 0.15 * gshare) - 0.5 * freed)
        # A capped game below its TDP still boosts clocks past what it needs ("race to idle" is
        # not free): a third of the headroom is drawn. Lowering the TDP takes that away.
        self.power.draw = min(self.power.tdp, need + 0.33 * gshare * gshare * max(0.0, self.power.tdp - need))
        c = self.counters
        c["flips"] += self.refresh
        c["sources"] += rate
        if cap and generating and strict:
            # Exactly N-1 intermediates per real frame; the rest of the refresh repeats.
            gen = (mult - 1) * rate
            c["real"] += rate
            c["gen"] += gen
            c["repeat"] += max(0.0, self.refresh - rate - gen)
            self.gen_rate, self.out_rate = gen, rate + gen
        elif cap and generating:
            repeat = max(0.0, self.refresh * (1.0 - rate / cap))
            c["real"] += rate
            c["repeat"] += repeat
            gen = max(0.0, self.refresh - rate - repeat)
            c["gen"] += gen
            self.gen_rate, self.out_rate = gen, rate + gen
        else:
            c["real"] += rate
            self.gen_rate, self.out_rate = 0.0, rate
        c["over_budget"] += self.over_budget_per_s

    def status(self) -> Dict[str, Any]:
        t = self.clock()
        if not self.running:
            return {"engine": "absent", "fresh": False}
        if t < self.stale_until:
            return {**self.last, "fresh": False, "engine": "stale"}
        mult = self._int("kfg_multiplier")
        st = {
            "engine": "running", "fresh": True, "time_ns": int(t * 1e9), "refresh_ns": int(1e9 / self.refresh),
            "multiplier": mult, "state": "active" if mult and self.app_id not in (0, 769) else "off",
            "width": 1280, "height": 800, "app_id": self.app_id, "steam_ui": self.steam_ui,
            "auto": mult == 1 and not self._int("kfg_base_fps"), "cap_fps": self.cap,
            "base_fps": self._int("kfg_base_fps"), "gpu_us_avg": self.gpu_us,
            **({"strict": self._int("kfg_strict")} if self.strict else {}),
            **{k: int(v) for k, v in self.counters.items()},
        }
        if not self.old_engine:
            st.update({"policy": self._int("kfg_policy"), "req_multiplier": mult,
                       "req_base_fps": self._int("kfg_base_fps"), "req_auto_floor": self._int("kfg_auto_floor"),
                       "auto_floor": self.auto.levels[0] if self.auto else 0, "post": self.vars["kfg_post"],
                       "hdr_enabled": self.vars["kfg_hdr"] == "1", "transfer": "sdr"})
        self.last = st
        return st


class VPower:
    """The actuator API GFG's Governor uses (governor_power.SteamDeckPowerActuator)."""

    def __init__(self, user_tdp: float = 15.0, minimum: float = 3.0, maximum: float = 15.0) -> None:
        self.user_tdp = user_tdp
        self.tdp = user_tdp
        self.minimum, self.maximum = minimum, maximum
        self.owned = False
        self.initial: Optional[float] = None
        self.external = False
        self.expected: Optional[float] = None
        self.draw = 0.0
        self.writes = 0

    def claim(self) -> Dict[str, Any]:
        self.initial = self.tdp
        self.expected = self.tdp
        self.owned, self.external = True, False
        return self.status()

    def set_tdp_w(self, w: float) -> Dict[str, Any]:
        if not self.owned:
            return {"success": False, "error": "not owned", "state": self.status()}
        if self.tdp != self.expected:
            self.owned, self.external = False, True
            return {"success": False, "error": "external", "state": self.status()}
        w = max(self.minimum, min(self.initial or self.maximum, float(w)))
        self.tdp = self.expected = w
        self.writes += 1
        return {"success": True, "error": None, "state": self.status()}

    def verify_ownership(self) -> Dict[str, Any]:
        if self.owned and self.tdp != self.expected:
            self.owned, self.external = False, True
        return self.status()

    def restore_if_owned(self) -> Dict[str, Any]:
        if self.owned and self.tdp == self.expected and self.initial is not None:
            self.tdp = self.initial
            self.owned = False
            return {"success": True, "restored": True}
        self.owned = False
        return {"success": True, "restored": False}

    def steam_slider(self, w: float) -> None:
        """The player moves Steam's TDP slider."""
        self.tdp = self.slider = w

    def status(self) -> Dict[str, Any]:
        return {"owned": self.owned, "external_change": self.external, "initial_tdp_w": self.initial,
                "ceiling_tdp_w": self.initial, "minimum_tdp_w": self.minimum, "draw_w": round(self.draw, 2),
                "observed_tdp_w": self.tdp, "method": "virtual"}

    def steamos_power_source(self) -> None:
        """SteamOS re-applies its own TDP (the player's slider) when the charger is plugged or pulled."""
        self.tdp = getattr(self, "slider", self.user_tdp)


class VSensors:
    def __init__(self, clock: VClock, power: VPower, ambient: float = 25.0) -> None:
        self.clock, self.power = clock, power
        self.ambient = ambient
        self.temp = 45.0
        self.battery = 80.0
        self.external_power = False
        self.capacity_wh = 50.0

    def step(self) -> None:
        eq = self.ambient + 15.0 + 2.6 * self.power.draw
        self.temp += (eq - self.temp) / 60.0
        if not self.external_power:
            self.battery = max(0.0, self.battery - (self.power.draw + 4.0) / 3600.0 / self.capacity_wh * 100.0)

    def sample(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"temp_c": round(self.temp, 1)}
        e = getattr(self, "engine", None)
        if e is not None and e.rate > 0:
            cpu_cap = e.game.cpu_fps * e.cpu_share
            out["cpu_top_core_pct"] = round(min(100.0, 100.0 * e.rate / max(cpu_cap, 1e-6) * 0.95), 1)
            out["gpu_busy_pct"] = round(min(100.0, 100.0 * e.rate / max(e.gpu_capability, 1e-6)), 1)
            out["gpu_clock_mhz"] = round(1600.0 * getattr(e, "gpu_share", 1.0), 0)
        return out

    def read_battery(self) -> Dict[str, Any]:
        return {"available": True, "external_power": self.external_power, "percent": round(self.battery, 1),
                "discharging": not self.external_power}


class VControl:
    """What service.py sees as kedavra.ctl.Control."""

    def __init__(self, engine: VEngine) -> None:
        self.engine = engine

    def status(self) -> Dict[str, Any]:
        return self.engine.status()

    def set_var(self, name: str, value: Any) -> None:
        self.engine.set_var(name, value)


class VModel:
    """In-memory GameModelStore."""

    def __init__(self) -> None:
        self.entries: Dict[str, Dict[str, Any]] = {}
        self.floors: Dict[str, Dict[str, tuple]] = {}

    def get(self, key):
        return self.entries.get(key)

    def record(self, key, point, tdp):
        self.entries[key] = {"point": point, "tdp_w": tdp}
        return True

    def floor_failures(self, key):
        return {p: (v[0], 0.0, 1) for p, v in (self.floors.get(key) or {}).items()}

    def record_floor_failure(self, key, point, tdp, count=1):
        if tdp is None:  # the level held: game_model.py clears the entry
            return self.floors.get(key, {}).pop(point, None) is not None
        self.floors.setdefault(key, {})[point] = (tdp,)
        return True
