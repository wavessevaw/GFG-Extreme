"""Gamepad events for the Frame OS input sensor, from a tiny root child.

While Steam runs, the Deck's built-in controller is read by Steam itself and games get its
input from Steam's virtual gamepad (uinput), whose event node has no ``/dev/input/by-id`` link
and may not be readable by the desktop user the plugin drops to.  So, like the TDP helper, a
root child forked before the drop does exactly one thing: it opens event nodes that look like
gamepads (sticks + face buttons; never keyboards or mice), never grabs them, and forwards only
their stick and button records to the plugin through a pipe.  Without root the sensor opens the
same nodes directly when it can.

Pseudo record ``type == STATUS_TYPE`` carries ``code`` = number of open gamepads (diagnostics).
"""
from __future__ import annotations

import errno
import os
import select
import time
from pathlib import Path
from typing import Dict, List, Optional

from .input_sensor import EV_ABS, EV_KEY, EVENT, STATUS_TYPE

RESCAN_S = 2.0
ABS_NEEDED = (0x00, 0x01, 0x03, 0x04)   # ABS_X, ABS_Y, ABS_RX, ABS_RY
BTN_SOUTH = 0x130


def _bits(text: str) -> int:
    """sysfs capability bitmap: space-separated hex words, most significant first."""
    value = 0
    for word in text.split():
        value = (value << 64) | int(word, 16)
    return value


def is_gamepad(abs_caps: str, key_caps: str) -> bool:
    try:
        abs_bits, key_bits = _bits(abs_caps), _bits(key_caps)
    except ValueError:
        return False
    return all(abs_bits >> b & 1 for b in ABS_NEEDED) and bool(key_bits >> BTN_SOUTH & 1)


def gamepad_event_nodes(sys_input: Path = Path("/sys/class/input"),
                        dev_input: Path = Path("/dev/input")) -> Dict[Path, str]:
    """Event nodes of every gamepad-like device (physical or Steam's virtual pad) -> name."""
    found: Dict[Path, str] = {}
    try:
        entries = sorted(p for p in sys_input.iterdir() if p.name.startswith("event"))
    except OSError:
        return found
    for entry in entries:
        caps = entry / "device" / "capabilities"
        try:
            if not is_gamepad((caps / "abs").read_text(), (caps / "key").read_text()):
                continue
            name = (entry / "device" / "name").read_text().strip()
        except OSError:
            continue
        found[dev_input / entry.name] = name
    return found


class GamepadSet:
    """Keeps every current gamepad node open (rescans for hot-plug and Steam's virtual pad)."""

    def __init__(self, scan=gamepad_event_nodes) -> None:
        self._scan = scan
        self.fds: Dict[Path, int] = {}
        self.names: Dict[Path, str] = {}
        self.errors: Dict[str, str] = {}
        self._next = 0.0

    def rescan(self, now: float) -> None:
        if now < self._next:
            return
        self._next = now + RESCAN_S
        nodes = self._scan()
        for node in list(self.fds):
            if node not in nodes:
                self._close(node)
        for node, name in nodes.items():
            if node in self.fds:
                continue
            try:
                self.fds[node] = os.open(str(node), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
                self.names[node] = name
                self.errors.pop(str(node), None)
            except OSError as error:
                self.errors[str(node)] = errno.errorcode.get(error.errno, str(error.errno))

    def _close(self, node: Path) -> None:
        try:
            os.close(self.fds.pop(node))
        except OSError:
            pass
        self.names.pop(node, None)

    def read_ready(self, timeout: float) -> bytes:
        """Stick and button records from every readable node (filtered, at most one wait)."""
        fds = list(self.fds.values())
        if not fds:
            time.sleep(timeout)
            return b""
        try:
            ready, _, _ = select.select(fds, [], [], timeout)
        except (OSError, ValueError):
            return b""
        out = bytearray()
        for fd in ready:
            try:
                data = os.read(fd, EVENT.size * 64)
            except BlockingIOError:
                continue
            except OSError:  # unplugged: the next rescan drops it
                continue
            out += filter_records(data)
        return bytes(out)

    def close(self) -> None:
        for node in list(self.fds):
            self._close(node)


def filter_records(data: bytes) -> bytes:
    out = bytearray()
    for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
        record = data[offset:offset + EVENT.size]
        if EVENT.unpack(record)[2] in (EV_KEY, EV_ABS):
            out += record
    return bytes(out)


def status_record(devices: int) -> bytes:
    now = time.time()
    return EVENT.pack(int(now), int((now % 1) * 1e6), STATUS_TYPE, devices, 0)


def _serve(out: int) -> None:  # pragma: no cover - runs in the forked root child
    pads = GamepadSet()
    last_count = -1
    parent = os.getppid()
    while os.getppid() == parent:      # the plugin exited (even while no input flowed): stop

        pads.rescan(time.monotonic())
        payload = pads.read_ready(0.5)
        if len(pads.fds) != last_count:
            last_count = len(pads.fds)
            payload = status_record(last_count) + payload
        if not payload:
            continue
        try:
            os.write(out, payload)
        except BlockingIOError:
            continue          # the plugin is not reading (Frame OS off): drop, never block
        except OSError:
            break             # the plugin went away
    pads.close()


def spawn_relay() -> Optional[int]:
    """Fork the relay; returns the non-blocking read end for the plugin."""
    try:
        read_end, write_end = os.pipe()
    except OSError:
        return None
    pid = os.fork()
    if pid == 0:  # pragma: no cover - runs in the forked relay
        try:
            os.closerange(3, write_end)
            os.closerange(write_end + 1, 65536)
            os.set_blocking(write_end, False)
            _serve(write_end)
        finally:
            os._exit(0)
    os.close(write_end)
    os.set_blocking(read_end, False)
    return read_end


_relay_fd: Optional[int] = None


def set_relay_fd(fd: Optional[int]) -> None:
    global _relay_fd
    _relay_fd = fd


def relay_fd() -> Optional[int]:
    return _relay_fd


def direct_fds() -> List[int]:
    """Without the root relay: open what this user can read."""
    fds: List[int] = []
    for node in gamepad_event_nodes():
        try:
            fds.append(os.open(str(node), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC))
        except OSError:
            continue
    return fds
