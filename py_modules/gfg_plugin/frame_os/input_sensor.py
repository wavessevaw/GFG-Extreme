"""How hard is the player driving the game right now?  (GFG Frame OS, input sensor.)

Reads Linux evdev events from the gamepad without grabbing it (Steam keeps working) and boils
them down to three numbers the real-frame policy needs:

* ``camera`` 0..1  — right-stick deflection and how fast it changes (fast camera = real frames
  matter most: generated frames smear exactly there);
* ``action`` 0..1  — button presses per second (combat, menus);
* ``idle_s``       — seconds since the last meaningful input (pause, cutscene, AFK).

The decoding is pure (``feed``); ``EvdevReader`` only opens the device nodes and hands bytes over.
"""
from __future__ import annotations

import os
import struct
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple

# struct input_event on 64-bit Linux: timeval (2 x long), u16 type, u16 code, s32 value
EVENT = struct.Struct("llHHi")
EV_KEY, EV_ABS = 0x01, 0x03
STATUS_TYPE = 0x7FFF                 # relay pseudo record: code = open gamepads (input_relay.py)
ABS_RX, ABS_RY = 0x03, 0x04          # right stick on Steam Deck / XInput layouts
ABS_X, ABS_Y = 0x00, 0x01            # left stick
STICK_DEADZONE = 0.12
ACTION_WINDOW_S = 2.0
CAMERA_DECAY_S = 0.35                # camera intensity falls to ~0 in this long without motion


class InputState:
    """Pure decoder.  Times are seconds (event timestamps or a caller clock)."""

    def __init__(self, abs_range: Tuple[int, int] = (-32768, 32767)) -> None:
        self.abs_min, self.abs_max = abs_range
        self.right = [0.0, 0.0]
        self.left = [0.0, 0.0]
        self._camera = 0.0
        self._camera_at = 0.0
        self._last_input = None  # type: Optional[float]
        self._presses: Deque[float] = deque()
        self.devices: Optional[int] = None   # gamepads the relay has open (None: unknown)
        self.hidraw: Optional[int] = None
        self.events = 0

    def _norm(self, value: int) -> float:
        span = (self.abs_max - self.abs_min) / 2.0 or 1.0
        mid = (self.abs_max + self.abs_min) / 2.0
        return max(-1.0, min(1.0, (value - mid) / span))

    def _decay(self, now: float) -> float:
        dt = max(0.0, now - self._camera_at)
        return self._camera * max(0.0, 1.0 - dt / CAMERA_DECAY_S)

    def event(self, t: float, etype: int, code: int, value: int) -> None:
        if etype == STATUS_TYPE:
            self.devices = code + max(0, value)     # evdev pads + Deck hidraw nodes
            self.hidraw = max(0, value)
            if self.devices == 0:
                self.clear_activity()
            return
        self.events += 1
        if etype == EV_ABS and code in (ABS_RX, ABS_RY, ABS_X, ABS_Y):
            v = self._norm(value)
            stick = self.right if code in (ABS_RX, ABS_RY) else self.left
            axis = 0 if code in (ABS_RX, ABS_X) else 1
            delta = abs(v - stick[axis])
            stick[axis] = v
            if stick is self.right:
                mag = (self.right[0] ** 2 + self.right[1] ** 2) ** 0.5
                if mag > STICK_DEADZONE:
                    # deflection plus how fast it moves: a flick reads higher than a slow pan
                    level = min(1.0, (mag - STICK_DEADZONE) / (1 - STICK_DEADZONE) + 2.0 * delta)
                    self._camera = max(self._decay(t), level)
                    self._camera_at = t
                    self._last_input = t
            elif max(abs(self.left[0]), abs(self.left[1])) > STICK_DEADZONE:
                self._last_input = t
        elif etype == EV_KEY and value == 1:
            self._presses.append(t)
            self._last_input = t

    def clear_activity(self) -> None:
        """Forget held axes and old input when the input source disappears."""
        self.right = [0.0, 0.0]
        self.left = [0.0, 0.0]
        self._camera = self._camera_at = 0.0
        self._last_input = None
        self._presses.clear()

    def snapshot(self, now: float) -> Dict[str, float]:
        while self._presses and now - self._presses[0] > ACTION_WINDOW_S:
            self._presses.popleft()
        held = (self.right[0] ** 2 + self.right[1] ** 2) ** 0.5 > STICK_DEADZONE
        active = held or max(abs(self.left[0]), abs(self.left[1])) > STICK_DEADZONE
        if active:
            self._last_input = now  # evdev reports changes, not a steady held stick
        camera = self._camera if held else self._decay(now)
        return {
            "camera": round(camera, 3),
            "action": round(min(1.0, len(self._presses) / (ACTION_WINDOW_S * 4.0)), 3),  # 4 presses/s = 1.0
            "idle_s": round(max(0.0, now - self._last_input), 2) if self._last_input is not None else float("inf"),
        }

    def feed(self, data: bytes) -> int:
        """Decode raw evdev bytes; returns the number of events consumed."""
        n = 0
        for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
            sec, usec, etype, code, value = EVENT.unpack_from(data, offset)
            self.event(sec + usec / 1e6, etype, code, value)
            n += 1
        return n


class EvdevReader:
    """Non-blocking reader over event nodes (or the root relay's pipe).  Never grabs a device."""

    def __init__(self, nodes: Iterable[Path] = (), state: Optional[InputState] = None,
                 fds: Optional[Iterable[int]] = None, owned: bool = True, source: str = "direct") -> None:
        self.state = state or InputState()
        self.source = source
        self._owned = owned
        self._fds: List[int] = list(fds or [])
        self._rest: Dict[int, bytes] = {}
        for node in nodes:
            try:
                self._fds.append(os.open(str(node), os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                continue

    @property
    def available(self) -> bool:
        return bool(self._fds)

    def poll(self) -> int:
        consumed = 0
        for fd in list(self._fds):
            while True:
                try:
                    data = os.read(fd, EVENT.size * 64)
                except BlockingIOError:
                    break
                except InterruptedError:
                    continue
                except OSError:
                    self._drop(fd)
                    break
                if not data:
                    self._drop(fd)
                    break
                data = self._rest.pop(fd, b"") + data     # a pipe read can end mid-record
                whole = len(data) - len(data) % EVENT.size
                if whole < len(data):
                    self._rest[fd] = data[whole:]
                consumed += self.state.feed(data[:whole])
        return consumed

    def _drop(self, fd: int) -> None:
        self._fds.remove(fd)
        self._rest.pop(fd, None)
        if self._owned:
            try:
                os.close(fd)
            except OSError:
                pass
        self.state.clear_activity()
        if not self._fds:
            self.state.devices = self.state.hidraw = 0

    def status(self) -> Dict[str, object]:
        devices = self.state.devices
        if devices is None and self.source == "direct":
            devices = len(self._fds)
        return {"source": self.source if self._fds else "none", "gamepads": devices,
                "deck_hidraw": self.state.hidraw, "events": self.state.events}

    def close(self) -> None:
        if self._owned:
            for fd in self._fds:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._fds = []
