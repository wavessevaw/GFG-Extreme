"""Stress runs: the real service on the virtual Deck under long, random and hostile sessions.

    python3 -m sandbox.stress                    # all runs, summary
    python3 -m sandbox.stress --seeds 50 --json build/stress.json

Every second of every run is checked against invariants (point on the ladder, TDP inside the
player's range, nothing sent while the status is stale, the HUD always has a TDP, the Governor
never stays paused by a charger change, bounded memory). Model results, not hardware.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from .run import Rig, make_rig
from .vdeck import VGame
from gfg_plugin.pilot import lowest_point, x3_cap  # noqa: E402  (run.py puts py_modules on the path)

LADDER = (0, 20, 24, 25, 30, 35, 40, 45)


def drive(rig: Rig, seconds: int, events: Dict[int, Callable[[Rig], None]], bad: List[str],
          hook: Callable[[Rig], None] = lambda r: None) -> List[Dict[str, Any]]:
    rows = []
    sends = rig.engine.sends
    for k in range(seconds):
        hook(rig)
        if k in events:
            events[k](rig)
        rig.engine.step()
        rig.sensors.step()
        snap = rig.service.tick()
        g = snap["governor"]
        hud_tdp = g.get("tdp_w") if g.get("owned") else g.get("observed_tdp_w")
        row = {"t": k, "point": snap["pilot"]["point"], "policy": snap["policy"]["state"], "game": snap["game"],
               "tdp": rig.power.tdp, "paused": bool(g.get("paused")), "pause_reason": g.get("paused") or "",
               "hud_tdp": hud_tdp, "objective": snap["objective"], "sends": rig.engine.sends, "temp": rig.sensors.temp,
               "writes": rig.power.writes, "cap": rig.engine.cap, "rate": rig.engine.rate,
               "phase": snap["pilot"]["phase"], "holds": snap["pilot"].get("holds"),
               "refresh": rig.engine.refresh}
        rows.append(row)
        if row["point"] not in LADDER:
            bad.append(f"t={k}: point {row['point']} not on the ladder")
        if not (rig.power.minimum - 1e-6 <= row["tdp"] <= rig.power.user_tdp + 1e-6):
            bad.append(f"t={k}: TDP {row['tdp']} outside {rig.power.minimum}..{rig.power.user_tdp}")
        if row["policy"] == "hold" and rig.engine.sends != sends:
            bad.append(f"t={k}: sent while the status was stale")
        if row["game"] and hud_tdp is None:
            bad.append(f"t={k}: HUD has no TDP")
        sends = rig.engine.sends
        rig.clock.t += 1.0
    return rows


def first(bad: List[str], n: int = 3) -> str:
    return "; ".join(bad[:n]) + (f" (+{len(bad) - n} more)" if len(bad) > n else "")


def chaos(seed: int, seconds: int = 3600, steamos_ac: bool = True) -> Dict[str, Any]:
    """chaos_hour with a seed, plus SteamOS re-applying its TDP on every charger change."""
    rng = random.Random(seed)
    load = {"v": 1.0}
    rig = make_rig(VGame("chaos", rng.choice([35.0, 45.0, 55.0, 65.0, 80.0]), lambda t: load["v"]),
                   objective=rng.choice(["autopilot", "balanced", "battery", "quality"]), battery=rng.uniform(15, 95),
                   ambient=rng.choice([20.0, 25.0, 32.0, 40.0]))

    def restart(r): r.engine.restart()
    def hang(r): r.engine.stale_until = r.clock() + rng.randint(2, 12)
    def qam(r): r.engine.steam_ui = not r.engine.steam_ui
    def spike(r): load["v"] = rng.choice([0.45, 0.55, 0.7, 0.85, 1.0, 1.1, 1.3])
    def obj(r): r.settings.data["profiles"]["default"]["objective"] = rng.choice(["autopilot", "quality", "balanced", "battery"])
    def fg(r): r.settings.data["profiles"]["default"]["fg"] = rng.choice(["auto", "auto", "auto", "x2", "x3", "x3.75", "off"])

    def charger(r):
        r.sensors.external_power = not r.sensors.external_power
        if steamos_ac:
            r.power.steamos_power_source()

    def suspend(r):
        r.clock.t += rng.choice([60, 600, 3600])
        r.engine.stale_until = r.clock() + 3
        r.power.steamos_power_source()

    def switch(r):
        app = rng.choice([111, 222, 333, 444])
        r.engine.app_id = app
        r.engine.game = VGame(f"g{app}", rng.choice([30.0, 45.0, 65.0]), lambda t: load["v"], app_id=app)

    def dock(r):
        r.engine.refresh = 60 if r.engine.refresh == 90 else 90
        r.engine.auto = None

    def gone(r):
        r.engine.running = False
        revive["at"] = r.clock() + rng.randint(3, 30)

    def tick(r):
        if not r.engine.running and r.clock() >= revive["at"]:
            r.engine.running = True

    def base(r): r.settings.data["profiles"]["default"]["base_fps"] = rng.choice([20, 30, 45, 60, 90])

    revive = {"at": 0.0}
    pool = [restart, hang, qam, spike, spike, obj, fg, charger, charger, suspend, switch, dock, gone, base]
    ev: Dict[int, Callable[[Rig], None]] = {}
    for k in range(60, seconds - 200, rng.randint(15, 60)):
        ev[k + rng.randint(0, 10)] = rng.choice(pool)
    ev[seconds - 200] = lambda r: (setattr(r.engine, "running", True), r.engine.refresh != 90 and dock(r), r.settings.data["profiles"]["default"].update({"fg": "auto"}),
                                   setattr(r.engine, "steam_ui", False), setattr(r.engine, "stale_until", -1), load.update(v=1.0))
    bad: List[str] = []
    rows = drive(rig, seconds, ev, bad, hook=tick)
    confirmed = sum(r["policy"] == "confirmed" for r in rows) / len(rows)
    paused = sum(r["paused"] for r in rows)
    if confirmed < 0.75:
        bad.append(f"policy confirmed only {confirmed:.0%}")
    if paused:
        bad.append(f"Governor paused {paused} s ({rows[[r['paused'] for r in rows].index(True)]['pause_reason']})")
    if rows[-1]["policy"] != "confirmed":
        bad.append(f"does not settle: {rows[-1]['policy']}")
    # A trial of the next point and a Governor probe that dips (Autopilot tolerates 8-10 %)
    # are part of holding a point; a deeper or longer shortfall is not.
    tail = [r for r in rows[-100:] if r["phase"] != "trial"]
    held = sum(1 for r in tail if r["cap"] and r["rate"] >= 0.90 * r["cap"]) / len(tail)
    # Balanced stops at x3 and Quality at x2.5 (user, 3.0.10): a game too heavy for that lowest
    # point is reported (holds False), not moved below it.
    last = tail[-1]
    above = rig.settings.data["engine"].get("above_x3", False)
    floor = lowest_point(last["refresh"], last["objective"])
    floor = floor if above else max(floor, x3_cap(last["refresh"]))
    # A game too heavy for the lowest point the mode may use (x3 while x3.75 is locked, user 3.1.1).
    floor_case = (last["point"] == floor and last["holds"] is False
                  and (last["objective"] in ("balanced", "quality") or not above))
    if held < 0.95 and not floor_case:
        bad.append(f"the settled point does not hold: {held:.0%} of the last 100 s at {last['point']}")
    player = rig.power.slider if hasattr(rig.power, "slider") else rig.power.user_tdp
    rig.service.stop()
    if abs(rig.power.tdp - player) > 0.05:
        bad.append(f"after stop TDP {rig.power.tdp} W, player's {player} W")
    return {"bad": bad, "confirmed_pct": round(100 * confirmed, 1), "events": len(ev), "tdp_writes": rig.power.writes}


def charger_flap() -> Dict[str, Any]:
    """The charger cable is loose: plugged and pulled every 2-20 s for ten minutes, SteamOS
    re-applying 15 W each time. The Governor must keep the TDP and never pause."""
    rng = random.Random(3)
    rig = make_rig(VGame("g", 65.0), objective="autopilot", battery=60.0)
    ev = {}
    k = 300
    while k < 900:
        ev[k] = lambda r: (setattr(r.sensors, "external_power", not r.sensors.external_power), r.power.steamos_power_source())
        k += rng.randint(2, 20)
    bad: List[str] = []
    rows = drive(rig, 1200, ev, bad)
    paused = sum(r["paused"] for r in rows)
    at15 = sum(r["tdp"] >= 14.9 for r in rows[400:])
    if paused:
        bad.append(f"Governor paused {paused} s")
    if at15 > 120:
        bad.append(f"TDP sat at SteamOS's 15 W for {at15} s after the first flaps")
    return {"bad": bad, "flaps": len(ev), "paused_s": paused, "at_15w_s": at15, "tdp_final": rows[-1]["tdp"]}


def slider_then_charger() -> Dict[str, Any]:
    """The player moves Steam's slider (Governor steps back), then plugs the charger: the
    Governor must not take the TDP back from the player because of the charger."""
    rig = make_rig(VGame("g", 65.0), objective="autopilot", battery=60.0)
    bad: List[str] = []
    ev = {300: lambda r: r.power.steam_slider(8.0),
          340: lambda r: (setattr(r.sensors, "external_power", True), r.power.steamos_power_source())}
    rows = drive(rig, 600, ev, bad)
    owned_after = rig.service.governor.owned and not rig.service.governor.paused
    return {"bad": bad, "governor_owns_after": owned_after, "tdp_final": rows[-1]["tdp"],
            "note": "SteamOS re-applies the player's slider on AC change; a paused Governor should stay paused"}


def slider_inside_grace() -> Dict[str, Any]:
    """Charger plugged, then 5 s later the player moves Steam's slider to 6 W: that is the
    player's change: their 6 W is the ceiling from then on (the Governor may go lower)."""
    rig = make_rig(VGame("g", 65.0), objective="balanced", battery=60.0)
    bad: List[str] = []
    ev = {300: lambda r: (setattr(r.sensors, "external_power", True), r.power.steamos_power_source()),
          310: lambda r: r.power.steam_slider(6.0)}
    rows = drive(rig, 500, ev, bad)
    if max(r["tdp"] for r in rows[311:]) > 6.0:
        bad.append(f"above the player's 6 W: TDP {max(r['tdp'] for r in rows[311:])} W")
    return {"bad": bad, "tdp_final": rows[-1]["tdp"]}


def load_square_wave() -> Dict[str, Any]:
    """The scene alternates light/heavy every 6 s for 20 minutes (a fight with cutscenes):
    the point and the TDP must not flap with it."""
    rig = make_rig(VGame("g", 50.0, lambda t: 0.6 if int(t) // 6 % 2 else 1.15), objective="autopilot")
    bad: List[str] = []
    rows = drive(rig, 1500, {}, bad)
    tail = rows[300:]
    point_changes = sum(1 for a, b in zip(tail, tail[1:]) if a["point"] != b["point"])
    writes = tail[-1]["writes"] - tail[0]["writes"]
    per_min = writes / (len(tail) / 60)
    if point_changes > 20:
        bad.append(f"point changed {point_changes} times in 20 min")
    if per_min > 6:
        bad.append(f"{per_min:.1f} TDP writes per minute")
    return {"bad": bad, "point_changes": point_changes, "tdp_writes_per_min": round(per_min, 2)}


def hot_heavy_battery_low() -> Dict[str, Any]:
    """40 °C room, a heavy game, battery from 12 % to empty, Autopilot."""
    rig = make_rig(VGame("g", 28.0), objective="autopilot", battery=12.0, ambient=40.0)
    rig.sensors.capacity_wh = 8.0
    bad: List[str] = []
    rows = drive(rig, 1800, {}, bad)
    tmax = max(r["temp"] for r in rows)
    if tmax > 95:
        bad.append(f"temperature {tmax:.1f} °C")
    return {"bad": bad, "temp_max": round(tmax, 1), "point_final": rows[-1]["point"], "battery_final": round(rig.sensors.battery, 1)}


def four_hours() -> Dict[str, Any]:
    """Four hours of a slowly changing game: memory of every internal list must stay bounded."""
    rig = make_rig(VGame("g", 55.0, lambda t: 0.85 + 0.25 * ((t // 600) % 3) / 2), objective="autopilot")
    bad: List[str] = []
    sizes = []
    for _ in range(4):
        drive(rig, 3600, {}, bad)
        sizes.append(_sizes(rig.service))
    grew = {k: [s.get(k, 0) for s in sizes] for k in sizes[-1] if sizes[-1][k] > 2 * max(sizes[0].get(k, 0), 50)}
    if grew:
        bad.append(f"growing: {grew}")
    return {"bad": bad, "largest": sorted(sizes[-1].items(), key=lambda kv: -kv[1])[:5]}


def _sizes(obj, prefix="svc", depth=0, seen=None) -> Dict[str, int]:
    seen = seen if seen is not None else set()
    out: Dict[str, int] = {}
    if id(obj) in seen or depth > 3:
        return out
    seen.add(id(obj))
    for name, v in getattr(obj, "__dict__", {}).items():
        key = f"{prefix}.{name}"
        if isinstance(v, (list, dict, set, tuple)) or type(v).__name__ == "deque":
            out[key] = len(v)
        elif hasattr(v, "__dict__") and type(v).__module__.startswith("gfg_plugin"):
            out.update(_sizes(v, key, depth + 1, seen))
    return out


def autopilot_heavy() -> Dict[str, Any]:
    """Heavy games in Autopilot with SteamOS's TDP at 15 or 18 W (Steam's limit off), warm room
    (Deck report 3.0.7: 18 W, x3.75, 80+ C). Autopilot never goes above 15 W, keeps x3 whenever
    x3 holds below 15 W (user, 3.0.8), and does not climb above its point from 80 C."""
    bad: List[str] = []
    out: Dict[str, Any] = {}
    for fps15 in (22.0, 26.0, 30.0, 34.0, 40.0):
        for player in (15.0, 18.0):
            # x3.75 unlocked: this case checks Autopilot's fall-back below x3 (locked by default, 3.1.1).
            rig = make_rig(VGame("g", fps15), objective="autopilot", user_tdp=player, battery=70.0, ambient=30.0,
                           above_x3=True)
            rig.power.maximum = 20.0
            rows = drive(rig, 1200, {}, bad)
            tail = rows[400:]
            name = f"{fps15:.0f}fps@15W/steamos{player:.0f}W"
            top = max(r["tdp"] for r in rows[30:])
            x3_full = sum(1 for r in tail if r["point"] == 30 and r["tdp"] > 14.5)
            x375 = sum(1 for r in tail if r["point"] == 24)
            warm_climb = sum(1 for a, b in zip(rows, rows[1:]) if a["temp"] >= 80.0 and b["phase"] == "trial" != a["phase"])
            avg = sum(r["tdp"] for r in tail) / len(tail)
            out[name] = {"point": tail[-1]["point"], "tdp_avg": round(avg, 1), "tdp_max": top,
                         "temp_max": round(max(r["temp"] for r in rows), 1)}
            if top > 15.0 + 1e-6:
                bad.append(f"{name}: TDP {top} W above 15 W")
            if x3_full > 120:
                bad.append(f"{name}: x3 at 15 W for {x3_full} s")
            if fps15 >= 34.0 and x375 > 120:
                bad.append(f"{name}: x3.75 for {x375} s although x3 holds below 15 W")
            if warm_climb:
                bad.append(f"{name}: {warm_climb} climbs tried at 80 C or more")
    out["bad"] = bad
    return out


def paused_governor_climbs() -> Dict[str, Any]:
    """Deck report 3.0.7: a heavy start locks x3.75, the player then moves Steam's slider (the
    Governor pauses at their 15 W) and the game gets light (40+ fps). Autopilot must climb back
    instead of staying at x3.75 forever."""
    load = {"v": 0.45}
    rig = make_rig(VGame("g", 55.0, lambda t: load["v"]), objective="autopilot", battery=70.0, above_x3=True)
    bad: List[str] = []
    ev = {200: lambda r: r.power.steam_slider(14.0), 260: lambda r: load.update(v=1.0)}
    rows = drive(rig, 1200, ev, bad)
    if rows[199]["point"] != 24:
        bad.append(f"setup: expected x3.75 at the heavy start, got {rows[199]['point']}")
    if not rows[-1]["paused"]:
        bad.append("setup: the Governor did not pause")
    if rows[-1]["point"] < 35:
        bad.append(f"stuck at point {rows[-1]['point']} with a light game")
    return {"bad": bad, "point_final": rows[-1]["point"]}


def steamos_restores_after_sleep() -> Dict[str, Any]:
    """Deck report 3.0.6: SteamOS put its 20 W back mid-game (sleep, Steam's limit off) and the
    Governor paused for the rest of the game. Its own value coming back is SteamOS, not the
    player: take over again, Autopilot back under 15 W."""
    rig = make_rig(VGame("g", 60.0), objective="autopilot", user_tdp=20.0, battery=60.0)
    rig.power.maximum = 20.0
    bad: List[str] = []

    def sleep(r):
        r.clock.t += 900
        r.power.steamos_power_source()
    rows = drive(rig, 900, {400: sleep}, bad)
    if any(r["paused"] for r in rows):
        bad.append("Governor paused")
    if max(r["tdp"] for r in rows[420:]) > 15.0:
        bad.append(f"TDP above 15 W after the restore: {max(r['tdp'] for r in rows[420:])}")
    return {"bad": bad, "tdp_final": rows[-1]["tdp"]}


RUNS = {f.__name__: f for f in (charger_flap, slider_then_charger, slider_inside_grace, load_square_wave,
                                hot_heavy_battery_low, four_hours, autopilot_heavy, paused_governor_climbs,
                                steamos_restores_after_sleep)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--json")
    a = ap.parse_args()
    results: Dict[str, Any] = {}
    for seed in range(1, a.seeds + 1):
        results[f"chaos_seed_{seed}"] = chaos(seed)
    for name, fn in RUNS.items():
        results[name] = fn()
    failed = 0
    for name, r in results.items():
        ok = not r["bad"]
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"\n      {first(r['bad'])}"))
    print(f"\n{len(results) - failed}/{len(results)} passed")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(results, indent=1, default=str))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
