"""Flag changes to the historical sandbox scenarios and selected helpers.

This is a conservative source comparison, not proof of equivalent behavior. Changes
require review even when harmless. Dependencies outside the selected definitions and
runtime behavior are not covered. A matching comparison remains UNVERIFIED.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


BASELINE_SHA256 = "3d74ff5a65381ebcb9ff42a32dd9938481e3044e9836828c46290ee2ad0e5764"
HELPERS = ("MemSettings", "Rig", "make_rig", "play", "metrics", "scenario", "check", "_objective_run")


def contracts(source):
    tree = ast.parse(source)
    scenarios = {}
    helpers = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name in HELPERS:
            if node.name in helpers:
                raise ValueError(f"duplicate helper: {node.name}")
            helpers[node.name] = ast.dump(node, include_attributes=False)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                isinstance(decorator, ast.Name) and decorator.id == "scenario"
                for decorator in node.decorator_list):
            if node.name in scenarios:
                raise ValueError(f"duplicate scenario: {node.name}")
            scenarios[node.name] = ast.dump(node, include_attributes=False)
    return scenarios, helpers


def compare(baseline, target):
    reference, reference_helpers = contracts(baseline)
    candidate, candidate_helpers = contracts(target)
    if len(reference) != 39 or set(reference_helpers) != set(HELPERS):
        raise ValueError("baseline must have 39 distinct scenarios and all tracked helpers")
    missing = sorted(reference.keys() - candidate.keys())
    changed = sorted(name for name in reference.keys() & candidate.keys()
                     if reference[name] != candidate[name])
    missing_helpers = sorted(reference_helpers.keys() - candidate_helpers.keys())
    changed_helpers = sorted(name for name in reference_helpers.keys() & candidate_helpers.keys()
                             if reference_helpers[name] != candidate_helpers[name])
    return {
        "baseline_scenarios": len(reference),
        "candidate_scenarios": len(candidate),
        "missing_scenarios": missing,
        "changed_scenarios": changed,
        "added_scenarios": sorted(candidate.keys() - reference.keys()),
        "missing_helpers": missing_helpers,
        "changed_helpers": changed_helpers,
        "status": "BLOCKED" if missing or changed or missing_helpers or changed_helpers else "UNVERIFIED",
        "limitations": "AST changes require review and do not necessarily imply regression. Matching definitions do not prove behavior, test execution, unchanged dependencies, hardware performance, or quality.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="byte-exact historical sandbox source")
    parser.add_argument("candidate", help="candidate sandbox source")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        baseline = Path(args.baseline).read_bytes()
        if hashlib.sha256(baseline).hexdigest() != BASELINE_SHA256:
            raise ValueError("historical source SHA-256 mismatch")
        result = compare(baseline, Path(args.candidate).read_bytes())
    except (OSError, ValueError, SyntaxError) as exc:
        parser.exit(2, f"invalid input: {exc}\n")
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
