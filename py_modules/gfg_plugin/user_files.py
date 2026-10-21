"""Files in the user's home, written by a plugin that runs as root.

Everything GFG Extreme writes under the home directory is handed to the home's owner, so the
user (and a later plugin version) can always rewrite it.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple


def home_owner(home: Path) -> Optional[Tuple[int, int]]:
    try:
        st = Path(home).stat()
    except OSError:
        return None
    return st.st_uid, st.st_gid


def own(path: Path, owner: Optional[Tuple[int, int]]) -> None:
    if owner is None or os.geteuid() != 0:
        return
    try:
        os.chown(path, owner[0], owner[1])
    except OSError:
        pass


def ensure_dir(path: Path, owner: Optional[Tuple[int, int]], stop: Optional[Path] = None) -> None:
    """mkdir -p, owning every directory created below ``stop`` (the home)."""
    path = Path(path)
    missing = []
    probe = path
    while not probe.exists() and probe != probe.parent and probe != stop:
        missing.append(probe)
        probe = probe.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in missing:
        own(created, owner)


def write_text_atomic(path: Path, text: str, owner: Optional[Tuple[int, int]] = None, mode: int = 0o644) -> None:
    path = Path(path)
    ensure_dir(path.parent, owner)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        own(Path(tmp), owner)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path: Path, data: Any, owner: Optional[Tuple[int, int]] = None) -> None:
    write_text_atomic(path, json.dumps(data, indent=1, sort_keys=True) + "\n", owner)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return default
