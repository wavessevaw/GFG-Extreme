"""Diagnostic only: automatic versus fixed x3, with identical workload and seeds.

Predeclared design: fps15=34, seeds 1..5, user TDP 15/18 W, 1200 seconds,
90 Hz, battery 70%, ambient 30 C, above-x3 allowed. Observe every second,
including startup; also report seconds 400..1199. No candidate injection,
acceptance threshold, hardware inference, or retrospective exclusion of seeds.
Energy is sampled AFTER the engine step, including the final second.
The fixed arm explicitly overrides the in-memory profile AFTER normalization:
3.2.2 normalizes saved x3 to auto. This is controller isolation, not a claim
that the historical UI exposed fixed x3. Auto uses the normal profile path.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.output.exists():
        raise SystemExit("output already exists; preserve prior observations")
    sha = subprocess.check_output(["git", "rev-parse", args.source + "^{commit}"], cwd=root, text=True).strip()
    subprocess.run(["git", "diff", "--exit-code", sha, "--", "py_modules", "sandbox"], cwd=root, check=True)
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", "py_modules", "sandbox"], cwd=root, text=True).strip():
        raise SystemExit("product or sandbox changes present")
    # Ignore pre-existing bytecode; -B alone only prevents new cache writes.
    sys.pycache_prefix = str(args.output.resolve().with_suffix(".unused-cache"))
    if Path(sys.pycache_prefix).exists():
        raise SystemExit("cache isolation directory must not exist")
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root), str(root / "py_modules")]
    from sandbox.run import make_rig
    from sandbox.vdeck import VGame

    cases = []
    for seed in range(1, 6):
        for limit in (15., 18.):
            for mode in ("auto", "x3"):
                rig = make_rig(VGame("g", 34., seed=seed), fg=mode, objective="autopilot",
                               user_tdp=limit, battery=70., ambient=30., above_x3=True)
                rig.power.maximum = 20.
                normalized_mode = rig.settings.data["profiles"]["default"]["fg"]
                if mode == "x3":
                    rig.settings.data["profiles"]["default"]["fg"] = "x3"
                rows = []
                try:
                    for second in range(1200):
                        rig.engine.step()
                        rig.sensors.step()
                        snap = rig.service.tick()
                        rows.append({"t": second, "cap": rig.engine.cap,
                                     "rate": rig.engine.rate, "draw_w": rig.power.draw,
                                     "tdp_w": rig.power.tdp, "point": snap["pilot"]["point"],
                                     "fg": snap["fg"],
                                     "confirmed": snap["policy"]["state"] == "confirmed"})
                        rig.clock.t += 1.
                    def metrics(part):
                        return {"seconds": len(part), "energy_wh": sum(r["draw_w"] for r in part) / 3600.,
                                "mean_real_fps": sum(r["rate"] for r in part) / len(part),
                                "cap_24_seconds": sum(r["cap"] == 24 for r in part),
                                "cap_30_seconds": sum(r["cap"] == 30 for r in part),
                                "below_27_9_fps_seconds": sum(r["rate"] < .93 * 30 for r in part),
                                "unconfirmed_seconds": sum(not r["confirmed"] for r in part)}
                    cases.append({"seed": seed, "limit_w": limit, "mode": mode,
                                  "normalized_mode": normalized_mode,
                                  "controller_fixture_override": mode == "x3",
                                  "observed_modes": sorted({r["fg"] for r in rows}),
                                  "session": metrics(rows), "tail": metrics(rows[400:]),
                                  "tdp_writes_before_stop": rig.power.writes,
                                  "journal": list(rig.log)})
                finally:
                    rig.service.stop()
    result = {"classification": "SIMULATION; diagnostic only; hardware UNVERIFIED",
              "source_commit": sha, "python": platform.python_version(), "platform": platform.platform(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "sampling": "post engine step; 1200 seconds; tail starts at 400; all five seeds retained",
              "cases": cases}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"saved {len(cases)} cases to {args.output}")


if __name__ == "__main__":
    main()
