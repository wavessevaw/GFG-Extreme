"""Boost (user, 3.1.1): real frames for a fast camera turn.

While the right stick turns the camera, generated frames smear exactly where the player looks.
Boost lowers the multiplier to x1.25-x1.75 (the engine's base cap goes up to refresh / x) for
the turn and gives the multiplier back as soon as the stick rests. Both changes must be fast,
so they do not wait for the service's 1 s tick: a thread reads the controller and sends the
base cap to the engine itself, and the Policy Coordinator holds still meanwhile.

The model (user, 3.1.1):
  start    a turn of 0.6 s with the stick past 35 %, or 0.3 s past 80 % (a sharp turn); a flick
           or aiming does not count
  depth    a medium turn x1.75, a sharp one the setting's multiplier (x1.5 by default); never a
           base cap above what the game renders at the present TDP (the watts are not touched),
           and no boost at all with less than 5 fps of headroom over the point
  end      the stick rests (under 20 %) for 0.25 s, or the boost has run 1.5 s; the next boost
           needs the stick at rest first, so a long turn does not flip the multiplier back and forth
  meanwhile the pilot and the Governor skip the boost and 2 s after it

Input, as in 2.1.6's Frame OS: the Deck's own controller from its hidraw node (every reader gets
the state reports while Steam runs) and evdev gamepads (an external pad in the dock). Nothing is
grabbed; only the right stick is decoded. The plugin runs as root, so no relay is needed.
"""
from __future__ import annotations

import math
import os
import select
import struct
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

MULTS = (1.25, 1.5, 1.75)
DEFAULT_MULT = 1.5
ENGAGE = 0.35         # right-stick deflection that counts as turning (deadzone and drift stay out)
TURN_S = 0.6          # a turn this long starts a boost; a flick does not
SHARP = 0.80          # a sharp turn ...
SHARP_S = 0.3         # ... starts one sooner and goes deeper
MEDIUM_MULT = 1.75
MAX_BOOST_S = 1.5     # a boost is short (user, 3.1.1); the next one needs the stick to rest first
MIN_GAIN_FPS = 5.0
GPU_BUDGET = 0.95     # share of a second the GPU may be busy at the boosted cap
RELEASE = 0.20        # ... under this ...
REST_S = 0.25         # ... this long gives the multiplier back
HOLD_S = 1.5          # the coordinator holds this long after a boost so the engine status catches up
SETTLE_S = 2.0        # the pilot and the Governor skip readings this close to a boost
RESCAN_S = 2.0
WAIT_S = 0.05
# The Deck controller sends 250 reports a second: the reader wakes at most this often and takes
# what queued up (hidraw keeps 64 reports), not one wake per report. 40 ms is far under the
# 0.3 s a turn needs.
PERIOD_S = 0.04
EPS = 1e-6

# struct input_event on 64-bit Linux: timeval (2 x long), u16 type, u16 code, s32 value
EVENT = struct.Struct("llHHi")
EV_ABS, ABS_RX, ABS_RY = 0x03, 0x03, 0x04
DECK_HID_ID = "HID_ID=0003:000028DE:00001205"   # Valve Steam Deck controller
DECK_STATE_REPORT = 0x09
DECK_RX, DECK_RY = 52, 54                        # s16 LE offsets in the state report (hid-steam)


def boost_cap(refresh: int, mult: float) -> int:
    return max(1, round(int(refresh) / float(mult)))


def deck_hidraw_nodes(sys_hidraw: Path = Path("/sys/class/hidraw"), dev: Path = Path("/dev")) -> Dict[Path, str]:
    found: Dict[Path, str] = {}
    try:
        entries = sorted(sys_hidraw.iterdir())
    except OSError:
        return found
    for entry in entries:
        try:
            if DECK_HID_ID in (entry / "device" / "uevent").read_text():
                found[dev / entry.name] = "hidraw"
        except OSError:
            continue
    return found


def _bits(text: str) -> int:
    value = 0
    for word in text.split():
        value = (value << 64) | int(word, 16)
    return value


def gamepad_event_nodes(sys_input: Path = Path("/sys/class/input"), dev_input: Path = Path("/dev/input")) -> Dict[Path, str]:
    """Event nodes with both sticks and a south button (pads, Steam's virtual pad; never mice)."""
    found: Dict[Path, str] = {}
    try:
        entries = sorted(p for p in sys_input.iterdir() if p.name.startswith("event"))
    except OSError:
        return found
    for entry in entries:
        caps = entry / "device" / "capabilities"
        try:
            abs_bits, key_bits = _bits((caps / "abs").read_text()), _bits((caps / "key").read_text())
        except (OSError, ValueError):
            continue
        if all(abs_bits >> b & 1 for b in (0, 1, ABS_RX, ABS_RY)) and key_bits >> 0x130 & 1:
            found[dev_input / entry.name] = "evdev"
    return found


def deck_right_stick(report: bytes) -> Optional[tuple]:
    if len(report) < 56 or report[0] != 0x01 or report[2] != DECK_STATE_REPORT:
        return None
    rx = int.from_bytes(report[DECK_RX:DECK_RX + 2], "little", signed=True)
    ry = int.from_bytes(report[DECK_RY:DECK_RY + 2], "little", signed=True)
    return rx, ry


class Boost:
    """State machine (pure: ``stick`` and ``step``) plus the reader thread (``start``/``stop``)."""

    def __init__(self, ctl: Any, coord: Any = None, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None,
                 hid_scan: Callable[[], Dict[Path, str]] = deck_hidraw_nodes,
                 pad_scan: Callable[[], Dict[Path, str]] = gamepad_event_nodes, threaded: bool = True) -> None:
        self.threaded = threaded   # False: the caller feeds ``stick`` and ``step`` (tests, sandbox)
        self.ctl = ctl
        self.coord = coord
        self.clock = clock
        self.journal = journal
        self.hid_scan, self.pad_scan = hid_scan, pad_scan
        self.lock = threading.Lock()
        self.enabled = False
        self.mult = DEFAULT_MULT
        self.refresh = 90
        self.wanted: Any = None          # the policy the service wants (multiplier, base_fps)
        self.active = False
        self.engaged_at = -1e9
        self.last_active = -1e9          # the last moment a boost ran
        self.rest_since: Optional[float] = None
        self.turn_since: Optional[float] = None
        self.sharp_since: Optional[float] = None
        self.need_rest = False
        self.deflection = 0.0
        self.point = 0.0                 # the base cap the policy runs now
        self.headroom: Optional[float] = None   # the base cap the game can render at this TDP
        self.cap = 0
        self.pads: Dict[int, list] = {}  # evdev fd -> [rx, ry]
        self.count = 0
        self.errors = 0
        self.thread: Optional[threading.Thread] = None
        self.stopping = threading.Event()
        self.fds: Dict[Path, int] = {}
        self.hid_fds: set = set()
        self.next_scan = 0.0

    # ------------------------------------------------------------------ service side
    def configure(self, *, enabled: bool, mult: float, refresh: int, wanted: Any,
                  headroom: Optional[float] = None) -> None:
        """Every service tick: on only while a game generates frames and Boost is on."""
        mult = mult if mult in MULTS else DEFAULT_MULT
        with self.lock:
            point = self._current_cap(wanted, refresh) if wanted is not None else 0.0
            useful = bool(enabled and wanted is not None and wanted.multiplier
                          and point < boost_cap(refresh, MEDIUM_MULT))
            self.mult, self.refresh, self.point = mult, int(refresh), point
            if not self.active:
                self.headroom = headroom
            changed = self.wanted is None or wanted is None or wanted.key() != self.wanted.key()
            self.wanted = wanted
            if self.active and (not useful or changed):
                self._release(self.clock(), "policy-changed" if useful else "off")
            self.enabled = useful
        if not self.threaded:
            return
        if useful and self.thread is None:
            self.start()
        elif not useful and self.thread is not None:
            self.stop()

    def busy(self, now: float, settle: float = SETTLE_S) -> bool:
        """A boost runs or ran within ``settle`` seconds: its readings are not the point's."""
        return self.active or now - self.last_active < settle

    def status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "active": self.active, "mult": self.mult, "count": self.count,
                "cap": self.cap, "headroom": None if self.headroom is None else round(self.headroom, 1),
                "inputs": len(self.fds), "errors": self.errors}

    @staticmethod
    def estimate_headroom(refresh: int, real: Optional[float], gpu_busy_pct: Optional[float],
                          gen_us: Optional[float], analysis_us: Optional[float]) -> Optional[float]:
        """The base cap the GPU could carry at this TDP if fewer frames were generated: the game's
        own GPU time per frame from the busy share, minus what generation costs now."""
        if not all(isinstance(v, (int, float)) and v > 0 for v in (real, gpu_busy_pct)) or refresh <= 0:
            return None
        gen = (gen_us or 0.0) * 1e-6
        ana = (analysis_us or 0.0) * 1e-6 / 2.0     # one analysis per pair of real frames
        busy = min(1.0, gpu_busy_pct / 100.0)
        game = (busy - gen * max(0.0, refresh - real) - ana * real) / real
        if game <= 0:
            return None
        denom = game - gen + ana
        return float(refresh) if denom <= 0 else max(0.0, (GPU_BUDGET - gen * refresh) / denom)

    @staticmethod
    def _current_cap(wanted: Any, refresh: int) -> float:
        if wanted.base_fps:
            return wanted.base_fps
        return refresh / max(1, wanted.multiplier) if wanted.multiplier > 1 else refresh / 3.0

    # ------------------------------------------------------------------ pure logic
    def stick(self, rx: int, ry: int) -> None:
        self.deflection = min(1.0, math.hypot(rx, ry) / 32767.0)

    def step(self, now: float) -> None:
        with self.lock:
            if not self.enabled:
                return
            if not self.active:
                if self.need_rest:
                    self.need_rest = self.deflection >= RELEASE
                    return
                self.turn_since = None if self.deflection < ENGAGE else (self.turn_since if self.turn_since is not None else now)
                self.sharp_since = None if self.deflection < SHARP else (self.sharp_since if self.sharp_since is not None else now)
                sharp = self.sharp_since is not None and now - self.sharp_since >= SHARP_S - EPS
                if sharp or (self.turn_since is not None and now - self.turn_since >= TURN_S - EPS):
                    self.turn_since = self.sharp_since = None
                    self._engage(now, self.mult if sharp else MEDIUM_MULT)
                return
            self.last_active = now
            if now - self.engaged_at >= MAX_BOOST_S - EPS:
                self._release(now, "max-time")
                self.need_rest = True
            elif self.deflection >= RELEASE:
                self.rest_since = None
            elif self.rest_since is None:
                self.rest_since = now
            elif now - self.rest_since >= REST_S - EPS:
                self._release(now, "stick-rests")

    def _hold(self, now: float) -> None:
        if self.coord is not None:
            self.coord.hold_until = max(getattr(self.coord, "hold_until", 0.0), now + HOLD_S)

    def _send(self, base: int, mult: int) -> bool:
        try:
            self.ctl.set_var("kfg_base_fps", base)
            self.ctl.set_var("kfg_multiplier", mult)
            return True
        except Exception as error:   # gamescopectl failed: no boost, the policy stays as it is
            self.errors += 1
            if self.journal:
                self.journal("boost-failed", error=str(error)[:200])
            return False

    def _engage(self, now: float, mult: float) -> None:
        cap = float(boost_cap(self.refresh, mult))
        if self.headroom is not None:
            cap = min(cap, self.headroom)
        cap = int(cap)
        if self.headroom is None or cap < self.point + MIN_GAIN_FPS:
            return   # the game cannot render more frames at this TDP: a boost would only stutter
        self._hold(now)
        if not self._send(cap, 1):
            return
        self.cap = cap
        self.active, self.engaged_at, self.last_active, self.rest_since = True, now, now, None
        self.count += 1

    def _release(self, now: float, why: str) -> None:
        self._hold(now)
        w = self.wanted
        if w is not None:
            self._send(w.base_fps, w.multiplier)
        self.active, self.last_active, self.rest_since, self.turn_since, self.cap = False, now, None, None, 0
        self.last_why = why

    # ------------------------------------------------------------------ reader thread
    def start(self) -> None:
        self.stopping.clear()
        self.thread = threading.Thread(target=self._run, name="gfg-boost", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        t = self.thread
        self.thread = None
        self.stopping.set()
        if t is not None and t is not threading.current_thread():
            t.join(timeout=1.0)
        with self.lock:
            if self.active:
                self._release(self.clock(), "stop")
        self._close_all()
        self.deflection = 0.0

    def _rescan(self, now: float) -> None:
        if now < self.next_scan:
            return
        self.next_scan = now + RESCAN_S
        nodes = {**self.pad_scan(), **self.hid_scan()}   # the Deck's own pad, Steam's virtual pad, a dock pad
        for node in [n for n in self.fds if n not in nodes]:
            self._close(node)
        for node, kind in nodes.items():
            if node in self.fds:
                continue
            try:
                fd = os.open(str(node), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
            except OSError:
                continue
            self.fds[node] = fd
            if kind == "hidraw":
                self.hid_fds.add(fd)
            else:
                self.pads[fd] = [0, 0]

    def _close(self, node: Path) -> None:
        fd = self.fds.pop(node)
        self.hid_fds.discard(fd)
        self.pads.pop(fd, None)
        try:
            os.close(fd)
        except OSError:
            pass

    def _close_all(self) -> None:
        for node in list(self.fds):
            self._close(node)
        self.next_scan = 0.0

    def _read(self, fd: int) -> None:
        if fd in self.hid_fds:
            stick = None
            for _ in range(64):
                try:
                    report = os.read(fd, 64)
                except OSError:
                    break
                if not report:
                    break
                stick = deck_right_stick(report) or stick
            if stick is not None:
                self.stick(*stick)
            return
        try:
            data = os.read(fd, EVENT.size * 64)
        except OSError:
            return
        pad = self.pads.get(fd)
        if pad is None:
            return
        for off in range(0, len(data) - EVENT.size + 1, EVENT.size):
            _, _, typ, code, value = EVENT.unpack_from(data, off)
            if typ == EV_ABS and code in (ABS_RX, ABS_RY):
                pad[code - ABS_RX] = value
        self.stick(*pad)

    def _run(self) -> None:  # pragma: no cover - needs a controller
        while not self.stopping.is_set():
            now = self.clock()
            self._rescan(now)
            fds = list(self.fds.values())
            if not fds:
                self.stopping.wait(0.5)
                continue
            try:
                ready, _, _ = select.select(fds, [], [], WAIT_S)
            except (OSError, ValueError):
                ready = []
            for fd in ready:
                self._read(fd)
            self.step(self.clock())
            rest = PERIOD_S - (self.clock() - now)
            if ready and rest > 0:
                self.stopping.wait(rest)
        self._close_all()
