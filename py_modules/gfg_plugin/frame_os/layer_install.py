"""Stage the bundled gfg-pacer layer (``bin/gfg-frame-os`` in the plugin) where the launcher looks.

The launcher adds the pacer only when this directory holds its manifest
(``wrapper_generation.FRAME_OS_MANIFEST_FILENAME``), so staging is the install step and
removing the directory is the uninstall. Files are replaced atomically: a running game keeps
the library it mapped.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict

from ..managed_files import copy_managed_file_atomically

LIBRARY = "libVkLayer_gfg_pacer.so"
MANIFEST = "VkLayer_gfg_pacer.json"
FILES = (LIBRARY, MANIFEST)          # manifest last: the launcher keys on it


def bundled_dir(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "gfg-frame-os"


def target_dir(local_share_dir: Path) -> Path:
    """Private, outside every directory the loader scans on its own (``implicit_layer.d``'s sibling)."""
    return local_share_dir.parent / "gfg-frame-os"


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def stage(source_dir: Path, target_dir: Path, logger: Any) -> Dict[str, Any]:
    """Copy the layer when it differs. Returns {"installed", "changed", "error"}."""
    missing = [name for name in FILES if not (source_dir / name).is_file()]
    if missing:
        return {"installed": is_staged(target_dir), "changed": False,
                "error": "this build does not include the Frame OS layer"}
    changed = False
    try:
        for name in FILES:
            source, target = source_dir / name, target_dir / name
            if target.is_file() and not target.is_symlink() and _digest(target) == _digest(source):
                continue
            copy_managed_file_atomically(source, target, 0o644, logger)
            changed = True
    except OSError as error:
        return {"installed": is_staged(target_dir), "changed": changed, "error": str(error)}
    return {"installed": True, "changed": changed, "error": None}


def is_staged(target_dir: Path) -> bool:
    return all((target_dir / name).is_file() for name in FILES)


def remove(target_dir: Path) -> None:
    for name in reversed(FILES):                      # manifest first: the launcher stops using it
        try:
            (target_dir / name).unlink()
        except FileNotFoundError:
            pass
    shutil.rmtree(target_dir, ignore_errors=True)
