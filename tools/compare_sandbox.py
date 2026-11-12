"""Compare named sandbox checks across saved runs; this is not a hardware benchmark.

Usage: python tools/compare_sandbox.py baseline.json stable.json candidate.json
Reports missing or failed checks. Changed check names and numerical values need human
investigation; this tool cannot prove equivalent predicates or image quality.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def checks(results):
    if not isinstance(results, dict) or not results:
        raise ValueError("results must be a nonempty scenario object")
    out = {}
    for scenario, result in results.items():
        if not isinstance(scenario, str) or not isinstance(result, dict):
            raise ValueError("invalid scenario entry")
        entries = result.get("checks")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{scenario}: no checks")
        names = {}
        for check in entries:
            if not isinstance(check, dict):
                raise ValueError(f"{scenario}: invalid check")
            name, ok = check.get("name"), check.get("ok")
            if not isinstance(name, str) or not name or type(ok) is not bool or name in names:
                raise ValueError(f"{scenario}: invalid or duplicate check name/status")
            names[name] = ok
        if result.get("pass") is not all(names.values()):
            raise ValueError(f"{scenario}: inconsistent scenario status")
        out[scenario] = names
    return out


def numeric_leaves(value, path=()):
    """Finite scalar model outputs, excluding check metadata and booleans."""
    found = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ("checks", "pass", "doc"):
                continue
            found.update(numeric_leaves(child, path + (str(key),)))
    elif type(value) in (int, float) and math.isfinite(value):
        pointer = "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path)
        found[pointer] = value
    return found


def compare(reference, target):
    ref, got = checks(reference), checks(target)
    missing_scenarios = sorted(ref.keys() - got.keys())
    missing_checks = {s: sorted(ref[s].keys() - got[s].keys()) for s in sorted(ref.keys() & got.keys())
                      if ref[s].keys() - got[s].keys()}
    failed_reference = {s: sorted(name for name, ok in entries.items() if not ok)
                        for s, entries in ref.items() if not all(entries.values())}
    failed = {s: sorted(name for name, ok in entries.items() if not ok)
              for s, entries in got.items() if not all(entries.values())}
    added_scenarios = sorted(got.keys() - ref.keys())
    numeric_changes = {}
    missing_numeric = {}
    added_numeric = {}
    for scenario in sorted(ref.keys() & got.keys()):
        before = numeric_leaves(reference[scenario])
        after = numeric_leaves(target[scenario])
        if before.keys() - after.keys():
            missing_numeric[scenario] = sorted(before.keys() - after.keys())
        if after.keys() - before.keys():
            added_numeric[scenario] = sorted(after.keys() - before.keys())
        changed = {path: {"reference": before[path], "target": after[path],
                          "delta": after[path] - before[path]}
                   for path in sorted(before.keys() & after.keys()) if before[path] != after[path]}
        if changed:
            numeric_changes[scenario] = changed
    return {"missing_scenarios": missing_scenarios, "missing_checks": missing_checks,
            "failed_reference_checks": failed_reference, "failed_checks": failed, "added_scenarios": added_scenarios,
            "observed_numeric_changes": numeric_changes, "missing_numeric": missing_numeric, "added_numeric": added_numeric,
            "status": "BLOCKED" if missing_scenarios or missing_checks or failed_reference or failed else "UNVERIFIED"}


def load_result(path):
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("stable")
    parser.add_argument("candidate")
    parser.add_argument("--output")
    for label in ("baseline", "stable", "candidate"):
        parser.add_argument(f"--{label}-revision", help="caller-supplied source revision, not independently verified")
    args = parser.parse_args()
    try:
        paths = (args.baseline, args.stable, args.candidate)
        loaded = [load_result(path) for path in paths]
        runs = [entry[0] for entry in loaded]
        inputs = [{"label": label, "path": path, "sha256": entry[1],
                   "claimed_revision": getattr(args, label + "_revision")}
                  for label, path, entry in zip(("baseline", "stable", "candidate"), paths, loaded)]
        report = {"evidence_class": "simulation", "inputs": inputs, "baseline_to_stable": compare(runs[0], runs[1]),
                  "baseline_to_candidate": compare(runs[0], runs[2]),
                  "stable_to_candidate": compare(runs[1], runs[2]),
                  "limitations": "Model numbers are unqualified observations, not evidence of improvement or hardware measurements. Predicates, thresholds, comparability, pacing and image quality require independent review."}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"invalid input: {exc}\n")
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if any(v["status"] == "BLOCKED" for k, v in report.items() if k.endswith("_to_candidate") or k == "baseline_to_stable") else 0


if __name__ == "__main__":
    raise SystemExit(main())
