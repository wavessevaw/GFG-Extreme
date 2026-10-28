"""Replay of real Deck telemetry through the real GFG Extreme service on the virtual Deck.

    python3 -m sandbox.replay LOGDIR [LOGDIR ...] [--since TS] [--split] [--json out.json]

LOGDIR is an unpacked GFG report folder (the one holding samples.jsonl, samples.jsonl.1, ...).
The files are read as data only (JSON lines), nothing in them is executed.

What it does: every 1 s sample says what the game rendered (real), how busy the GPU and the
busiest CPU core were, and at which TDP. Inverting the virtual Deck's own model (vdeck.VGame,
VSensors) gives the scene load per second, independent of what the controllers did then:

    GPU frames at 15 W  = (100 * real / gpu busy) / ((TDP - 2.5) / 12.5) ** 0.55  (/ 0.92 generating)
    CPU frames          = 95 * real / busiest core %          (/ the CPU clock share when capped)

That scene then plays again, second by second, on the virtual Deck under today's Governor,
pilot and policy coordinator: one Service for the whole replay (the game book and the TDP model
learn across sessions, as on the Deck), each session with the player's TDP, refresh rate,
objective changes, charger and battery from the telemetry. The room temperature per session is
fitted so the model's APU temperature matches the recorded one at the recorded draw.

Counted per hour of game time: TDP writes, policy changes (multiplier / base FPS / Auto floor
the engine is told), locked-point changes, trials, CPU-cap changes; the share of seconds the
game falls short of its point, real fps, the model's APU draw (energy proxy) and the time spent
at each point. "Steady" seconds lie in 5-minute stretches whose scene load varies by at most
15 % (p90 / p10 of a 10 s median).

Model results on recorded scene load, not a Deck measurement: the fps-against-watts curve and
the draw are vdeck's, and frame-time noise inside a second is not in a 1 s sample.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .run import Rig, make_rig
from .vdeck import CPU_MAX_KHZ, VGame

GAP_S = 15.0          # samples further apart start a new session
MIN_SESSION_S = 120   # shorter sessions (a launch and quit) are left out
IDLE_TICKS = 15       # Steam's own UI between two sessions: the service ends the game
MAX_JUMP_S = 3600.0   # the clock between sessions jumps at most this far (floors age)
GPU_MIN_PCT = 25.0    # a GPU (or CPU) busy reading under this is not trusted for the inversion
FPS15_MAX = 240.0
STEADY_S = 300
STEADY_SPREAD = 1.15
SHORT_RATIO = 0.93    # Autopilot's tolerated dip (user, 3.1.1)
DEEP_RATIO = 80.0 / 90.0  # an output dip under 80 of 90 (user: 80-83 of 90 is still fine)


def load_samples(dirs: Iterable[str], since: float = 0.0, until: float = float("inf")) -> List[Dict[str, Any]]:
    """Every sample of every report folder, de-duplicated by time (the zips overlap)."""
    seen: Dict[float, Dict[str, Any]] = {}
    for d in dirs:
        for f in sorted(Path(d).glob("samples.jsonl*")):
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    t = r.get("t") if isinstance(r, dict) else None
                    if isinstance(t, (int, float)) and since <= t < until:
                        seen[round(float(t), 1)] = r
    return [seen[k] for k in sorted(seen)]


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def sessions(rows: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Contiguous samples of one game at one refresh rate, gaps filled with the last sample."""
    out: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for r in rows:
        if not r.get("app") or not r.get("hz"):
            continue
        if cur and (r["t"] - cur[-1]["t"] > GAP_S or r["app"] != cur[-1]["app"] or r["hz"] != cur[-1]["hz"]):
            out.append(cur)
            cur = []
        if cur:
            for k in range(1, int(round(r["t"] - cur[-1]["t"]))):
                cur.append({**cur[-1], "t": cur[-1]["t"] + 1.0})
        cur.append(r)
    if cur:
        out.append(cur)
    return [s for s in out if len(s) >= MIN_SESSION_S]


def scene(session: List[Dict[str, Any]], gen_cost: Optional[float] = None) -> Dict[str, List[float]]:
    """Per second: the GPU frames the scene allows at 15 W (vdeck's power law) and the frames the
    CPU can prepare at full clock. A second without readings keeps the last one."""
    gpu15: List[float] = []
    cpu: List[float] = []
    g_last, c_last = 40.0, 200.0
    for r in session:
        real, gpu, top = _num(r.get("real")), _num(r.get("gpu")), _num(r.get("cpu"))
        tdp = _num(r.get("tdp")) or _num(r.get("ceiling")) or 15.0
        khz = _num(r.get("cpu_cap_khz"))
        share = min(1.0, khz / CPU_MAX_KHZ) if khz else 1.0
        fps, mult = _num(r.get("fps")), r.get("mult")
        generating = bool(mult) and fps is not None and real is not None and fps > 1.3 * real
        if real is not None and real > 1.0 and gpu is not None:
            freed = 3.0 * (1.0 - share * share)
            g_cap = 100.0 * real / max(gpu, GPU_MIN_PCT)
            f = (max(tdp + 0.6 * freed - 2.5, 0.1) / 12.5) ** 0.55
            lost = 0.08 if gen_cost is None else gen_cost * max(0.0, (fps or 0.0) - real) / 60.0
            g_last = min(FPS15_MAX, g_cap / f / ((1.0 - lost) if generating else 1.0))
        if real is not None and real > 1.0 and top is not None:
            c_last = min(FPS15_MAX * 2, 95.0 * real / max(top, GPU_MIN_PCT) / share)
        gpu15.append(g_last)
        cpu.append(c_last)
    return {"gpu15": gpu15, "cpu": cpu}


def steady_mask(load: List[float]) -> List[bool]:
    """Seconds inside a 5-minute stretch whose (10 s median) scene load varies by <= 15 %."""
    n = len(load)
    smooth = [statistics.median(load[max(0, i - 5):i + 5]) for i in range(n)]
    mask = [False] * n
    for start in range(0, max(1, n - STEADY_S + 1), 30):
        win = sorted(smooth[start:start + STEADY_S])
        if len(win) < STEADY_S:
            break
        p10, p90 = win[len(win) // 10], win[(9 * len(win)) // 10]
        if p10 > 0 and p90 / p10 <= STEADY_SPREAD:
            for i in range(start, start + STEADY_S):
                mask[i] = True
    return mask


class ReplayGame(VGame):
    """A VGame whose 15 W frames follow the recorded scene, second by second (no added noise)."""

    def __init__(self, app_id: int, sc: Dict[str, List[float]], t0: float, noise: float = 0.0, seed: int = 1) -> None:
        super().__init__(f"app{app_id}", 1.0, lambda t: self.at("gpu15", t), app_id=app_id, noise=noise,
                         seed=seed + app_id, cpu_fps=sc["cpu"][0])
        self.sc, self.t0 = sc, t0

    def at(self, key: str, t: float) -> float:
        arr = self.sc[key]
        return arr[min(len(arr) - 1, max(0, int(t - self.t0)))]


def replay(rows: List[Dict[str, Any]], split: bool = False, gpu_clock: bool = False, noise: float = 0.0,
           seed: int = 1, strict: bool = False, gen_cost: Optional[float] = None,
           objective: Optional[str] = None) -> Dict[str, Any]:
    """noise/seed: extra +-noise per second on the scene (vdeck's own), to see how far a result
    moves on a slightly different playthrough of the same scenes. strict: the engine draws honest
    multipliers. gen_cost: generation's cost per 60 generated frames a second (None: a flat 8 %).
    objective: every session in this objective instead of the recorded ones."""
    ss = sessions(rows)
    if not ss:
        return {"sessions": 0}
    first = ss[0]
    rig: Rig = make_rig(VGame("idle", 40.0, app_id=769), objective="autopilot", refresh=int(first[0]["hz"]),
                        user_tdp=float(_num(first[0].get("ceiling")) or 15.0), split=split, gpu_clock=gpu_clock,
                        game_list=True)
    rig.engine.app_id = 769
    rig.engine.strict, rig.engine.gen_cost = strict, gen_cost
    acc = Acc()
    for i, s in enumerate(ss):
        if i:
            rig.clock.t += min(MAX_JUMP_S, max(0.0, s[0]["t"] - ss[i - 1][-1]["t"]))
        _play_session(rig, s, acc, noise, seed + i, gen_cost, objective)
    out = acc.result()
    out["sessions"] = len(ss)
    # Why the TDP and the point moved (the journal), for reading the numbers.
    out["tdp_why"] = dict(Counter(str(e.get("why", "")).split(":")[0] for e in rig.log
                                  if e.get("kind") == "governor-tdp").most_common())
    out["governor_events"] = dict(Counter(e["kind"] + (":" + str(e.get("reason")).split(":")[0] if e.get("reason") else "")
                                          for e in rig.log if e.get("kind", "").startswith("governor-")
                                          and e.get("kind") != "governor-tdp").most_common(16))
    out["pilot_why"] = dict(Counter(_reason(e.get("reason", "")) for e in rig.log if e.get("kind") == "pilot").most_common(12))
    return out


def _reason(text: str) -> str:
    """A pilot reason without its numbers, to count kinds."""
    return "".join("#" if ch.isdigit() else ch for ch in str(text)).replace("##", "#")[:48]


def _idle(rig: Rig, ticks: int) -> None:
    rig.engine.app_id = 769
    for _ in range(ticks):
        rig.engine.step()
        rig.sensors.step()
        rig.service.tick()
        rig.clock.t += 1.0


def _play_session(rig: Rig, s: List[Dict[str, Any]], acc: "Acc", noise: float = 0.0, seed: int = 1,
                  gen_cost: Optional[float] = None, objective: Optional[str] = None) -> None:
    _idle(rig, IDLE_TICKS)
    sc = scene(s, gen_cost)
    hz = int(s[0]["hz"])
    ceiling = float(_num(s[0].get("ceiling")) or 15.0)
    p = rig.power
    p.user_tdp = p.tdp = ceiling
    p.maximum = max(15.0, ceiling)
    if hasattr(p, "slider"):
        del p.slider
    draws = [(_num(r.get("temp")), _num(r.get("draw"))) for r in s]
    amb = [t - 15.0 - 2.6 * d for t, d in draws if t is not None and d is not None]
    rig.sensors.ambient = min(45.0, max(10.0, statistics.median(amb))) if amb else 25.0
    rig.sensors.temp = next((t for t, _ in draws if t is not None), 45.0)
    eng = rig.engine
    if eng.refresh != hz:
        eng.refresh, eng.auto = hz, None
    t0 = rig.clock()
    game = ReplayGame(int(s[0]["app"]), sc, t0, noise, seed)
    eng.game, eng.app_id = game, game.app_id
    load = [min(g, c) for g, c in zip(sc["gpu15"], sc["cpu"])]
    mask = steady_mask(load)
    # The game's class from its median frames at 15 W: light 50+, medium 35-50, heavy under 35.
    med = statistics.median(load)
    acc.cls = "light" if med >= 50 else ("medium" if med >= 35 else "heavy")
    prof = rig.settings.data["profiles"]["default"]
    ac = s[0].get("ac")
    rig.sensors.external_power = bool(ac)
    for k, r in enumerate(s):
        obj = objective or r.get("objective")
        if obj in ("autopilot", "battery", "balanced", "quality") and obj != prof["objective"]:
            prof["objective"] = obj
        if isinstance(r.get("ac"), bool) and r["ac"] != ac:
            ac = r["ac"]
            rig.sensors.external_power = ac
            p.steamos_power_source()   # SteamOS puts its own TDP back on a charger change
        bat = _num(r.get("bat"))
        if bat is not None:
            rig.sensors.battery = bat
        game.cpu_fps = sc["cpu"][k]
        writes, cpu_share, logged = p.writes, eng.cpu_share, len(rig.log)
        eng.step()
        rig.sensors.step()
        snap = rig.service.tick()
        acc.add(rig, snap, writes, cpu_share, mask[k], prof["objective"], rig.log[logged:])
        rig.clock.t += 1.0
    acc.end_session()


def _aim(eng: Any, point: int) -> int:
    """What the game should hold: the cap, or under honest xN the pilot's point (the cap is
    refresh / N there and the Governor aims at the point)."""
    if eng.strict and eng._int("kfg_multiplier") >= 2 and point:
        return min(eng.cap, int(point))
    return eng.cap


def _even(eng: Any, point: int = 0) -> bool:
    """An even cadence this second: the game holds its aim and every frame is shown the same
    number of refreshes (the output divides the refresh)."""
    aim = _aim(eng, point)
    if eng.rate < 0.98 * aim:
        return False
    mult = eng._int("kfg_multiplier")
    if mult >= 2 and eng.strict:
        return eng.refresh % (mult * aim) == 0
    return mult >= 2 or eng.refresh % eng.cap == 0


class Acc:
    """Counts per hour of game time, all and steady seconds, per objective."""

    def __init__(self) -> None:
        self.groups: Dict[str, Dict[str, Any]] = {}
        self.prev: Optional[Dict[str, Any]] = None
        self.paces: deque = deque(maxlen=8)
        self.cls = ""

    def _g(self, name: str) -> Dict[str, Any]:
        return self.groups.setdefault(name, Counter())

    def end_session(self) -> None:
        self.prev = None
        self.paces.clear()

    def add(self, rig: Rig, snap: Dict[str, Any], writes_before: int, share_before: float, steady: bool,
            objective: str, journal: List[Dict[str, Any]] = ()) -> None:
        if not snap.get("game"):
            self.prev = None
            return
        eng = rig.engine
        pol = (eng._int("kfg_multiplier"), eng._int("kfg_base_fps"), eng._int("kfg_auto_floor"))
        pilot = snap["pilot"]
        cur = {"policy": pol, "point": pilot["point"], "phase": pilot["phase"]}
        prev = self.prev
        self.prev = cur
        pace = (snap.get("live") or {}).get("pace")
        if pace is not None:
            self.paces.append(pace)
        ev = {
            "s": 1,
            "tdp_writes": rig.power.writes - writes_before,
            "policy_changes": int(prev is not None and prev["policy"] != pol),
            "point_changes": int(prev is not None and prev["point"] != cur["point"]),
            "trials": int(prev is not None and cur["phase"] == "trial" and prev["phase"] != "trial"),
            "cpu_cap_changes": int(abs(eng.cpu_share - share_before) > 1e-6),
            "real": eng.rate,
            "draw": rig.power.draw,
            "tdp": rig.power.tdp,
            "capped_s": int(eng.cap > 0),
            "short_s": int(eng.cap > 0 and eng.rate < SHORT_RATIO * _aim(eng, pilot["point"])),
            "deep_s": int(eng.cap > 0 and eng.rate < DEEP_RATIO * _aim(eng, pilot["point"])),
            "pace8_s": int(len(self.paces) == 8 and statistics.fmean(self.paces) < 0.98),
            "hot_s": int(rig.sensors.temp >= 85.0),
            "out": eng.out_rate,
            "even_s": int(eng.cap > 0 and pilot["phase"] in ("locked", "fixed") and _even(eng, pilot["point"])),
        }
        names = ["all", f"obj:{objective}"] + (["steady"] if steady else []) + ([f"class:{self.cls}"] if self.cls else [])
        for name in names:
            g = self._g(name)
            for key, v in ev.items():
                g[key] += v
            if eng.cap > 0 and pilot["phase"] in ("locked", "fixed"):
                g[f"at:{pilot['point']}"] += 1
                mult = eng._int("kfg_multiplier")
                g[f"pair:{'x%d' % mult if mult >= 2 and eng.strict else ('fill' if mult == 1 else 'x%d' % mult)}@{_aim(eng, pilot['point'])}"] += 1
            for e in journal:
                if e.get("kind") == "governor-tdp":
                    g["why:" + str(e.get("why", "")).split(":")[0]] += 1

    def result(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, g in sorted(self.groups.items()):
            n = g["s"]
            h = n / 3600.0
            if not n:
                continue
            locked = sum(v for k, v in g.items() if k.startswith("at:")) or 1
            out[name] = {
                "hours": round(h, 2),
                "tdp_writes_h": round(g["tdp_writes"] / h, 1),
                "policy_changes_h": round(g["policy_changes"] / h, 1),
                "point_changes_h": round(g["point_changes"] / h, 1),
                "trials_h": round(g["trials"] / h, 1),
                "cpu_cap_changes_h": round(g["cpu_cap_changes"] / h, 1),
                "short_pct": round(100.0 * g["short_s"] / max(1, g["capped_s"]), 2),
                "deep_pct": round(100.0 * g["deep_s"] / max(1, g["capped_s"]), 2),
                "pace8_pct": round(100.0 * g["pace8_s"] / n, 2),
                "real_fps": round(g["real"] / n, 2),
                "draw_w": round(g["draw"] / n, 3),
                "tdp_w": round(g["tdp"] / n, 2),
                "energy_wh": round(g["draw"] / 3600.0, 1),
                "hot_pct": round(100.0 * g["hot_s"] / n, 2),
                "out_fps": round(g["out"] / n, 2),
                "even_pct": round(100.0 * g["even_s"] / max(1, g["capped_s"]), 2),
                "pairs_pct": {k[5:]: round(100.0 * v / locked, 1) for k, v in sorted(g.items(), key=lambda kv: -kv[1])
                              if k.startswith("pair:")},
                "tdp_why_h": {k[4:]: round(v / h, 1) for k, v in sorted(g.items(), key=lambda kv: -kv[1])
                              if k.startswith("why:")},
                "points_pct": {k[3:]: round(100.0 * v / locked, 1) for k, v in sorted(g.items(), key=lambda kv: kv[0])
                               if k.startswith("at:")},
            }
        return out


def table(res: Dict[str, Any], groups: Iterable[str] = ("all", "steady", "obj:autopilot")) -> str:
    cols = ("hours", "tdp_writes_h", "policy_changes_h", "point_changes_h", "trials_h", "cpu_cap_changes_h",
            "short_pct", "deep_pct", "pace8_pct", "real_fps", "draw_w", "tdp_w", "hot_pct")
    lines = ["group           " + " ".join(f"{c:>17}" for c in cols)]
    for g in groups:
        if g in res:
            lines.append(f"{g:<16}" + " ".join(f"{res[g][c]:>17}" for c in cols))
            lines.append(f"{'':<16} points: {res[g]['points_pct']}")
            lines.append(f"{'':<16} TDP writes/h by reason: {res[g]['tdp_why_h']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--since", type=float, default=0.0)
    ap.add_argument("--until", type=float, default=float("inf"))
    ap.add_argument("--split", action="store_true", help="Power Split on (off by default since 3.3.0)")
    ap.add_argument("--noise", type=float, default=0.0, help="extra per-second scene noise (0.02 = +-2 %%)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = load_samples(a.dirs, a.since, a.until)
    res = replay(rows, split=a.split, noise=a.noise, seed=a.seed)
    print(f"{res.get('sessions', 0)} sessions, {len(rows)} samples")
    print(table(res))
    print("TDP writes by reason:", res.get("tdp_why"))
    print("pilot moves by reason:", res.get("pilot_why"))
    print("governor events:", res.get("governor_events"))
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
