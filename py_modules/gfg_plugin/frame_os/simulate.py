"""Session simulation for GFG Frame OS policy tuning (development tool, no hardware).

A synthetic 10-minute session: exploration with occasional camera pans, combat bursts, a pause
menu, scene cuts.  Power model: the APU draws ``idle_w + w_per_real * real_fps * scene`` (a
real frame costs energy; a generated one costs a small fixed overhead).  Compares the current
Governor behaviour (fixed calm point) with Frame OS injection + energy broker.

Numbers are a model, not a measurement: they tell whether the policy does what it is meant to
(real frames where motion is, no extra energy overall), and tune its constants before a Deck test.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .policy import EnergyBroker, InjectionPolicy
from .scene import SceneChangeDetector

TICK_S = 0.1


def session(seed: int = 7, minutes: float = 10.0) -> List[Tuple[float, Dict[str, float], float, bool]]:
    """(t, input snapshot, scene complexity, cut) per tick."""
    rng = random.Random(seed)
    out = []
    t, phase_end, phase = 0.0, 0.0, "explore"
    scene = 1.0
    last_input = 0.0
    while t < minutes * 60:
        if t >= phase_end:
            phase = rng.choices(["explore", "combat", "menu"], [0.6, 0.3, 0.1])[0]
            phase_end = t + {"explore": rng.uniform(20, 60), "combat": rng.uniform(10, 30),
                             "menu": rng.uniform(25, 45)}[phase]
        cut = rng.random() < 0.004
        if cut:
            scene = rng.uniform(0.8, 1.3)
        if phase == "menu":
            camera, action = 0.0, 0.0
        elif phase == "combat":
            camera = min(1.0, abs(rng.gauss(0.6, 0.25)))
            action = min(1.0, abs(rng.gauss(0.6, 0.2)))
        else:
            camera = 0.8 if rng.random() < 0.08 else abs(rng.gauss(0.1, 0.1))
            action = 0.3 if rng.random() < 0.05 else 0.0
        if camera > 0.15 or action > 0.1:
            last_input = t
        out.append((t, {"camera": camera, "action": action, "idle_s": t - last_input}, scene, cut))
        t += TICK_S
    return out


def draw_w(real_hz: float, scene: float, cap_w: float, idle_w: float = 3.0, w_per_real: float = 0.22) -> float:
    return min(cap_w, idle_w + w_per_real * real_hz * scene)


def run(frame_os: bool, seed: int = 7, calm_w: float = 10.0) -> Dict[str, float]:
    events = session(seed)
    broker = EnergyBroker(calm_w=calm_w) if frame_os else None
    policy = InjectionPolicy(output_hz=90, calm_real_hz=30, broker=broker)
    scene_detector = SceneChangeDetector()
    energy = motion_real = motion_ticks = boosts = 0.0
    latency = 0.0
    last_draw = None
    for t, inp, scene, cut in events:
        if frame_os:
            cost = 1000.0 / 30 * 0.6 * scene
            d = policy.tick(t, inp, scene_change=scene_detector.tick(t, cost), draw_w=last_draw)
            real, cap = d.real_hz, d.tdp_w or calm_w
            boosts += d.level == "boost"
            if d.level == "rest":
                real = 30.0
        else:
            real, cap = 30.0, calm_w
        w = draw_w(real, scene, cap)
        last_draw = w
        energy += w * TICK_S
        latency += 1000.0 / real
        if inp["camera"] >= 0.5:
            motion_ticks += 1
            motion_real += real
    n = len(events)
    return {
        "energy_wh": round(energy / 3600.0, 3),
        "avg_w": round(energy / (n * TICK_S), 2),
        "real_fps_in_motion": round(motion_real / motion_ticks, 1) if motion_ticks else 0.0,
        "frame_time_ms_avg": round(latency / n, 1),
        "boost_share": round(boosts / n, 3),
    }


def compare(seed: int = 7) -> Dict[str, Dict[str, float]]:
    return {"governor": run(False, seed), "frame_os": run(True, seed)}


if __name__ == "__main__":
    for name, result in compare().items():
        print(f"{name:9s} {result}")
