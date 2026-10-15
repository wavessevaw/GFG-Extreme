"""Install, update and remove GFG Shell from the GFG Extreme plugin.

The plugin zip carries the shell itself (``bin/gfg-shell/``: the exported .pck, the launcher
and helper scripts, Godot's licence texts and ``godot.json`` naming the pinned official
Godot runtime). The runtime (~60 MB) is downloaded once from the Godot release on GitHub and
must match the pinned SHA-256 before anything is installed.

Everything goes to ``~/.local/share/gfg-shell/app`` owned by the Deck user; nothing outside
the user's home is touched. The Steam shortcut is created by the frontend (Steam's own
``SteamClient.Apps.AddShortcut``); its app id is remembered here so a later launch reuses it.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .package_paths import PLUGIN_ROOT

PACKAGED = PLUGIN_ROOT / "bin" / "gfg-shell"
APP_FILES = ("gfg-shell.pck", "gfg-shell.sh", "uninstall.sh", "collect-diagnostics.sh", "VERSION")
EXECUTABLES = ("gfg-shell.sh", "uninstall.sh", "collect-diagnostics.sh")
DOWNLOAD_TIMEOUT_S = 30
MAX_RUNTIME_ZIP = 200 * 1024 * 1024


# Decky's bundled Python does not know where SteamOS keeps its CA certificates, so the
# default context fails with CERTIFICATE_VERIFY_FAILED. Point it at the system bundle;
# verification stays on (and the download is SHA-256 checked as well).
CA_BUNDLES = ("/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt",
              "/etc/ssl/cert.pem", "/etc/ca-certificates/extracted/tls-ca-bundle.pem")


def ssl_context(bundles=CA_BUNDLES) -> ssl.SSLContext:
    for path in bundles:
        if os.path.isfile(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


class _CurlResponse:
    """Minimal urlopen-like response over a file downloaded by the system curl."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fh = open(path, "rb")
        self.headers = {"Content-Length": str(path.stat().st_size)}

    def read(self, n: int = -1) -> bytes:
        return self._fh.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self._fh.close()
        try:
            self._path.unlink()
        except OSError:
            pass


def system_urlopen(url: str, timeout: float):
    """urlopen with the system CA bundle; falls back to the system curl on TLS trouble."""
    try:
        return urllib.request.urlopen(url, timeout=timeout, context=ssl_context())
    except Exception as error:  # ssl.SSLError arrives wrapped in URLError
        if "CERTIFICATE" not in str(error).upper() and "SSL" not in str(error).upper():
            raise
        curl = shutil.which("curl", path="/usr/bin:/bin")
        if not curl:
            raise
        fd, name = tempfile.mkstemp(prefix=".godot-", suffix=".zip")
        os.close(fd)
        env = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "SSL_CERT_FILE")}
        result = subprocess.run([curl, "-fsSL", "--proto", "=https", "--max-time", "600", "-o", name, url],
                                env=env, capture_output=True, text=True)
        if result.returncode != 0:
            os.unlink(name)
            raise OSError("curl failed: " + (result.stderr.strip() or str(result.returncode)))
        return _CurlResponse(Path(name))


def _read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


class ShellInstaller:
    def __init__(self, home: Path, packaged: Path = PACKAGED,
                 opener: Callable[..., Any] = system_urlopen,
                 uid: Optional[int] = None, gid: Optional[int] = None) -> None:
        self.home = Path(home)
        self.packaged = Path(packaged)
        self.opener = opener
        self.base = self.home / ".local" / "share" / "gfg-shell"
        self.app = self.base / "app"
        self.state_file = self.base / "plugin.json"
        if uid is None:
            try:
                info = self.home.stat()
                uid, gid = info.st_uid, info.st_gid
            except OSError:
                pass
        self.uid, self.gid = uid, gid
        self._lock = threading.Lock()
        self.progress: Dict[str, Any] = {"busy": False, "step": "", "done": 0, "total": 0}

    # ------------------------------------------------------------------ status
    def runtime_spec(self) -> Dict[str, Any]:
        spec = json.loads((self.packaged / "godot.json").read_text())
        for key in ("version", "url", "sha256", "bin"):
            if not isinstance(spec.get(key), str) or not spec[key]:
                raise ValueError("godot.json lacks " + key)
        if not spec["url"].startswith("https://github.com/godotengine/godot/releases/download/"):
            raise ValueError("Godot runtime must come from the official Godot releases")
        return spec

    def _state(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.state_file.read_text())
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def status(self) -> Dict[str, Any]:
        packaged_version = _read(self.packaged / "VERSION")
        installed_version = _read(self.app / "VERSION")
        runtime = _read(self.app / "bin" / "godot.version")
        try:
            spec_version = self.runtime_spec()["version"] if packaged_version else ""
        except (OSError, ValueError):
            spec_version = ""
        installed = bool(installed_version) and (self.app / "gfg-shell.sh").is_file() and (self.app / "bin" / "godot").is_file()
        shortcut = self._state().get("shortcut_appid")
        return {
            "success": True,
            "packaged": bool(packaged_version),
            "packaged_version": packaged_version,
            "installed": installed,
            "installed_version": installed_version,
            "runtime_version": runtime,
            "update_available": installed and bool(packaged_version) and (
                installed_version != packaged_version or runtime != spec_version),
            "path": str(self.app / "gfg-shell.sh"),
            "start_dir": str(self.app),
            "shortcut_appid": shortcut if isinstance(shortcut, int) else None,
            "progress": dict(self.progress),
        }

    # ----------------------------------------------------------------- helpers
    def _own(self, path: Path) -> None:
        if self.uid is None:
            return
        try:
            os.chown(path, self.uid, self.gid if self.gid is not None else -1, follow_symlinks=False)
        except OSError:
            pass

    def _own_tree(self, root: Path) -> None:
        self._own(root)
        for p in root.rglob("*"):
            self._own(p)

    def _check_destination(self) -> None:
        for path in (self.home / ".local", self.home / ".local" / "share", self.base, self.app):
            if path.is_symlink():
                raise ValueError("Install path contains a symbolic link: " + str(path))

    def _download_runtime(self, spec: Dict[str, Any], stage: Path) -> Path:
        """Download the pinned Godot zip into stage and return the extracted binary."""
        self.progress.update(step="download", done=0, total=0)
        zpath = stage / "godot.zip"
        digest = hashlib.sha256()
        with self.opener(spec["url"], timeout=DOWNLOAD_TIMEOUT_S) as response, open(zpath, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0) if getattr(response, "headers", None) else 0
            self.progress["total"] = total
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                self.progress["done"] += len(chunk)
                if self.progress["done"] > MAX_RUNTIME_ZIP:
                    raise ValueError("Godot download is larger than expected")
        if digest.hexdigest() != spec["sha256"].lower():
            raise ValueError("Godot download failed its SHA-256 check")
        self.progress.update(step="extract")
        with zipfile.ZipFile(zpath) as zf:
            if spec["bin"] not in zf.namelist():
                raise ValueError("Godot archive does not contain " + spec["bin"])
            target = stage / "godot"
            with zf.open(spec["bin"]) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
        zpath.unlink()
        target.chmod(0o755)
        return target

    # ----------------------------------------------------------------- actions
    def install(self) -> Dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            return {"success": False, "error": "An installation is already running"}
        stage: Optional[Path] = None
        try:
            self.progress.update(busy=True, step="check", done=0, total=0)
            if not _read(self.packaged / "VERSION"):
                return {"success": False, "error": "This GFG Extreme build does not include GFG Shell"}
            spec = self.runtime_spec()
            self._check_destination()
            self.base.mkdir(parents=True, exist_ok=True)
            self._own(self.base)
            stage = Path(tempfile.mkdtemp(prefix=".install-", dir=self.base))
            payload = stage / "app"
            (payload / "bin").mkdir(parents=True)
            for name in APP_FILES:
                shutil.copyfile(self.packaged / name, payload / name)
            shutil.copytree(self.packaged / "licenses", payload / "licenses")
            for name in EXECUTABLES:
                (payload / name).chmod(0o755)
            # Reuse the runtime already installed when it is the pinned version.
            current_runtime = self.app / "bin" / "godot"
            if _read(self.app / "bin" / "godot.version") == spec["version"] and current_runtime.is_file():
                shutil.copy2(current_runtime, payload / "bin" / "godot")
            else:
                os.replace(self._download_runtime(spec, stage), payload / "bin" / "godot")
            (payload / "bin" / "godot.version").write_text(spec["version"] + "\n")
            self.progress.update(step="activate")
            self._own_tree(payload)
            previous = stage / "previous"
            if self.app.exists():
                os.replace(self.app, previous)
            try:
                os.replace(payload, self.app)
            except OSError:
                if previous.exists():
                    os.replace(previous, self.app)
                raise
            return {"success": True, "version": _read(self.app / "VERSION"), "path": str(self.app / "gfg-shell.sh")}
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            return {"success": False, "error": str(error)}
        except Exception as error:  # network errors (URLError, timeouts) and the like
            return {"success": False, "error": "Download failed: %s" % error}
        finally:
            if stage is not None:
                shutil.rmtree(stage, ignore_errors=True)
            self.progress.update(busy=False, step="")
            self._lock.release()

    def uninstall(self) -> Dict[str, Any]:
        """Removes program files. Logs and the shell's own settings stay unless asked."""
        if not self._lock.acquire(blocking=False):
            return {"success": False, "error": "An installation is running"}
        try:
            self._check_destination()
            if self.app.exists():
                shutil.rmtree(self.app)
            state = self._state()
            state.pop("shortcut_appid", None)
            self._write_state(state)
            return {"success": True}
        except (OSError, ValueError) as error:
            return {"success": False, "error": str(error)}
        finally:
            self._lock.release()

    def set_shortcut(self, appid: Any) -> Dict[str, Any]:
        if appid is not None and (type(appid) is not int or appid <= 0 or appid > 0xFFFFFFFF):
            return {"success": False, "error": "A Steam shortcut app id is required"}
        state = self._state()
        if appid is None:
            state.pop("shortcut_appid", None)
        else:
            state["shortcut_appid"] = appid
        try:
            self._write_state(state)
        except OSError as error:
            return {"success": False, "error": str(error)}
        return {"success": True}

    def _write_state(self, state: Dict[str, Any]) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        self._own(self.base)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        self._own(tmp)
        os.replace(tmp, self.state_file)
