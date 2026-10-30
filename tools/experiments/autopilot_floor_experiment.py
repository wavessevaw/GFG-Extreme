"""Exploratory virtual-only comparison; does not modify product source or certify Deck.

Declared before running: compare the same ten deterministic cases and 1,200-second
sessions. Reject this hypothesis for integration if it adds below-93%-of-point seconds,
increases TDP writes, or increases simulated session energy in any case. This deliberately
strict screen is not a device acceptance threshold; it also cannot validate visual quality.
"""
import json
import statistics
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "py_modules"))
from gfg_plugin.governor import PowerGovernor
from gfg_plugin.pilot import BAND_MAX_W
from sandbox.stress import VGame, make_rig, drive

original = PowerGovernor._stable_check


def candidate(self, draw):
    floor = self.floors.get(self.cap)
    if (not self.stable and self.objective == "autopilot" and self.tdp is not None
            and self.tdp > BAND_MAX_W and floor is not None and floor[0] < self.tdp - 1.5):
        return False
    return original(self, draw)


def run(fps, player, modified):
    PowerGovernor._stable_check = candidate if modified else original
    rig = make_rig(VGame("g", fps), objective="autopilot", user_tdp=player,
                   battery=70.0, ambient=30.0, above_x3=True)
    rig.power.maximum = 20.0
    bad = []
    draws = []
    try:
        rows = drive(rig, 1200, {}, bad, hook=lambda r: draws.append(r.power.draw))
        tail = rows[400:]
        return {
            "x375_seconds_tail": sum(r["point"] == 24 for r in tail),
            "real_below_93pct_seconds": sum(r["point"] > 0 and r["rate"] < .93 * r["point"] for r in rows),
            "avg_tdp_w_tail": statistics.fmean(r["tdp"] for r in tail),
            "energy_wh_session": sum(draws) / 3600.0,
            "tdp_writes": rig.power.writes,
            "point_changes": sum(a["point"] != b["point"] for a, b in zip(rows, rows[1:])),
            "max_temp_c": max(r["temp"] for r in rows),
            "invariant_violations": bad,
        }
    finally:
        rig.service.stop()


try:
    result = {f"{fps:.0f}@{player:.0f}": {"before": run(fps, player, False),
                                            "candidate": run(fps, player, True)}
              for fps in (22., 26., 30., 34., 40.) for player in (15., 18.)}
    print(json.dumps({"class": "simulation; experimental; no device evidence", "cases": result}, indent=2))
finally:
    PowerGovernor._stable_check = original
