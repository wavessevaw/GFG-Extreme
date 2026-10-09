"""Install the bundled CSS Loader theme without network access or root."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from .package_paths import PLUGIN_ROOT

THEME_NAME = "GFG Extreme"


class ThemeInstaller:
    def __init__(self, home: Path, source: Path = PLUGIN_ROOT / "themes" / "css-loader" / THEME_NAME):
        self.home = Path(home)
        self.source = Path(source)
        self.destination = self.home / "homebrew" / "themes" / THEME_NAME

    def _validate(self) -> None:
        # The RPC accepts no paths. Never traverse links while replacing files.
        for path in (self.home / "homebrew", self.destination.parent, self.destination):
            if path.is_symlink():
                raise ValueError("Theme destination contains a symbolic link")
        if not self.source.is_dir() or self.source.is_symlink():
            raise ValueError("Bundled theme is missing")
        manifest = json.loads((self.source / "theme.json").read_text())
        if manifest.get("name") != THEME_NAME:
            raise ValueError("Bundled theme manifest is invalid")
        for root in (self.source, self.destination):
            if root.exists() and (not root.is_dir() or any(p.is_symlink() for p in root.rglob("*"))):
                raise ValueError("Theme contains a symbolic link or is not a directory")

    def status(self) -> Dict[str, Any]:
        try:
            self._validate()
            files = [p for p in self.source.rglob("*") if p.is_file()]
            installed = self.destination.is_dir()
            current = installed and all(
                (self.destination / p.relative_to(self.source)).is_file()
                and (self.destination / p.relative_to(self.source)).read_bytes() == p.read_bytes()
                for p in files)
            return {"success": True, "installed": installed, "current": current,
                    "path": str(self.destination)}
        except (OSError, ValueError) as error:
            return {"success": False, "installed": False, "current": False, "error": str(error)}

    def install(self) -> Dict[str, Any]:
        stage = None
        backup = None
        try:
            self._validate()
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".gfg-theme-", dir=self.destination.parent))
            payload = stage / THEME_NAME
            if self.destination.exists():
                shutil.copytree(self.destination, payload)
            else:
                payload.mkdir()
            # Keep local extras; replace only files belonging to the bundled theme.
            for item in self.source.rglob("*"):
                target = payload / item.relative_to(self.source)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item, target)
                    target.chmod(0o644)
            if self.destination.exists():
                backup = stage / "previous"
                os.replace(self.destination, backup)
            try:
                os.replace(payload, self.destination)
            except OSError:
                if backup is not None:
                    os.replace(backup, self.destination)
                raise
            return {"success": True, "installed": True, "current": True,
                    "path": str(self.destination),
                    "message": "Installed. In CSS Loader, reload themes and enable GFG Extreme."}
        except (OSError, ValueError) as error:
            return {"success": False, "error": str(error)}
        finally:
            if stage is not None:
                shutil.rmtree(stage, ignore_errors=True)
