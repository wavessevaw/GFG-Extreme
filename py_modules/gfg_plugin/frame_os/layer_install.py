"""Stage the bundled gfg-pacer layer (``bin/gfg-frame-os`` in the plugin) where the launcher looks.

The launcher adds the pacer only when this directory holds its manifest
(``wrapper_generation.FRAME_OS_MANIFEST_FILENAME``), so staging is the install step and
removing the directory is the uninstall. Files are replaced atomically: a running game keeps
the library it mapped.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from ..managed_files import copy_managed_file_atomically, write_managed_text_atomically

LIBRARY = "libVkLayer_gfg_pacer.so"
MANIFEST = "VkLayer_gfg_pacer.json"
FILES = (LIBRARY, MANIFEST)          # manifest last: the launcher keys on it
# Copy registered in the user's standard implicit-layer directory: Steam's container (Pressure
# Vessel) imports layers from the standard search paths, not from a wrapper-only path. Gated by
# GFG_FRAME_OS, which nothing sets (the launcher names the layer explicitly instead), so it never
# activates on its own.
REGISTERED_MANIFEST = "VkLayer_GFG_Extreme_frame_os.json"
GATE_ENV = "GFG_FRAME_OS"
DISABLE_ENV = "DISABLE_GFG_FRAME_OS"
# The ring HUD layer ships beside the pacer (bin/gfg-frame-os) and is staged the same way.
HUD_LIBRARY = "libVkLayer_gfg_hud.so"
HUD_MANIFEST = "VkLayer_gfg_hud.json"
HUD_FILES = (HUD_LIBRARY, HUD_MANIFEST)
HUD_REGISTERED_MANIFEST = "VkLayer_GFG_Extreme_hud.json"
LAYERS = {
    "pacer": (FILES, REGISTERED_MANIFEST, GATE_ENV, DISABLE_ENV),
    "hud": (HUD_FILES, HUD_REGISTERED_MANIFEST, "GFG_HUD", "DISABLE_GFG_HUD"),
}


def bundled_dir(plugin_root: Path) -> Path:
    return plugin_root / "bin" / "gfg-frame-os"


def target_dir(local_share_dir: Path) -> Path:
    """Private, outside every directory the loader scans on its own (``implicit_layer.d``'s sibling)."""
    return local_share_dir.parent / "gfg-frame-os"


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def registered_manifest_text(target_dir: Path, source_manifest: Path, layer_key: str = "pacer") -> str:
    files, _registered, gate, disable = LAYERS[layer_key]
    data = json.loads(source_manifest.read_text(encoding="utf-8"))
    layer = data["layer"]
    layer["library_path"] = str(target_dir / files[0])
    layer["library_arch"] = "64"
    layer["enable_environment"] = {gate: "1"}
    layer["disable_environment"] = {disable: "1"}
    return json.dumps(data, indent=2) + "\n"


def stage(source_dir: Path, target_dir: Path, logger: Any,
          registry_dir: Optional[Path] = None, layer_key: str = "pacer") -> Dict[str, Any]:
    """Copy the layer when it differs. Returns {"installed", "changed", "error"}."""
    files, registered, _gate, _disable = LAYERS[layer_key]
    missing = [name for name in files if not (source_dir / name).is_file()]
    if missing:
        return {"installed": is_staged(target_dir, layer_key), "changed": False,
                "error": "this build does not include the " + ("ring HUD" if layer_key == "hud" else "Frame OS")
                         + " layer"}
    changed = False
    try:
        for name in files:
            source, target = source_dir / name, target_dir / name
            if target.is_file() and not target.is_symlink() and _digest(target) == _digest(source):
                continue
            copy_managed_file_atomically(source, target, 0o644, logger)
            changed = True
        if registry_dir is not None:
            text = registered_manifest_text(target_dir, source_dir / files[1], layer_key)
            changed = write_managed_text_atomically(registry_dir / registered, text, 0o644, logger) or changed
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"installed": is_staged(target_dir, layer_key), "changed": changed, "error": str(error)}
    return {"installed": True, "changed": changed, "error": None}


def is_staged(target_dir: Path, layer_key: str = "pacer") -> bool:
    return all((target_dir / name).is_file() for name in LAYERS[layer_key][0])


def remove(target_dir: Path, registry_dir: Optional[Path] = None) -> None:
    if registry_dir is not None:
        for _files, registered, _gate, _disable in LAYERS.values():
            try:
                (registry_dir / registered).unlink()
            except FileNotFoundError:
                pass
    for name in (MANIFEST, HUD_MANIFEST, LIBRARY, HUD_LIBRARY):   # manifests first: the launcher stops
        try:
            (target_dir / name).unlink()
        except FileNotFoundError:
            pass
    shutil.rmtree(target_dir, ignore_errors=True)
