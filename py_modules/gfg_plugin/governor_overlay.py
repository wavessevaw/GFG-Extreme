"""Governor runtime overlay: a temporary renderer config that never edits Saved.

Architecture::

    Saved Profile (user intent, never written by Governor)
          |
          v
    overlay TOML  = Saved config file + Governor deltas for ONE profile
          |
          v   MAKO_CONFIG (chosen by the launch wrapper while the lease is alive)
    Renderer

Renderer v4 reloads compatible profile changes live (``WatchedConfig``), but the
bundled binary also states that the Scaling Engine and Frame Generation
*provisioning* toggles are process-static ("restart the game to rebuild the
process Vulkan layer chain").  Therefore the overlay only ever changes live
fields, and the scaling-engine toggle is decided at launch by the base overlay.

Every overlay starts with a header the wrapper copies into the launch manifest::

    # gfg-governor-launch: scaling=<0|1> rev=<N> owner=<pid>
    # gfg-governor-point: <key|base>

``owner`` is a lease: the wrapper only selects the overlay while ``/proc/<owner>``
exists, so a crashed plugin cannot leave new launches bound to a stale point.
"""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

OVERLAY_DIRNAME = "governor-overlay"
LAUNCH_HEADER = "# gfg-governor-launch: "
POINT_HEADER = "# gfg-governor-point: "
_LAUNCH_RE = re.compile(
    r"^scaling=(?P<scaling>[01]) rev=(?P<rev>\d+) owner=(?P<owner>\d+)$"
)

# Fields the Governor is allowed to change inside an overlay.  Anything else is
# Saved intent and must stay byte-for-byte equal to the Saved projection.
LIVE_FIELDS = frozenset({
    "adaptive",
    "multiplier",
    "target_fps",
    "base_fps_cap",
    "frame_generation_enabled",
    "scaling_factor",
    "scaling_method",
})
# Launch-time only (process-static): may appear only in the base overlay.
LAUNCH_FIELDS = frozenset({"scaling_enabled"})


class PointNotApplicable(Exception):
    """The operating point cannot be expressed with the current capabilities."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def overlay_key(profile: str) -> str:
    return hashlib.sha256(profile.encode("utf-8")).hexdigest()[:16]


def overlay_path(config_dir: Path, profile: str) -> Path:
    return Path(config_dir) / OVERLAY_DIRNAME / f"overlay-{overlay_key(profile)}.toml"


def parse_launch_line(value: str) -> Optional[Dict[str, int]]:
    """Parse the ``gfg_governor_launch`` value recorded in a launch manifest."""
    match = _LAUNCH_RE.match(str(value or "").strip())
    if not match:
        return None
    return {
        "scaling": int(match.group("scaling")),
        "rev": int(match.group("rev")),
        "owner": int(match.group("owner")),
    }


def base_deltas(saved: Dict[str, Any], *, scale_ready: bool) -> Dict[str, Any]:
    """Launch-time deltas.  Empty unless the user opted into scale-ready launches.

    ``scale_ready`` provisions the (process-static) Scaling Engine at 1.0x in
    Native Resolution mode so that live scale points are possible without a
    relaunch.  It is refused when Gamescope WSI compatibility is on, because
    that mode builds a different Vulkan layer chain from the Saved profile.
    """
    if not scale_ready or saved.get("scaling_enabled"):
        return {}
    if saved.get("gamescope_wsi_compatibility"):
        raise PointNotApplicable("scale-ready-incompatible-with-wsi-chain")
    return {
        "scaling_enabled": True,
        "scaling_method": "native",
        "scaling_factor": 1.0,
    }


def point_deltas(
    point: Dict[str, Any],
    saved: Dict[str, Any],
    *,
    scale_capable: bool,
    scale_ready: bool,
) -> Dict[str, Any]:
    """Map an Operating Point to live overlay fields (never Saved)."""
    multiplier = int(point["multiplier"])
    if multiplier not in (1, 2, 3):
        raise PointNotApplicable("multiplier-not-allowed-automatically")
    deltas: Dict[str, Any] = {
        "adaptive": False,
        "multiplier": multiplier if multiplier > 1 else int(saved.get("multiplier", 2) or 2),
        "target_fps": int(point["target_output_fps"]),
        "base_fps_cap": int(point["base_target_fps"]),
        "frame_generation_enabled": multiplier > 1,
    }
    scale_pct = int(point.get("render_scale_pct", 100))
    if scale_pct != 100:
        if not scale_capable:
            raise PointNotApplicable("scaling-engine-not-provisioned-at-launch")
        if scale_pct not in (90, 80):
            raise PointNotApplicable("scale-not-allowed-automatically")
        if saved.get("scaling_enabled"):
            reference = float(saved.get("scaling_factor", 1.0) or 1.0)
            method = str(saved.get("scaling_method") or "ls1")
        elif scale_ready:
            reference = 1.0
            method = str(saved.get("scaling_method") or "ls1")
            if method == "native":
                method = "ls1"
        else:
            raise PointNotApplicable("scaling-engine-not-provisioned-at-launch")
        factor = round(reference * (100.0 / scale_pct), 3)
        if factor > 2.0:
            raise PointNotApplicable("scaling-factor-limit")
        deltas["scaling_factor"] = factor
        deltas["scaling_method"] = method
    elif saved.get("scaling_enabled") or scale_ready:
        # Back to the user's own (or the provisioned 1.0x) scaling.
        deltas["scaling_factor"] = float(saved.get("scaling_factor", 1.0) or 1.0) if saved.get("scaling_enabled") else 1.0
        if not saved.get("scaling_enabled"):
            deltas["scaling_method"] = "native"
    return deltas


@dataclass
class OverlayRecord:
    profile: str
    revision: int
    point_key: str
    deltas: Dict[str, Any]
    sha256: str
    path: str
    scaling_provisioned: bool = False
    owner: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "revision": self.revision,
            "point_key": self.point_key,
            "deltas": dict(self.deltas),
            "sha256": self.sha256,
            "path": self.path,
            "scaling_provisioned": self.scaling_provisioned,
            "owner": self.owner,
        }


class OverlayStore:
    """Atomic, verified overlay writer.

    ``build_text(profile, deltas)`` must return the full TOML body for the
    Saved config with ``deltas`` applied to ``profile`` only.
    """

    def __init__(
        self,
        config_dir: Path,
        build_text: Callable[[str, Dict[str, Any]], str],
        *,
        owner_pid: Optional[int] = None,
        replace: Callable[[str, str], None] = os.replace,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.build_text = build_text
        self.owner_pid = int(owner_pid if owner_pid is not None else os.getpid())
        self._replace = replace
        self._revisions: Dict[str, int] = {}

    def path_for(self, profile: str) -> Path:
        return overlay_path(self.config_dir, profile)

    def _next_revision(self, profile: str) -> int:
        current = self._revisions.get(profile)
        if current is None:
            header = self.read_header(profile)
            current = int(header["rev"]) if header else 0
        current += 1
        self._revisions[profile] = current
        return current

    def read_header(self, profile: str) -> Optional[Dict[str, int]]:
        try:
            with self.path_for(profile).open("r", encoding="utf-8") as handle:
                for _ in range(4):
                    line = handle.readline()
                    if line.startswith(LAUNCH_HEADER):
                        return parse_launch_line(line[len(LAUNCH_HEADER):])
        except (OSError, UnicodeError):
            return None
        return None

    def exists(self, profile: str) -> bool:
        return self.path_for(profile).is_file()

    def write(
        self,
        profile: str,
        deltas: Dict[str, Any],
        *,
        point_key: str = "base",
        released: bool = False,
    ) -> OverlayRecord:
        """Write and read back an overlay.  Raises ``OSError`` on any failure.

        ``released`` writes owner=0: the wrapper then ignores the overlay for
        new launches while a still-running game keeps a valid Saved snapshot.
        """
        body = self.build_text(profile, dict(deltas))
        revision = self._next_revision(profile)
        owner = 0 if released else self.owner_pid
        scaling = 1 if _body_scaling_enabled(body, profile) else 0
        header = (
            f"{LAUNCH_HEADER}scaling={scaling} rev={revision} owner={owner}\n"
            f"{POINT_HEADER}{point_key}\n"
        )
        text = header + body
        path = self.path_for(profile)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o644)
            self._replace(temp_name, str(path))
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
        readback = path.read_text(encoding="utf-8")
        if readback != text:
            raise OSError("overlay read-back verification failed")
        return OverlayRecord(
            profile=profile,
            revision=revision,
            point_key=point_key,
            deltas=dict(deltas),
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            path=str(path),
            scaling_provisioned=bool(scaling),
            owner=owner,
        )

    def remove(self, profile: str) -> None:
        try:
            self.path_for(profile).unlink()
        except FileNotFoundError:
            pass

    def profiles_on_disk(self) -> list[str]:
        """Overlay keys present on disk (profile names are not recoverable)."""
        directory = self.config_dir / OVERLAY_DIRNAME
        try:
            return sorted(p.name for p in directory.glob("overlay-*.toml"))
        except OSError:
            return []


def _body_scaling_enabled(body: str, profile: str) -> bool:
    """Whether the generated TOML provisions the Scaling Engine for ``profile``."""
    try:
        data = tomllib.loads(body)
    except tomllib.TOMLDecodeError:
        return False
    for entry in data.get("profile", []) or []:
        if isinstance(entry, dict) and entry.get("name") == profile:
            return bool(entry.get("scaling_enabled", False))
    return False
