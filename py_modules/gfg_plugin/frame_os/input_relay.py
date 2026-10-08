"""Gamepad events for the Frame OS input sensor, from a tiny root child.

While Steam runs, the Deck's built-in controller is read by Steam itself and games get its
input from Steam's virtual gamepad (uinput), whose event node has no ``/dev/input/by-id`` link
and may not be readable by the desktop user the plugin drops to.  So, like the TDP helper, a
root child forked before the drop does exactly one thing: it opens event nodes that look like
gamepads (sticks + face buttons; never keyboards or mice), never grabs them, and forwards only
their stick and button records to the plugin through a pipe.  Without root the sensor opens the
same nodes directly when it can.

The Deck's own controller is also read from its hidraw node: while Steam runs, the kernel stops
feeding its evdev node, but every hidraw reader still receives the controller's state reports.
Only sticks and the main buttons are decoded from them (``DeckReportDecoder``).

Pseudo record ``type == STATUS_TYPE``: ``code`` = open evdev gamepads, ``value`` = open Deck
hidraw nodes (diagnostics).
"""
from __future__ import annotations

import errno
import os
import select
import time
from pathlib import Path
from typing import Dict, List, Optional

from .input_sensor import ABS_RX, ABS_RY, ABS_X, ABS_Y, EV_ABS, EV_KEY, EVENT, STATUS_TYPE

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


DECK_HID_ID = "HID_ID=0003:000028DE:00001205"   # Valve Steam Deck controller
DECK_STATE_REPORT = 0x09
DECK_AXES = ((ABS_X, 48), (ABS_Y, 50), (ABS_RX, 52), (ABS_RY, 54))   # s16 LE offsets (hid-steam)
DECK_BUTTON_BYTES = (8, 9, 10)          # face, shoulder, d-pad, menu, grip and stick-click bits
AXIS_STEP = 256                         # forward a stick only when it moved this much


def deck_hidraw_nodes(sys_hidraw: Path = Path("/sys/class/hidraw"), dev: Path = Path("/dev")) -> Dict[Path, str]:
    found: Dict[Path, str] = {}
    try:
        entries = sorted(sys_hidraw.iterdir())
    except OSError:
        return found
    for entry in entries:
        try:
            if DECK_HID_ID in (entry / "device" / "uevent").read_text():
                found[dev / entry.name] = "Steam Deck controller (hidraw)"
        except OSError:
            continue
    return found


class DeckReportDecoder:
    """Deck controller state report -> evdev-style stick and button records (changes only)."""

    def __init__(self) -> None:
        self.axes: Dict[int, int] = {}
        self.buttons = [0] * len(DECK_BUTTON_BYTES)

    def decode(self, report: bytes, t: float) -> bytes:
        if len(report) < 56 or report[0] != 0x01 or report[2] != DECK_STATE_REPORT:
            return b""
        sec, usec = int(t), int((t % 1) * 1e6)
        out = bytearray()
        for code, offset in DECK_AXES:
            value = int.from_bytes(report[offset:offset + 2], "little", signed=True)
            if abs(value - self.axes.get(code, 0)) >= AXIS_STEP or (value == 0 and self.axes.get(code)):
                self.axes[code] = value
                out += EVENT.pack(sec, usec, EV_ABS, code, value)
        for i, offset in enumerate(DECK_BUTTON_BYTES):
            byte = report[offset]
            pressed = byte & ~self.buttons[i]
            self.buttons[i] = byte
            for bit in range(8):
                if pressed >> bit & 1:
                    out += EVENT.pack(sec, usec, EV_KEY, 0x100 + offset * 8 + bit, 1)
        return bytes(out)


class GamepadSet:
    """Keeps every current gamepad node open (rescans for hot-plug and Steam's virtual pad)."""

    def __init__(self, scan=gamepad_event_nodes, hid_scan=deck_hidraw_nodes) -> None:
        self._scan = scan
        self._hid_scan = hid_scan
        self.decoders: Dict[int, DeckReportDecoder] = {}
        self.fds: Dict[Path, int] = {}
        self.names: Dict[Path, str] = {}
        self.errors: Dict[str, str] = {}
        self._next = 0.0

    def rescan(self, now: float) -> None:
        if now < self._next:
            return
        self._next = now + RESCAN_S
        hid = self._hid_scan()
        nodes = dict(hid)
        for node, name in self._scan().items():
            if hid and name.strip() == "Steam Deck":
                continue            # the same controller, already read from hidraw
            nodes[node] = name
        for node in list(self.fds):
            if node not in nodes:
                self._close(node)
        for node, name in nodes.items():
            if node in self.fds:
                continue
            try:
                fd = os.open(str(node), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
                self.fds[node] = fd
                self.names[node] = name
                if node in hid:
                    self.decoders[fd] = DeckReportDecoder()
                self.errors.pop(str(node), None)
            except OSError as error:
                self.errors[str(node)] = errno.errorcode.get(error.errno, str(error.errno))

    @property
    def counts(self) -> tuple:
        hid = sum(1 for fd in self.fds.values() if fd in self.decoders)
        return len(self.fds) - hid, hid

    def _close(self, node: Path) -> None:
        fd = self.fds.get(node)
        self.decoders.pop(fd, None)
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
            decoder = self.decoders.get(fd)
            if decoder is not None:
                for _ in range(64):              # one state report per read
                    try:
                        report = os.read(fd, 64)
                    except OSError:              # drained (EAGAIN) or unplugged
                        break
                    if not report:
                        break
                    out += decoder.decode(report, time.time())
                continue
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
        self._next = 0.0


def filter_records(data: bytes) -> bytes:
    out = bytearray()
    for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
        record = data[offset:offset + EVENT.size]
        if EVENT.unpack(record)[2] in (EV_KEY, EV_ABS):
            out += record
    return bytes(out)


PIPE_CHUNK = (4096 // EVENT.size) * EVENT.size     # <= PIPE_BUF: each write is atomic, whole records


def write_records(out: int, payload: bytes) -> bool:
    """Whole records only; a full pipe (plugin not reading) drops the rest, never blocks.
    False when the plugin is gone."""
    for start in range(0, len(payload), PIPE_CHUNK):
        try:
            os.write(out, payload[start:start + PIPE_CHUNK])
        except BlockingIOError:
            return True
        except OSError:
            return False
    return True


def status_record(evdev: int, hidraw: int = 0) -> bytes:
    now = time.time()
    return EVENT.pack(int(now), int((now % 1) * 1e6), STATUS_TYPE, evdev, hidraw)


WAKE_S = 0.02          # at most 50 wake-ups a second (the Deck reports far faster)


def _serve(out: int, wanted: Optional[Path]) -> None:  # pragma: no cover - runs in the forked root child
    pads = GamepadSet()
    last_count = (-1, -1)
    parent = os.getppid()
    while os.getppid() == parent:      # the plugin exited (even while no input flowed): stop
        if wanted is not None and not wanted.exists():
            pads.close()               # Frame OS off in every profile: hold nothing, read nothing
            last_count = (-1, -1)
            time.sleep(RESCAN_S)
            continue
        pads.rescan(time.monotonic())
        payload = pads.read_ready(0.5)
        time.sleep(WAKE_S)
        if pads.counts != last_count:
            last_count = pads.counts
            payload = status_record(*last_count) + payload
        if not payload:
            continue
        if not write_records(out, payload):
            break             # the plugin went away
    pads.close()


def spawn_relay(wanted: Optional[Path] = None) -> Optional[int]:
    """Fork the relay; returns the non-blocking read end for the plugin.

    ``wanted``: the Frame OS launch marker; without it the relay holds no device open.
    """
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
            _serve(write_end, wanted)
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
    """Without the root relay: open the evdev pads this user can read (no hidraw decoding here)."""
    fds: List[int] = []
    for node in gamepad_event_nodes():
        try:
            fds.append(os.open(str(node), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC))
        except OSError:
            continue
    return fds
