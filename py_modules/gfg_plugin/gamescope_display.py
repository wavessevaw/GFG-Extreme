"""Synchronize MAKO Adaptive Target FPS with Gamescope display refresh.

This uses Gamescope's private ``gamescope_control`` Wayland protocol, version 2,
with the ``only_change_refresh_rate`` flag. The request therefore changes the
display cadence without installing Gamescope's own FPS cap on top of MAKO.

Gamescope intentionally chooses the highest display refresh that is an integer
multiple of the requested cycle. MAKO's UI feature promises Target FPS == Hz,
so the request is issued only when Gamescope's published mode list proves that
this policy will resolve to the exact requested refresh rate.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import re
import select
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_service import BaseService


class _WlArray(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("alloc", ctypes.c_size_t),
        ("data", ctypes.c_void_p),
    ]


class _WlMessage(ctypes.Structure):
    pass


class _WlInterface(ctypes.Structure):
    pass


_WlMessage._fields_ = [
    ("name", ctypes.c_char_p),
    ("signature", ctypes.c_char_p),
    ("types", ctypes.POINTER(ctypes.POINTER(_WlInterface))),
]
_WlInterface._fields_ = [
    ("name", ctypes.c_char_p),
    ("version", ctypes.c_int),
    ("method_count", ctypes.c_int),
    ("methods", ctypes.POINTER(_WlMessage)),
    ("event_count", ctypes.c_int),
    ("events", ctypes.POINTER(_WlMessage)),
]


_REGISTRY_GLOBAL = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_char_p,
    ctypes.c_uint32,
)
_REGISTRY_GLOBAL_REMOVE = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32
)
_CONTROL_FEATURE_SUPPORT = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_uint32,
)
_CALLBACK_DONE = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32
)
_CONTROL_ACTIVE_DISPLAY_INFO = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.POINTER(_WlArray),
)


class GamescopeDisplayService(BaseService):
    """Best-effort exact Target FPS -> refresh synchronization in Game Mode."""

    _CONTROL_INTERFACE_NAME = b"gamescope_control"
    _CONTROL_VERSION = 2
    _DISPLAY_FLAG_INTERNAL = 0x1
    _TARGET_FLAG_INTERNAL_DISPLAY = 0x1
    _TARGET_FLAG_ALLOW_REFRESH_SWITCHING = 0x2
    _TARGET_FLAG_ONLY_CHANGE_REFRESH_RATE = 0x4
    _WL_DISPLAY_SYNC = 0
    _WL_DISPLAY_GET_REGISTRY = 1
    _WL_REGISTRY_BIND = 0
    _ROUNDTRIP_TIMEOUT_SECONDS = 2.0

    def __init__(self, logger: Optional[Any] = None):
        super().__init__(logger)
        self._wayland = self._load_wayland()
        self._registry_interface = None
        self._callback_interface = None
        self._cached_x_display: Optional[str] = None
        if self._wayland is not None:
            try:
                self._registry_interface = _WlInterface.in_dll(
                    self._wayland, "wl_registry_interface"
                )
                self._callback_interface = _WlInterface.in_dll(
                    self._wayland, "wl_callback_interface"
                )
            except (ValueError, OSError) as error:
                self.log.debug("Wayland registry interface unavailable: %s", error)
                self._wayland = None


    _X_DISPLAY = re.compile(r"^:[0-9]+(?:\.[0-9]+)?$")
    _X_CARDINAL = re.compile(
        r"^(GAMESCOPE_PID|GAMESCOPE_XWAYLAND_SERVER_ID|"
        r"GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK)\(CARDINAL\) = ([0-9]+)$",
        re.MULTILINE,
    )

    @classmethod
    def _xroot_properties(cls, display_name: str) -> Optional[Dict[str, int]]:
        try:
            result = subprocess.run(
                (
                    "xprop", "-display", display_name, "-root",
                    "GAMESCOPE_PID",
                    "GAMESCOPE_XWAYLAND_SERVER_ID",
                    "GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK",
                ),
                capture_output=True, text=True, timeout=0.8, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode:
            return None
        return {name: int(value) for name, value in cls._X_CARDINAL.findall(result.stdout)}

    def _xwayland_candidates(self, current_display: str) -> List[str]:
        """Return only X displays that actually have a local X11 socket.

        Decky commonly runs without DISPLAY. Scanning :0..:15 spawned up to 16
        failing xprop processes per refresh read, so prefer the live socket set
        and remember the last Gamescope server-zero display.
        """
        candidates: List[str] = []
        for value in (current_display, self._cached_x_display or ""):
            if self._X_DISPLAY.fullmatch(value) and value not in candidates:
                candidates.append(value)

        socket_dir = Path("/tmp/.X11-unix")
        try:
            numbers = sorted(
                int(path.name[1:])
                for path in socket_dir.iterdir()
                if (path.name.startswith("X") and path.name[1:].isascii()
                    and path.name[1:].isdigit())
            )
        except OSError:
            numbers = []
        for number in numbers:
            display_name = f":{number}"
            if display_name not in candidates:
                candidates.append(display_name)

        # Some Xwayland setups use an abstract socket only. Keep one bounded
        # fallback instead of the old blind 16-display sweep.
        if not candidates:
            candidates.append(":0")
        return candidates

    def read_current_refresh_hz(self) -> Optional[int]:
        """Read Gamescope's actual output refresh from server-zero Xwayland."""
        current_display = os.environ.get("DISPLAY", "")
        current_props = (
            self._xroot_properties(current_display)
            if self._X_DISPLAY.fullmatch(current_display) else None
        )
        session_pid = current_props.get("GAMESCOPE_PID") if current_props else None

        # A previously verified server-zero Xwayland display is the cheapest
        # and most likely answer when Decky has no DISPLAY.  Revalidate that
        # socket once and return immediately instead of spawning xprop for every
        # live X socket on each poll.  If DISPLAY identified a Gamescope PID,
        # retain the PID check so a cache from another session cannot leak in.
        cached_display = self._cached_x_display
        if cached_display and cached_display != current_display:
            cached_props = self._xroot_properties(cached_display)
            if cached_props and cached_props.get("GAMESCOPE_XWAYLAND_SERVER_ID") == 0:
                cached_pid = cached_props.get("GAMESCOPE_PID")
                cached_refresh = cached_props.get(
                    "GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK"
                )
                if (not session_pid or cached_pid == session_pid) and (
                        isinstance(cached_refresh, int) and cached_refresh > 0):
                    return cached_refresh
            else:
                self._cached_x_display = None

        matches: List[int] = []
        for display_name in self._xwayland_candidates(current_display):
            props = (
                current_props
                if display_name == current_display and current_props is not None
                else self._xroot_properties(display_name)
            )
            if not props:
                if display_name == self._cached_x_display:
                    self._cached_x_display = None
                continue
            if props.get("GAMESCOPE_XWAYLAND_SERVER_ID") != 0:
                continue
            if session_pid and props.get("GAMESCOPE_PID") != session_pid:
                continue
            refresh = props.get("GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK")
            if isinstance(refresh, int) and refresh > 0:
                self._cached_x_display = display_name
                matches.append(refresh)
                if session_pid:
                    return refresh
        return matches[0] if len(matches) == 1 else None

    def wait_for_refresh_hz(self, target_hz: int, attempts: int = 16) -> Optional[int]:
        """Wait for Gamescope's deferred modeset and return verified refresh.

        Gamescope deliberately delays dynamic refresh changes to avoid mode
        flicker. Keep the readback window comfortably beyond that debounce
        instead of declaring failure just before the compositor applies it.
        """
        last: Optional[int] = None
        for attempt in range(max(1, attempts)):
            last = self.read_current_refresh_hz()
            if last == int(target_hz):
                return last
            if attempt + 1 < attempts:
                time.sleep(0.10)
        return last

    @staticmethod
    def _load_wayland():
        name = ctypes.util.find_library("wayland-client") or "libwayland-client.so.0"
        try:
            library = ctypes.CDLL(name, use_errno=True)
        except OSError:
            return None

        library.wl_display_connect.argtypes = [ctypes.c_char_p]
        library.wl_display_connect.restype = ctypes.c_void_p
        library.wl_display_connect_to_fd.argtypes = [ctypes.c_int]
        library.wl_display_connect_to_fd.restype = ctypes.c_void_p
        library.wl_display_disconnect.argtypes = [ctypes.c_void_p]
        library.wl_display_disconnect.restype = None
        library.wl_display_roundtrip.argtypes = [ctypes.c_void_p]
        library.wl_display_roundtrip.restype = ctypes.c_int
        library.wl_display_get_fd.argtypes = [ctypes.c_void_p]
        library.wl_display_get_fd.restype = ctypes.c_int
        library.wl_display_prepare_read.argtypes = [ctypes.c_void_p]
        library.wl_display_prepare_read.restype = ctypes.c_int
        library.wl_display_cancel_read.argtypes = [ctypes.c_void_p]
        library.wl_display_cancel_read.restype = None
        library.wl_display_read_events.argtypes = [ctypes.c_void_p]
        library.wl_display_read_events.restype = ctypes.c_int
        library.wl_display_dispatch_pending.argtypes = [ctypes.c_void_p]
        library.wl_display_dispatch_pending.restype = ctypes.c_int
        library.wl_display_flush.argtypes = [ctypes.c_void_p]
        library.wl_display_flush.restype = ctypes.c_int
        library.wl_proxy_get_version.argtypes = [ctypes.c_void_p]
        library.wl_proxy_get_version.restype = ctypes.c_uint32
        library.wl_proxy_add_listener.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
        ]
        library.wl_proxy_add_listener.restype = ctypes.c_int
        library.wl_proxy_destroy.argtypes = [ctypes.c_void_p]
        library.wl_proxy_destroy.restype = None
        # Variadic after the first five fixed arguments.
        library.wl_proxy_marshal_flags.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(_WlInterface),
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        library.wl_proxy_marshal_flags.restype = ctypes.c_void_p
        return library

    def _gamescope_display_name(self) -> Optional[str]:
        configured = os.environ.get("GAMESCOPE_WAYLAND_DISPLAY")
        if configured:
            return configured
        try:
            uid = self.user_home.stat().st_uid
        except OSError:
            return "gamescope-0"
        runtime = Path(f"/run/user/{uid}")
        preferred = runtime / "gamescope-0"
        if preferred.exists():
            return preferred.name
        try:
            candidates = [
                path for path in runtime.glob("gamescope-*")
                if path.is_socket()
            ]
        except OSError:
            candidates = []
        if not candidates:
            return "gamescope-0"
        def safe_mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except OSError:
                return float("-inf")

        candidates.sort(key=safe_mtime, reverse=True)
        return candidates[0].name

    def _connect_gamescope(self):
        """Connect directly to the logged-in user's Gamescope Unix socket."""
        display_name = self._gamescope_display_name()
        try:
            uid = self.user_home.stat().st_uid
        except OSError:
            uid = None

        if uid is not None and display_name:
            display_path = Path(display_name)
            if not display_path.is_absolute():
                display_path = Path(f"/run/user/{uid}") / display_path
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                client.connect(str(display_path))
                fd = client.detach()
                display = self._wayland.wl_display_connect_to_fd(fd)
                if display:
                    return display, str(display_path)
                # wl_display_connect_to_fd() owns fd even on failure.
            except OSError:
                client.close()

        # Last-resort fallback for environments where Decky already inherited
        # the correct Gamescope Wayland variables.
        display = self._wayland.wl_display_connect(
            display_name.encode("utf-8") if display_name else None
        )
        return display, display_name or "default"

    def _roundtrip_with_timeout(
            self, display: ctypes.c_void_p,
            timeout_seconds: float | None = None,
    ) -> None:
        """Perform a Wayland sync roundtrip without an unbounded blocking read."""
        if self._callback_interface is None:
            raise RuntimeError("Wayland callback interface is unavailable")
        timeout = (
            self._ROUNDTRIP_TIMEOUT_SECONDS
            if timeout_seconds is None else max(0.05, float(timeout_seconds))
        )
        done = False

        @_CALLBACK_DONE
        def on_done(_data, _callback, _serial):
            nonlocal done
            done = True

        listener = (ctypes.c_void_p * 1)(
            ctypes.cast(on_done, ctypes.c_void_p).value
        )
        display_version = self._wayland.wl_proxy_get_version(display)
        callback = self._wayland.wl_proxy_marshal_flags(
            display,
            self._WL_DISPLAY_SYNC,
            ctypes.byref(self._callback_interface),
            display_version,
            0,
            None,
        )
        if not callback:
            raise RuntimeError("could not create Wayland sync callback")
        if self._wayland.wl_proxy_add_listener(
                callback,
                ctypes.cast(listener, ctypes.POINTER(ctypes.c_void_p)),
                None,
        ) != 0:
            self._wayland.wl_proxy_destroy(callback)
            raise RuntimeError("could not install Wayland sync listener")

        deadline = time.monotonic() + timeout
        display_fd = self._wayland.wl_display_get_fd(display)
        poller = select.poll()
        try:
            while not done:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Gamescope Wayland roundtrip timed out")
                if self._wayland.wl_display_dispatch_pending(display) < 0:
                    raise RuntimeError("Wayland pending-event dispatch failed")
                if done:
                    break

                # prepare_read fails while events are already queued; dispatch
                # them and retry instead of blocking.
                if self._wayland.wl_display_prepare_read(display) != 0:
                    continue

                flush_result = self._wayland.wl_display_flush(display)
                flush_blocked = False
                if flush_result < 0:
                    error_number = ctypes.get_errno()
                    if error_number != errno.EAGAIN:
                        self._wayland.wl_display_cancel_read(display)
                        raise RuntimeError(
                            f"Wayland flush failed: errno={error_number}"
                        )
                    flush_blocked = True

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._wayland.wl_display_cancel_read(display)
                    raise TimeoutError("Gamescope Wayland roundtrip timed out")

                event_mask = select.POLLIN
                if flush_blocked:
                    event_mask |= select.POLLOUT
                poller.register(display_fd, event_mask)
                try:
                    events = poller.poll(max(1, int(remaining * 1000)))
                finally:
                    poller.unregister(display_fd)

                if not events:
                    self._wayland.wl_display_cancel_read(display)
                    raise TimeoutError("Gamescope Wayland roundtrip timed out")

                mask = events[0][1]
                if mask & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
                    self._wayland.wl_display_cancel_read(display)
                    raise RuntimeError("Gamescope Wayland connection closed")
                if mask & select.POLLIN:
                    if self._wayland.wl_display_read_events(display) < 0:
                        raise RuntimeError("Wayland event read failed")
                else:
                    # Only writability changed; release read ownership and retry
                    # the flush without consuming an event.
                    self._wayland.wl_display_cancel_read(display)
        finally:
            try:
                self._wayland.wl_proxy_destroy(callback)
            except Exception:
                pass
            _ = on_done, listener

    @staticmethod
    def _gamescope_selected_rate(
            target_fps: int, valid_rates: List[int]
    ) -> Optional[int]:
        compatible = [rate for rate in valid_rates if rate % target_fps == 0]
        return max(compatible) if compatible else None

    @staticmethod
    def _control_interface() -> tuple[_WlInterface, Any, Any]:
        # Protocol v2 is sufficient for display_info and set_app_target_refresh_cycle.
        methods = (_WlMessage * 2)(
            _WlMessage(b"destroy", b"", None),
            _WlMessage(b"set_app_target_refresh_cycle", b"2uu", None),
        )
        events = (_WlMessage * 2)(
            _WlMessage(b"feature_support", b"uuu", None),
            _WlMessage(b"active_display_info", b"2sssua", None),
        )
        interface = _WlInterface(
            b"gamescope_control",
            2,
            2,
            methods,
            2,
            events,
        )
        return interface, methods, events

    def sync_target_fps(self, target_fps: int) -> Dict[str, Any]:
        """Request exact refresh matching the settled Adaptive target.

        Passing 0 performs a read-only active-display query.  This keeps the
        Automatic Dock detector on the same Gamescope protocol path as refresh
        synchronization instead of guessing from USB-C or DRM connector state.
        """
        try:
            target_fps = int(target_fps)
        except (TypeError, ValueError):
            return {"success": False, "applied": False, "error": "invalid target FPS"}
        inspect_only = target_fps == 0
        if not inspect_only and not 20 <= target_fps <= 500:
            return {"success": False, "applied": False, "error": "invalid target FPS"}
        if self._wayland is None or self._registry_interface is None:
            return {
                "success": False,
                "applied": False,
                "error": "libwayland-client is unavailable",
            }

        display, display_name = self._connect_gamescope()
        if not display:
            return {
                "success": False,
                "applied": False,
                "error": f"could not connect to Gamescope Wayland display {display_name}",
            }

        registry = None
        control = None
        callback_refs: List[Any] = []
        protocol_refs: List[Any] = []
        state: Dict[str, Any] = {
            "valid_rates": [],
            "display_flags": 0,
            "control_version": 0,
        }

        try:
            display_version = self._wayland.wl_proxy_get_version(display)
            registry = self._wayland.wl_proxy_marshal_flags(
                display,
                self._WL_DISPLAY_GET_REGISTRY,
                ctypes.byref(self._registry_interface),
                display_version,
                0,
                None,
            )
            if not registry:
                raise RuntimeError("could not create Wayland registry proxy")

            control_interface, methods, events = self._control_interface()
            protocol_refs.extend([control_interface, methods, events])

            @_CONTROL_FEATURE_SUPPORT
            def on_feature(_data, _proxy, _feature, _version, _flags):
                return None

            @_CONTROL_ACTIVE_DISPLAY_INFO
            def on_display_info(
                    _data, _proxy, _connector, _make, _model,
                    display_flags, valid_rates_array
            ):
                state["display_flags"] = int(display_flags)
                state["connector"] = (
                    _connector.decode("utf-8", errors="replace")
                    if _connector else ""
                )
                state["make"] = (
                    _make.decode("utf-8", errors="replace") if _make else ""
                )
                state["model"] = (
                    _model.decode("utf-8", errors="replace") if _model else ""
                )
                rates: List[int] = []
                if valid_rates_array:
                    array = valid_rates_array.contents
                    count = array.size // ctypes.sizeof(ctypes.c_uint32)
                    if count and array.data:
                        values = ctypes.cast(
                            array.data,
                            ctypes.POINTER(ctypes.c_uint32 * count),
                        ).contents
                        rates = [int(value) for value in values]
                state["valid_rates"] = sorted(set(rates))

            control_listener = (ctypes.c_void_p * 2)(
                ctypes.cast(on_feature, ctypes.c_void_p).value,
                ctypes.cast(on_display_info, ctypes.c_void_p).value,
            )
            callback_refs.extend([on_feature, on_display_info, control_listener])

            @_REGISTRY_GLOBAL
            def on_global(_data, registry_proxy, name, interface_name, version):
                nonlocal control
                if control or interface_name != self._CONTROL_INTERFACE_NAME:
                    return
                bind_version = min(int(version), self._CONTROL_VERSION)
                state["control_version"] = bind_version
                control = self._wayland.wl_proxy_marshal_flags(
                    registry_proxy,
                    self._WL_REGISTRY_BIND,
                    ctypes.byref(control_interface),
                    bind_version,
                    0,
                    ctypes.c_uint32(name),
                    control_interface.name,
                    ctypes.c_uint32(bind_version),
                    None,
                )
                if control:
                    self._wayland.wl_proxy_add_listener(
                        control,
                        ctypes.cast(
                            control_listener,
                            ctypes.POINTER(ctypes.c_void_p),
                        ),
                        None,
                    )

            @_REGISTRY_GLOBAL_REMOVE
            def on_global_remove(_data, _registry, _name):
                return None

            registry_listener = (ctypes.c_void_p * 2)(
                ctypes.cast(on_global, ctypes.c_void_p).value,
                ctypes.cast(on_global_remove, ctypes.c_void_p).value,
            )
            callback_refs.extend([on_global, on_global_remove, registry_listener])
            if self._wayland.wl_proxy_add_listener(
                    registry,
                    ctypes.cast(registry_listener, ctypes.POINTER(ctypes.c_void_p)),
                    None,
            ) != 0:
                raise RuntimeError("could not install Wayland registry listener")

            # First roundtrip discovers globals, second receives display_info.
            self._roundtrip_with_timeout(display)
            if not control or state["control_version"] < 2:
                return {
                    "success": False,
                    "applied": False,
                    "error": "Gamescope control protocol v2 is unavailable",
                }
            self._roundtrip_with_timeout(display)

            valid_rates = state["valid_rates"]
            if inspect_only:
                display_flags = int(state.get("display_flags", 0))
                return {
                    "success": True,
                    "applied": False,
                    "inspect_only": True,
                    "connector": state.get("connector", ""),
                    "make": state.get("make", ""),
                    "model": state.get("model", ""),
                    "display_flags": display_flags,
                    "internal": bool(display_flags & self._DISPLAY_FLAG_INTERNAL),
                    "external": not bool(display_flags & self._DISPLAY_FLAG_INTERNAL),
                    "valid_rates": valid_rates,
                    "control_version": state.get("control_version", 0),
                }
            if not valid_rates:
                return {
                    "success": True,
                    "applied": False,
                    "target_fps": target_fps,
                    "reason": "active display does not publish switchable refresh modes",
                }
            if target_fps not in valid_rates:
                return {
                    "success": True,
                    "applied": False,
                    "target_fps": target_fps,
                    "valid_rates": valid_rates,
                    "reason": "target is not an exact supported refresh rate",
                }

            selected = self._gamescope_selected_rate(target_fps, valid_rates)
            if selected != target_fps:
                return {
                    "success": True,
                    "applied": False,
                    "target_fps": target_fps,
                    "gamescope_would_select_hz": selected,
                    "valid_rates": valid_rates,
                    "reason": "Gamescope would choose a higher integer-multiple refresh",
                }

            flags = (
                self._TARGET_FLAG_ALLOW_REFRESH_SWITCHING
                | self._TARGET_FLAG_ONLY_CHANGE_REFRESH_RATE
            )
            if state["display_flags"] & self._DISPLAY_FLAG_INTERNAL:
                flags |= self._TARGET_FLAG_INTERNAL_DISPLAY

            self._wayland.wl_proxy_marshal_flags(
                control,
                1,  # set_app_target_refresh_cycle
                None,
                state["control_version"],
                0,
                ctypes.c_uint32(target_fps),
                ctypes.c_uint32(flags),
            )
            self._roundtrip_with_timeout(display)

            verified_refresh_hz = self.wait_for_refresh_hz(target_fps)
            verified = verified_refresh_hz == target_fps
            self.log.info(
                "GFG Target FPS display sync applied: target_fps=%s requested_hz=%s verified_hz=%s",
                target_fps,
                target_fps,
                verified_refresh_hz if verified_refresh_hz is not None else "unavailable",
            )
            return {
                "success": True,
                "applied": True,
                "target_fps": target_fps,
                "refresh_hz": target_fps,
                "verified": verified,
                "verified_refresh_hz": verified_refresh_hz,
                "valid_rates": valid_rates,
            }
        except Exception as error:
            self.log.debug("Gamescope refresh synchronization failed: %s", error)
            return {"success": False, "applied": False, "error": str(error)}
        finally:
            # Proxies are local client objects; disconnecting tears down the
            # protocol connection after Gamescope has processed the request.
            if control:
                try:
                    self._wayland.wl_proxy_destroy(control)
                except Exception:
                    pass
            if registry:
                try:
                    self._wayland.wl_proxy_destroy(registry)
                except Exception:
                    pass
            try:
                self._wayland.wl_display_disconnect(display)
            except Exception:
                pass
            # Keep listeners/interfaces alive until after the final roundtrip.
            _ = callback_refs, protocol_refs

    def get_active_display_info(self) -> Dict[str, Any]:
        """Return Gamescope's active connector and valid output rates."""
        return self.sync_target_fps(0)

    @staticmethod
    def dock_target_fps(display_info: Dict[str, Any]) -> int:
        """Choose the Dock output contract. 60 is preferred whenever physical
        refresh is at least 60 Hz; slower displays use their highest mode.
        Higher-refresh TVs may refuse an exact 60 Hz switch because Gamescope
        prefers an integer-multiple mode; Automatic Dock detects that result
        and uses its 60 FPS Adaptive fallback instead of FixedRefreshBudget.
        """
        rates = sorted({
            int(rate) for rate in display_info.get("valid_rates", [])
            if isinstance(rate, (int, float)) and int(rate) > 0
        })
        if not rates:
            return 60
        if max(rates) >= 60:
            return 60
        return max(rates)

