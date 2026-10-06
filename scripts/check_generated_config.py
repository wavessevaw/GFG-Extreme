#!/usr/bin/env python3
"""Verify py_modules/gfg_plugin/config_schema_generated.py matches shared_config.py.

The generated file is derived from ``CONFIG_SCHEMA_DEF``.  The original generator
did not ship with this tree, so this check compares the generated artefact with
its source of truth instead of regenerating it: field-name constants,
``ConfigurationData`` and ``ConfigurationPatch`` must list exactly the schema
fields with matching Python types.  Exit status 1 on any drift.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
TYPE_MAP = {"boolean": bool, "integer": int, "float": float, "string": str}


def check(schema: Dict[str, Dict[str, Any]], generated: types.ModuleType) -> List[str]:
    problems: List[str] = []
    names = set(schema)
    constants = {
        value for key, value in vars(generated).items()
        if key.isupper() and isinstance(value, str) and value in names | {
            v for v in vars(generated).values() if isinstance(v, str)
        } and not key.startswith("_")
    }
    for name in sorted(names):
        if name not in constants:
            problems.append(f"missing name constant for schema field '{name}'")
    for class_name in ("ConfigurationData", "ConfigurationPatch"):
        annotations = getattr(generated, class_name).__annotations__
        for name in sorted(names - set(annotations)):
            problems.append(f"{class_name} lacks field '{name}'")
        for name in sorted(set(annotations) - names):
            problems.append(f"{class_name} has unknown field '{name}'")
        for name, definition in schema.items():
            expected = TYPE_MAP[definition["fieldType"].value]
            if name in annotations and annotations[name] is not expected:
                problems.append(f"{class_name}.{name} is {annotations[name]!r}, expected {expected.__name__}")
    return problems


def main() -> int:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "py_modules"))
    import shared_config  # noqa: E402
    from gfg_plugin import config_schema_generated  # noqa: E402

    problems = check(shared_config.CONFIG_SCHEMA_DEF, config_schema_generated)
    for problem in problems:
        print(f"generated-config drift: {problem}", file=sys.stderr)
    if not problems:
        print(f"generated config OK ({len(shared_config.CONFIG_SCHEMA_DEF)} fields)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
