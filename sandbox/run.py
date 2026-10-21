"""Sandbox scenarios: the real GFG Extreme service on the virtual Deck.

    python3 -m sandbox.run                 # all scenarios, summary table
    python3 -m sandbox.run --only battery  # some
    python3 -m sandbox.run --report docs/SANDBOX_REPORT.md --json build/sandbox.json

Each scenario plays N seconds at one tick per second and checks what the controllers did:
which point the pilot locked, what the Governor did with the TDP, whether the game held the
point, whether the engine confirmed every policy, and that nothing fought anything.
Model results, not hardware measurements.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin import settings as settings_mod  # noqa: E402
from gfg_plugin.service import Service  # noqa: E402

from gfg_plugin.split_control import SplitControl  # noqa: E402
from gfg_plugin.gpu_clock import GpuClock, MemoryBackend  # noqa: E402
from gfg_plugin.gpu_clock_control import GpuClockControl  # noqa: E402

from .vdeck import VClock, VControl, VCpu, VEngine, VGame, VModel, VPower, VSensors  # noqa: E402


class MemSettings(settings_mod.Settings):
    def __init__(self, data: Dict[str, Any]) -> None:
        self.path = Path("/nonexistent")
        self.owner = None
        self.exists = True
        self.data = settings_mod.normalize(data)

    def save(self) -> None:
        pass


@dataclass
class Rig:
    clock: VClock
    game: VGame
    power: VPower
    engine: VEngine
    sensors: VSensors
    service: Service
    settings: MemSettings
    log: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)


def make_rig(game: VGame, *, fg: str = "auto", objective: str = "balanced", preference: str = "auto",
             refresh: int = 90, user_tdp: float = 15.0, ambient: float = 25.0, battery: float = 80.0,
             external_power: bool = False, base_fps: int = 45, power_enabled: bool = True,
             split: bool = True, gpu_clock: bool = True) -> Rig:
    clock = VClock()
    power = VPower(user_tdp=user_tdp)
    engine = VEngine(clock, game, power, refresh=refresh)
    sensors = VSensors(clock, power, ambient=ambient)
    sensors.battery, sensors.external_power = battery, external_power
    sensors.engine = engine
    vcpu = VCpu()
    engine.gpu_backend = MemoryBackend()
    engine.cpu = vcpu
    data = settings_mod.defaults()
    data["profiles"]["default"].update({"fg": fg, "objective": objective, "base_fps": base_fps})
    data["autopilot"]["preference"] = preference
    data["power"]["enabled"] = power_enabled
    data["power"]["split"] = split
    data["power"]["gpu_clock"] = gpu_clock
    data["hud"]["enabled"] = False
    st = MemSettings(data)
    log: List[Dict[str, Any]] = []
    svc = Service(settings=st, ctl=VControl(engine), actuator=power, model=VModel(), sensors=sensors,
                  battery=sensors.read_battery, hud=None, hud_path="/dev/shm/gfg-extreme-hud.raw", clock=clock,
                  journal=lambda src, kind, **f: log.append({"t": clock(), "src": src, "kind": kind, **f}),
                  split=SplitControl(vcpu.actuator(), clock=clock,
                                     journal=lambda kind, **f: log.append({"t": clock(), "src": "split", "kind": kind, **f})),
                  gclock=GpuClockControl(GpuClock(engine.gpu_backend, writes_enabled=True), clock=clock,
                                         journal=lambda kind, **f: log.append({"t": clock(), "src": "gpu", "kind": kind, **f})))
    return Rig(clock, game, power, engine, sensors, svc, st, log)


def play(rig: Rig, seconds: int, events: Optional[Dict[int, Callable[[Rig], None]]] = None) -> None:
    events = events or {}
    start = len(rig.timeline)
    for i in range(seconds):
        k = start + i
        if k in events:
            events[k](rig)
        rig.engine.step()
        rig.sensors.step()
        snap = rig.service.tick()
        rig.timeline.append({
            "t": k, "point": snap["pilot"]["point"], "phase": snap["pilot"]["phase"], "cap": rig.engine.cap,
            "rate": round(rig.engine.rate, 2), "capability": round(rig.engine.capability, 2),
            "tdp": rig.power.tdp, "draw": rig.power.draw, "temp": rig.sensors.temp, "battery": rig.sensors.battery,
            "objective": snap["objective"], "policy": snap["policy"]["state"], "game": snap["game"],
            "sends": rig.engine.sends, "gov_paused": bool(snap["governor"].get("paused")),
            "mult": rig.engine._int("kfg_multiplier"), "base": rig.engine._int("kfg_base_fps"),
            "cpu_share": round(rig.engine.cpu_share, 2), "gpu_share": round(getattr(rig.engine, "gpu_share", 1.0), 3), "split_phase": (snap.get("split") or {}).get("phase"),
        })
        rig.clock.t += 1.0


def metrics(rig: Rig, skip: int = 60, until: Optional[int] = None) -> Dict[str, Any]:
    rows = [r for r in rig.timeline[skip:until] if r["game"]]
    if not rows:
        return {}
    held = [r for r in rows if r["cap"] and r["rate"] >= 0.95 * r["cap"]]
    locked = [r for r in rows if r["phase"] in ("locked", "fixed")]
    return {
        "seconds": len(rows),
        "smooth_pct": round(100.0 * len(held) / len(rows), 1),
        "point_final": rows[-1]["point"],
        "points": sorted({r["point"] for r in locked}),
        "tdp_final": rows[-1]["tdp"],
        "tdp_avg": round(statistics.fmean(r["tdp"] for r in rows), 2),
        "draw_avg_w": round(statistics.fmean(r["draw"] for r in rows), 2),
        "energy_wh": round(sum(r["draw"] for r in rows) / 3600.0, 3),
        "temp_max": round(max(r["temp"] for r in rows), 1),
        "confirmed_pct": round(100.0 * sum(r["policy"] == "confirmed" for r in rows) / len(rows), 1),
        "conflict_s": sum(r["policy"] == "conflict" for r in rows),
        "sends": rows[-1]["sends"] - rows[0]["sends"],
        "objective_final": rows[-1]["objective"],
        "demotions": rig.service.pilot.demotions,
        "promotions": rig.service.pilot.promotions,
        "tdp_writes": rig.power.writes,
    }


# ---------------------------------------------------------------- scenarios
SCENARIOS: Dict[str, Callable[[], Dict[str, Any]]] = {}


def scenario(fn):
    SCENARIOS[fn.__name__] = fn
    return fn


def check(results: Dict[str, Any], name: str, ok: bool, detail: str = "") -> None:
    results.setdefault("checks", []).append({"name": name, "ok": bool(ok), "detail": detail})


def _objective_run(obj: str, fps15: float, seconds: int = 900) -> Rig:
    rig = make_rig(VGame("game", fps15), objective=obj)
    play(rig, seconds)
    return rig


@scenario
def objectives_light_game() -> Dict[str, Any]:
    """A light game (65 fps at 15 W) under each objective."""
    out: Dict[str, Any] = {"runs": {}}
    for obj in ("quality", "balanced", "battery"):
        out["runs"][obj] = metrics(_objective_run(obj, 65.0), skip=120)
    q, b, bat = out["runs"]["quality"], out["runs"]["balanced"], out["runs"]["battery"]
    check(out, "quality locks x2 (45) and keeps the player's TDP", q["point_final"] == 45 and q["tdp_final"] == 15.0,
          f"point {q['point_final']}, TDP {q['tdp_final']}")
    check(out, "balanced locks x2 (45) and saves watts", b["point_final"] == 45 and b["tdp_avg"] < 14.0,
          f"point {b['point_final']}, TDP avg {b['tdp_avg']}")
    check(out, "battery locks x3.75 (24)", bat["point_final"] == 24, f"point {bat['point_final']}")
    check(out, "energy: battery < balanced < quality",
          bat["energy_wh"] < b["energy_wh"] < q["energy_wh"], f"{bat['energy_wh']} < {b['energy_wh']} < {q['energy_wh']} Wh")
    for obj, m in out["runs"].items():
        check(out, f"{obj}: the game holds its point >= 98 % of the time", m["smooth_pct"] >= 98.0, f"{m['smooth_pct']} %")
        check(out, f"{obj}: no conflict", m["conflict_s"] == 0)
    return out


@scenario
def objectives_medium_game() -> Dict[str, Any]:
    """A medium game (40 fps at 15 W, 36.8 while generating): x2.6 at full power."""
    out: Dict[str, Any] = {"runs": {}}
    for obj in ("quality", "balanced", "battery"):
        out["runs"][obj] = metrics(_objective_run(obj, 40.0), skip=120)
    q, b, bat = out["runs"]["quality"], out["runs"]["balanced"], out["runs"]["battery"]
    check(out, "quality locks 35 (x2.6)", q["point_final"] == 35, f"point {q['point_final']}")
    check(out, "balanced keeps 35 and never trades it for watts", b["point_final"] == 35 and b["smooth_pct"] >= 97.0,
          f"point {b['point_final']}, smooth {b['smooth_pct']} %, TDP {b['tdp_avg']}")
    check(out, "battery locks 24 (x3.75) with less energy", bat["point_final"] == 24 and bat["energy_wh"] < b["energy_wh"],
          f"{bat['energy_wh']} vs {b['energy_wh']} Wh")
    return out


@scenario
def heavy_game_x375() -> Dict[str, Any]:
    """A heavy game (27 fps at 15 W) cannot hold x3 (30): every objective uses x3.75, steadily."""
    out: Dict[str, Any] = {"runs": {}}
    for obj in ("quality", "balanced", "battery"):
        rig = _objective_run(obj, 27.0, 600)
        out["runs"][obj] = metrics(rig, skip=120)
    for obj, m in out["runs"].items():
        check(out, f"{obj}: x3.75 (24)", m["point_final"] == 24, f"point {m['point_final']}")
        check(out, f"{obj}: steady (no demote/promote loop)", m["demotions"] <= 1 and m["promotions"] <= 0,
              f"demotions {m['demotions']}, promotions {m['promotions']}")
        check(out, f"{obj}: holds 24", m["smooth_pct"] >= 97.0, f"{m['smooth_pct']} %")
    return out


@scenario
def scene_gets_heavy_then_light() -> Dict[str, Any]:
    """60 fps game; from 300 s to 420 s the scene costs twice as much; then light again."""
    load = lambda t: 0.5 if 1300 <= t < 1420 else 1.0  # noqa: E731  (clock starts at 1000)
    out: Dict[str, Any] = {}
    rig = make_rig(VGame("spiky", 60.0, load), objective="balanced")
    play(rig, 1200)
    tl = rig.timeline
    during = [r for r in tl[310:420]]
    after = tl[-1]
    first_drop = next((r["t"] for r in tl[300:420] if r["point"] < 45), None)
    out["metrics"] = metrics(rig, skip=120)
    out["first_point_drop_s"] = None if first_drop is None else first_drop - 300
    check(out, "the point steps down within 20 s of the heavy scene", first_drop is not None and first_drop - 300 <= 20,
          f"after {out['first_point_drop_s']} s")
    check(out, "during the heavy scene the lower point holds", sum(r["rate"] >= 0.95 * r["cap"] for r in during if r["cap"]) / max(1, len(during)) >= 0.85)
    check(out, "x2 (45) comes back after the scene", after["point"] == 45, f"final {after['point']}")
    check(out, "balanced TDP back below the ceiling at the end", after["tdp"] < 15.0, f"TDP {after['tdp']}")
    return out


@scenario
def hot_deck() -> Dict[str, Any]:
    """Hot room (40 C) and a demanding game in Autopilot on external power."""
    rig = make_rig(VGame("hot", 46.0), objective="autopilot", ambient=40.0, external_power=True)
    play(rig, 1500)
    m = metrics(rig, skip=120)
    out = {"metrics": m}
    objectives = {r["objective"] for r in rig.timeline[200:]}
    check(out, "temperature stays below 95 C", m["temp_max"] < 95.0, f"max {m['temp_max']} C")
    check(out, "Autopilot leaves Quality when hot", "balanced" in objectives, f"objectives {sorted(objectives)}")
    return out


@scenario
def steam_slider_moved() -> Dict[str, Any]:
    """The player moves Steam's TDP slider during the game: the Governor stops for this game."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    play(rig, 400)
    writes = rig.power.writes
    play(rig, 300, {400: lambda r: r.power.steam_slider(8.0)})
    out = {"metrics": metrics(rig, skip=120)}
    check(out, "Governor paused", rig.timeline[-1]["gov_paused"])
    check(out, "no TDP write after the outside change", rig.power.writes == writes, f"{rig.power.writes - writes} writes")
    check(out, "the player's 8 W stays", rig.power.tdp == 8.0, f"{rig.power.tdp} W")
    return out


@scenario
def gamescope_restart() -> Dict[str, Any]:
    """Gamescope restarts mid-game (all convars back to defaults): the policy comes back."""
    rig = make_rig(VGame("g", 65.0), objective="quality")
    play(rig, 300)
    play(rig, 120, {300: lambda r: r.engine.restart()})
    tl = rig.timeline
    back = next((r["t"] for r in tl[300:] if r["policy"] == "confirmed" and r["base"] == 45), None)
    out = {"back_after_s": None if back is None else back - 300}
    check(out, "policy re-applied and confirmed within 5 s", back is not None and back - 300 <= 5, f"{out['back_after_s']} s")
    check(out, "no conflict reported for one restart", all(r["policy"] != "conflict" for r in tl))
    return out


@scenario
def rival_plugin() -> Dict[str, Any]:
    """The standalone GSF Kedavra plugin (or a script) keeps setting x3 every 3 s."""
    rig = make_rig(VGame("g", 65.0), objective="quality")
    play(rig, 200)
    sends0 = rig.engine.sends

    def rival(e):
        if int(e.clock()) % 3 == 0:
            e.vars["kfg_multiplier"] = "3"
            e.vars["kfg_base_fps"] = "0"
    play(rig, 300, {200: lambda r: setattr(r.engine, "rival", rival)})
    tl = rig.timeline[200:]
    our_sends = rig.engine.sends - sends0
    out = {"gfg_sends_in_300s": our_sends, "conflict_s": sum(r["policy"] == "conflict" for r in tl)}
    check(out, "GFG reports a conflict", out["conflict_s"] > 0)
    check(out, "GFG backs off instead of fighting (< 1 policy send per 5 s)", our_sends <= 6 * 60 / 5,
          f"{our_sends} convar writes in 300 s")
    play(rig, 200, {500: lambda r: setattr(r.engine, "rival", None)})
    check(out, "after the rival stops, GFG's policy is confirmed again (within the 2 min back-off)",
          rig.timeline[-1]["policy"] == "confirmed")
    check(out, "the rival never moved GFG's point", all(r["point"] == 45 for r in rig.timeline[200:]))
    rig2 = make_rig(VGame("g", 65.0), objective="quality")
    play(rig2, 200)
    play(rig2, 60, {200: lambda r: setattr(r.engine, "rival", rival)})
    play(rig2, 10, {260: lambda r: (setattr(r.engine, "rival", None), r.service.coord.take_over())})
    check(out, "Take over: confirmed within 10 s", rig2.timeline[-1]["policy"] == "confirmed")
    return out


@scenario
def stale_status() -> Dict[str, Any]:
    """The engine stops answering for 10 s (a hang): HOLD, nothing is sent; then it recovers."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    play(rig, 300)
    sends = rig.engine.sends
    play(rig, 10, {300: lambda r: setattr(r.engine, "stale_until", r.clock() + 10)})
    out = {"sends_while_stale": rig.engine.sends - sends}
    check(out, "HOLD while stale", all(r["policy"] == "hold" for r in rig.timeline[301:309]))
    check(out, "nothing sent while stale", out["sends_while_stale"] == 0)
    play(rig, 30)
    check(out, "confirmed again after", rig.timeline[-1]["policy"] == "confirmed")
    return out


@scenario
def battery_drains_autopilot() -> Dict[str, Any]:
    """Autopilot on battery from 23 %: Balanced, then Battery below 20 % (x3.75), once."""
    rig = make_rig(VGame("g", 55.0), objective="autopilot", battery=23.0)
    rig.sensors.capacity_wh = 5.0  # drain fast
    play(rig, 1500)
    tl = rig.timeline
    objs = [r["objective"] for r in tl]
    switches = sum(1 for a, b in zip(objs, objs[1:]) if a != b)
    out = {"objective_switches": switches, "final": objs[-1], "battery_final": round(tl[-1]["battery"], 1)}
    check(out, "switches to Battery below 20 %", objs[-1] == "battery")
    check(out, "no flapping (<= 2 switches)", switches <= 2, f"{switches}")
    check(out, "Battery point x3.75 (24)", tl[-1]["point"] == 24, f"{tl[-1]['point']}")
    return out


@scenario
def plug_in_charger() -> Dict[str, Any]:
    """Autopilot on battery, then the charger: Quality, the TDP goes back to the player's."""
    rig = make_rig(VGame("g", 65.0), objective="autopilot", battery=60.0)
    play(rig, 400)
    play(rig, 300, {400: lambda r: setattr(r.sensors, "external_power", True)})
    out = {"objective": rig.timeline[-1]["objective"], "tdp": rig.timeline[-1]["tdp"]}
    check(out, "Quality on external power", out["objective"] == "quality")
    check(out, "TDP back at the player's 15 W", out["tdp"] == 15.0, f"{out['tdp']} W")
    return out


@scenario
def docked_60hz() -> Dict[str, Any]:
    """Docked at 60 Hz: the ladder is 20 (x3), 25, 30 (x2); no x3.75 below 20."""
    rig = make_rig(VGame("g", 34.0), objective="balanced", refresh=60)
    play(rig, 600)
    m = metrics(rig, skip=120)
    out = {"metrics": m}
    check(out, "a 34 fps game locks 30 (x2) at 60 Hz", m["point_final"] == 30, f"{m['point_final']}")
    rig = make_rig(VGame("g", 34.0), objective="battery", refresh=60)
    play(rig, 300)
    check(out, "battery at 60 Hz locks 20 (x3, never below 20)", rig.timeline[-1]["point"] == 20, f"{rig.timeline[-1]['point']}")
    return out


@scenario
def fixed_x3_too_heavy() -> Dict[str, Any]:
    """The player fixed x3 but the game cannot hold 30: GFG reports it and does not change it."""
    rig = make_rig(VGame("g", 26.0), fg="x3", objective="balanced")
    play(rig, 300)
    snap = rig.service.snapshot
    out = {"holds": snap["pilot"]["holds"], "mult": rig.timeline[-1]["mult"]}
    check(out, "multiplier stays x3", out["mult"] == 3)
    check(out, "reported as not holding", out["holds"] is False)
    return out


@scenario
def qam_and_menus() -> Dict[str, Any]:
    """The QAM (Steam UI on top) for 8 s: no session end, no TDP restore, no new measurement."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    play(rig, 400)
    tdp_before = rig.timeline[-1]["tdp"]
    restores = [e for e in rig.log if e["kind"] == "governor-restore"]

    def qam(r, on):
        r.engine.steam_ui = on
    play(rig, 60, {400: lambda r: qam(r, True), 408: lambda r: qam(r, False)})
    out = {"tdp_before": tdp_before}
    check(out, "no TDP restore", len([e for e in rig.log if e["kind"] == "governor-restore"]) == len(restores))
    check(out, "point unchanged", all(r["point"] == 45 for r in rig.timeline[400:]))
    return out


@scenario
def game_switch() -> Dict[str, Any]:
    """Game A (light), then game B (heavy): each gets its own measurement and point."""
    rig = make_rig(VGame("a", 65.0, app_id=111), objective="balanced")
    play(rig, 400)
    a_point = rig.timeline[-1]["point"]

    def switch(r):
        r.engine.app_id = 222
        r.engine.game = VGame("b", 33.0, app_id=222)
    play(rig, 400, {400: switch})
    out = {"a": a_point, "b": rig.timeline[-1]["point"]}
    check(out, "game A x2 (45)", a_point == 45)
    check(out, "game B measured anew: 30 (x3)", out["b"] == 30, f"{out['b']}")
    return out


@scenario
def old_engine() -> Dict[str, Any]:
    """An engine from before 3.0 (no policy echo): reported outdated, no send loop."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    rig.engine.old_engine = True
    play(rig, 120)
    out = {"state": rig.timeline[-1]["policy"], "sends": rig.engine.sends}
    check(out, "state outdated", out["state"] == "outdated")
    check(out, "nothing sent", out["sends"] == 0)
    return out


@scenario
def user_toggles_fast() -> Dict[str, Any]:
    """The player flips frame generation every 3 s for a minute, then leaves Auto."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    modes = ["x2", "x3", "off", "auto", "x3.75", "custom"]
    ev = {}
    for i in range(20):
        ev[100 + 3 * i] = (lambda m: (lambda r: r.settings.data["profiles"]["default"].update({"fg": m})))(modes[i % len(modes)])
    ev[160] = lambda r: r.settings.data["profiles"]["default"].update({"fg": "auto"})
    play(rig, 500, ev)
    out = {"final_policy": rig.timeline[-1]["policy"], "final_point": rig.timeline[-1]["point"]}
    check(out, "converges: confirmed", out["final_policy"] == "confirmed")
    check(out, "no conflict from the player's own changes", all(r["policy"] != "conflict" for r in rig.timeline))
    check(out, "Auto locks x2 (45) again", out["final_point"] == 45, f"{out['final_point']}")
    return out


@scenario
def hdr_switch() -> Dict[str, Any]:
    """The player turns HDR generation off and on mid-game (Setup): the engine gets kfg_hdr,
    the locked point and the TDP are kept (no new measurement, no conflict)."""
    rig = make_rig(VGame("g", 40.0), objective="balanced")
    seen = {}
    ev = {
        300: lambda r: r.settings.data["engine"].update({"hdr": False}),
        330: lambda r: seen.update(off=r.engine.vars["kfg_hdr"], point_off=r.service.pilot.point),
        400: lambda r: r.settings.data["engine"].update({"hdr": True}),
    }
    play(rig, 600, ev)
    after = rig.timeline[300:]
    out = {"kfg_hdr_while_off": seen.get("off"), "kfg_hdr_final": rig.engine.vars["kfg_hdr"],
           "point_before": rig.timeline[299]["point"], "point_final": rig.timeline[-1]["point"]}
    check(out, "kfg_hdr=0 sent while off", seen.get("off") == "0")
    check(out, "kfg_hdr=1 back on", out["kfg_hdr_final"] == "1")
    check(out, "point kept (no re-measure)", all(r["phase"] != "measure" for r in after)
          and out["point_final"] == out["point_before"], f"{out['point_before']} -> {out['point_final']}")
    check(out, "confirmed at the end, never conflict", rig.timeline[-1]["policy"] == "confirmed"
          and all(r["policy"] != "conflict" for r in after))
    return out


@scenario
def power_control_off() -> Dict[str, Any]:
    """TDP control off (player's choice): points still measured and guarded, TDP untouched."""
    rig = make_rig(VGame("g", 40.0), objective="balanced", power_enabled=False)
    play(rig, 600)
    out = {"tdp": rig.timeline[-1]["tdp"], "point": rig.timeline[-1]["point"], "writes": rig.power.writes}
    check(out, "no TDP write", out["writes"] == 0)
    check(out, "point 35 (x2.6)", out["point"] == 35, f"{out['point']}")
    return out


@scenario
def long_session_stability() -> Dict[str, Any]:
    """Two hours of a varying game (load waves of 10 min): no oscillation, bounded writes."""
    import math as _m
    load = lambda t: 0.85 + 0.15 * _m.sin(2 * _m.pi * t / 600.0)  # noqa: E731
    rig = make_rig(VGame("long", 52.0, load), objective="balanced")
    play(rig, 7200)
    m = metrics(rig, skip=120)
    out = {"metrics": m}
    check(out, "smooth >= 97 %", m["smooth_pct"] >= 97.0, f"{m['smooth_pct']} %")
    check(out, "TDP writes < 1 per 20 s on average", m["tdp_writes"] < 7200 / 20, f"{m['tdp_writes']}")
    ev = [e for e in rig.log if e["kind"] == "pilot" and e["phase"] == "locked"]
    bounces = sum(1 for a, b in zip(ev, ev[1:]) if b["point"] < a["point"] and "holds: locked" in a["reason"]
                  and b["t"] - a["t"] < 60)
    out["bounces"] = bounces
    check(out, "follows the load waves (points change with the scene, at most 8 per 10 min wave)",
          m["demotions"] + m["promotions"] <= 8 * 12, f"{m['demotions']} down, {m['promotions']} up")
    check(out, "no bounce (a promoted point never fails within 60 s)", bounces == 0, f"{bounces}")
    check(out, "no conflict", m["conflict_s"] == 0)
    return out


@scenario
def gpu_budget_overload() -> Dict[str, Any]:
    """Generation runs over its GPU budget (heavy filters + x3.75) while Balanced saves watts."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    play(rig, 400)
    tdp_low = rig.timeline[-1]["tdp"]
    play(rig, 60, {400: lambda r: setattr(r.engine, "over_budget_per_s", 5.0)})
    out = {"tdp_before": tdp_low, "tdp_after": rig.timeline[-1]["tdp"]}
    check(out, "over budget raises the TDP", out["tdp_after"] > tdp_low, f"{tdp_low} -> {out['tdp_after']} W")
    return out


@scenario
def engine_missing() -> Dict[str, Any]:
    """Stock Gamescope (engine not installed or rolled back): offline, nothing sent, TDP untouched."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    rig.engine.running = False
    play(rig, 120)
    out = {"state": rig.timeline[-1]["policy"], "writes": rig.power.writes, "sends": rig.engine.sends}
    check(out, "offline", out["state"] == "offline")
    check(out, "no convar sends, no TDP writes", out["sends"] == 0 and out["writes"] == 0)
    return out


@scenario
def dock_mid_game() -> Dict[str, Any]:
    """Docked mid-game: 90 Hz -> 60 Hz. The ladder changes and the game is measured again."""
    rig = make_rig(VGame("g", 65.0), objective="balanced")
    play(rig, 300)

    def dock(r):
        r.engine.refresh = 60
        r.engine.auto = None
    play(rig, 300, {300: dock})
    out = {"before": rig.timeline[299]["point"], "after": rig.timeline[-1]["point"]}
    check(out, "x2 at 90 Hz (45), x2 at 60 Hz (30)", out["before"] == 45 and out["after"] == 30, f"{out}")
    return out


@scenario
def chaos_hour() -> Dict[str, Any]:
    """One hour of random trouble: restarts, hangs, QAM, load spikes, objective and mode changes,
    a rival for a minute, charger in and out. Invariants must hold at every second."""
    import random as _r
    rng = _r.Random(7)
    load_state = {"v": 1.0}
    rig = make_rig(VGame("chaos", 55.0, lambda t: load_state["v"]), objective="autopilot", battery=50.0)
    ev: Dict[int, Callable[[Rig], None]] = {}
    actions = []

    def restart(r): r.engine.restart()
    def hang(r): r.engine.stale_until = r.clock() + rng.randint(2, 12)
    def qam(r): r.engine.steam_ui = not r.engine.steam_ui
    def spike(r): load_state["v"] = rng.choice([0.55, 0.7, 0.85, 1.0, 1.1])
    def obj(r): r.settings.data["profiles"]["default"]["objective"] = rng.choice(["autopilot", "quality", "balanced", "battery"])
    def fg(r): r.settings.data["profiles"]["default"]["fg"] = rng.choice(["auto", "auto", "auto", "x2", "x3", "x3.75", "off"])
    def charger(r): r.sensors.external_power = not r.sensors.external_power
    pool = [restart, hang, qam, spike, spike, obj, fg, charger]
    for k in range(120, 3600, 45):
        a = rng.choice(pool)
        ev[k + rng.randint(0, 20)] = a
        actions.append(a.__name__)
    ev[1800] = lambda r: setattr(r.engine, "rival", lambda e: e.vars.update({"kfg_multiplier": "3"}) if int(e.clock()) % 4 == 0 else None)
    ev[1860] = lambda r: setattr(r.engine, "rival", None)
    ev[3500] = lambda r: (r.settings.data["profiles"]["default"].update({"fg": "auto", "objective": "balanced"}),
                          setattr(r.engine, "steam_ui", False), setattr(r.engine, "stale_until", -1), load_state.update(v=1.0))
    play(rig, 3600, ev)
    tl = rig.timeline
    out = {"actions": len(actions)}
    ladder_ok = all(r["point"] in (0, 20, 24, 25, 30, 35, 40, 45) for r in tl)
    check(out, "point always on the ladder", ladder_ok)
    check(out, "TDP never above the player's 15 W or below 3 W", all(3.0 <= r["tdp"] <= 15.0 for r in tl))
    stale_sends = 0
    for a, b in zip(tl, tl[1:]):
        if b["policy"] == "hold" and b["sends"] != a["sends"]:
            stale_sends += 1
    check(out, "nothing sent while the status is stale", stale_sends == 0, f"{stale_sends}")
    confirmed = sum(r["policy"] == "confirmed" for r in tl) / len(tl)
    out["confirmed_pct"] = round(100 * confirmed, 1)
    check(out, "policy confirmed most of the hour (>= 80 %) despite the trouble", confirmed >= 0.8, f"{out['confirmed_pct']} %")
    check(out, "settles at the end: confirmed, x2 locked", tl[-1]["policy"] == "confirmed" and tl[-1]["point"] == 45,
          f"{tl[-1]['policy']} {tl[-1]['point']}")
    return out


@scenario
def power_split_gpu_bound() -> Dict[str, Any]:
    """A GPU-bound game (CPU can feed 200 fps) in Balanced, with and without Power Split."""
    out: Dict[str, Any] = {"runs": {}}
    for sp in (False, True):
        rig = make_rig(VGame("gpu-bound", 50.0), objective="balanced", split=sp)
        play(rig, 1200)
        m = metrics(rig, skip=120)
        m["cpu_share_min"] = min(r["cpu_share"] for r in rig.timeline)
        m["capped_s"] = sum(r["cpu_share"] < 1.0 for r in rig.timeline)
        m["capped_in_trial_s"] = sum(r["cpu_share"] < 1.0 and r["phase"] in ("measure", "trial")
                                     for r in rig.timeline)
        out["runs"]["split" if sp else "no-split"] = m
    a, b = out["runs"]["no-split"], out["runs"]["split"]
    check(out, "the split caps the CPU clock in a GPU-bound game", b["cpu_share_min"] < 1.0 and b["capped_s"] > 60,
          f"min share {b['cpu_share_min']}, capped {b['capped_s']} s")
    check(out, "same point with the split", b["point_final"] == a["point_final"], f"{a['point_final']} vs {b['point_final']}")
    check(out, "the point holds >= 97 % with the split", b["smooth_pct"] >= 97.0, f"{b['smooth_pct']} %")
    check(out, "no more energy with the split", b["energy_wh"] <= a["energy_wh"] * 1.01, f"{b['energy_wh']} vs {a['energy_wh']} Wh")
    check(out, "no CPU cap while the pilot measures or tries a point", b["capped_in_trial_s"] == 0, f"{b['capped_in_trial_s']} s")
    check(out, "no conflict", b["conflict_s"] == 0)
    return out


@scenario
def power_split_cpu_bound() -> Dict[str, Any]:
    """A CPU-bound game (the CPU feeds 38 fps at full clock): the split must not take its clock."""
    out: Dict[str, Any] = {}
    rig = make_rig(VGame("cpu-bound", 70.0, cpu_fps=38.0), objective="balanced")
    play(rig, 1200)
    m = metrics(rig, skip=120)
    out["metrics"] = m
    worst = min(r["cpu_share"] for r in rig.timeline[120:])
    lowered = sum(r["cpu_share"] < 1.0 for r in rig.timeline[120:])
    out["capped_s"] = lowered
    check(out, "the CPU cap never holds in a CPU-bound game (only probes, lifted at once)", lowered <= 30,
          f"capped {lowered} s, min share {worst}")
    check(out, "the point holds >= 97 %", m["smooth_pct"] >= 97.0, f"{m['smooth_pct']} %")
    return out


@scenario
def power_split_off() -> Dict[str, Any]:
    """Power Split switched off: the CPU clock is never touched."""
    out: Dict[str, Any] = {}
    rig = make_rig(VGame("gpu-bound", 50.0), objective="balanced", split=False)
    play(rig, 600)
    check(out, "the CPU clock stays at 100 %", all(r["cpu_share"] == 1.0 for r in rig.timeline))
    return out


@scenario
def gpu_clock_cpu_bound() -> Dict[str, Any]:
    """A CPU-bound game (CPU feeds 38 fps, GPU lightly loaded): the GPU clock ceiling steps down."""
    out: Dict[str, Any] = {"runs": {}}
    for on in (False, True):
        rig = make_rig(VGame("cpu-bound", 70.0, cpu_fps=38.0), objective="quality", gpu_clock=on)
        play(rig, 1200)
        m = metrics(rig, skip=120)
        m["gpu_share_min"] = min(r["gpu_share"] for r in rig.timeline)
        m["kept"] = sum(e["kind"] == "gpu-clock-kept" for e in rig.log)
        out["runs"]["on" if on else "off"] = m
    a, b = out["runs"]["off"], out["runs"]["on"]
    check(out, "the GPU clock is lowered and a step is kept", b["gpu_share_min"] < 1.0 and b["kept"] >= 1,
          f"min {b['gpu_share_min']}, kept {b['kept']}")
    check(out, "same point", a["point_final"] == b["point_final"], f"{a['point_final']} vs {b['point_final']}")
    check(out, "the point holds >= 97 %", b["smooth_pct"] >= 97.0, f"{b['smooth_pct']} %")
    check(out, "less energy", b["energy_wh"] < a["energy_wh"], f"{b['energy_wh']} vs {a['energy_wh']} Wh")
    return out


@scenario
def gpu_clock_gpu_bound_untouched() -> Dict[str, Any]:
    """A GPU-bound game: the GPU clock is never lowered."""
    out: Dict[str, Any] = {}
    rig = make_rig(VGame("gpu-bound", 50.0), objective="balanced")
    play(rig, 900)
    check(out, "the GPU clock stays the player's", all(r["gpu_share"] == 1.0 for r in rig.timeline))
    return out


def run_all(only: Optional[str] = None) -> Dict[str, Any]:
    results = {}
    for name, fn in SCENARIOS.items():
        if only and only not in name:
            continue
        r = fn()
        r["doc"] = (fn.__doc__ or "").strip()
        r["pass"] = all(c["ok"] for c in r.get("checks", []))
        results[name] = r
    return results


def report_md(results: Dict[str, Any]) -> str:
    lines = ["# GFG Extreme 3.0 sandbox report", "",
             "Generated by `python3 -m sandbox.run --report`. The real GFG Extreme service (pilot, Policy "
             "Coordinator, Governor, Autopilot) runs against a **modelled** Deck (`sandbox/vdeck.py`): "
             "these are model results that check the decisions, not hardware measurements.", "",
             f"Scenarios: {len(results)}, passed: {sum(r['pass'] for r in results.values())}.", ""]
    for name, r in results.items():
        lines.append(f"## {'PASS' if r['pass'] else 'FAIL'} · {name}")
        lines.append("")
        lines.append(r["doc"])
        lines.append("")
        for c in r.get("checks", []):
            lines.append(f"- {'✅' if c['ok'] else '❌'} {c['name']}" + (f" ({c['detail']})" if c["detail"] else ""))
        runs = r.get("runs")
        if runs:
            lines += ["", "| objective | point | smooth % | TDP avg W | draw avg W | energy Wh | max °C |", "|---|---|---|---|---|---|---|"]
            for obj, m in runs.items():
                lines.append(f"| {obj} | {m['point_final']} | {m['smooth_pct']} | {m['tdp_avg']} | {m['draw_avg_w']} | {m['energy_wh']} | {m['temp_max']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--report")
    ap.add_argument("--json")
    a = ap.parse_args()
    results = run_all(a.only)
    for name, r in results.items():
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {name}")
        for c in r.get("checks", []):
            if not c["ok"]:
                print(f"      x {c['name']} {c['detail']}")
    if a.report:
        Path(a.report).write_text(report_md(results))
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(results, indent=1, default=str))
    return 0 if all(r["pass"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
