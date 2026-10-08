"""Governor side of the gfg-pacer control channel (``engine/gfg-pacer/src/control.h``).

Same 232-byte layout (v3), same seqlock protocol: the Governor writes the policy block, the layer
writes the telemetry block.  The Deck is x86-64 (stores are not reordered with stores), so the
odd/even sequence writes through ``mmap`` are enough for the layer's reader.

Nothing in the file outlives the Governor that wrote it: the first ``open`` in a process and every
``reset`` (Frame OS re-enabled) recreate the file (the layer remaps on the inode change), and the
policy carries a CLOCK_MONOTONIC heartbeat (``heartbeat`` every runner tick) that the layer stops
trusting after 2 s.  Telemetry counts as ``live`` only while its writer runs and presents.
"""
from __future__ import annotations

import mmap
import os
import struct
import time
from pathlib import Path
from typing import Any, Dict, Optional

MAGIC = 0x43474647          # "GFGC"
VERSION = 3
SIZE = 232
HEADER = struct.Struct("<IIII")                # magic, version, size, writer_pid      @0
POLICY_SEQ_OFF = 16
POLICY_OFF = 24
# enabled, tick_shaping, pacing, mode, hz, margin, max_wait, generation, rsv, written_ns (heartbeat)
POLICY = struct.Struct("<IIIIdddIIq")
TELEMETRY_SEQ_OFF = 80
TELEMETRY_OFF = 88
# frames, hits, misses, cost p50, cost q, margin, avg_delay, freshness, interval p50, interval p95,
# last_present_ns, applied_generation, swapchain_recreations, present_hold, acquire_block,
# last_present_return_ns, passthrough, rsv, engine
TELEMETRY = struct.Struct("<QQQdddddddqIIddqII16s")
LIVE_NS = 1_000_000_000
MODES = {"act": 0, "observe": 1, "shadow": 2}
SEQ = struct.Struct("<I")
DEFAULT_PATH = Path("/dev/shm/gfg-frame-os")

assert POLICY_OFF + POLICY.size == TELEMETRY_SEQ_OFF
assert TELEMETRY_OFF + TELEMETRY.size == SIZE


class ControlChannel:
    """Owns the control file for the running game (one file, path passed to the game's launch)."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._fd: Optional[int] = None
        self._map: Optional[mmap.mmap] = None
        self._fresh = False                 # this process recreated the file
        self._policy: Optional[Dict[str, Any]] = None

    def open(self) -> bool:
        if self._map is not None:
            return True
        if not self._fresh:
            return self.reset()
        try:
            fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o600)
            if os.fstat(fd).st_size < SIZE:
                os.ftruncate(fd, SIZE)
            mapped = mmap.mmap(fd, SIZE)
        except OSError:
            return False
        magic, version, size, _pid = HEADER.unpack_from(mapped, 0)
        if (magic, version, size) != (MAGIC, VERSION, SIZE):
            mapped[:SIZE] = bytes(SIZE)
            HEADER.pack_into(mapped, 0, MAGIC, VERSION, SIZE, 0)
        self._fd, self._map = fd, mapped
        return True

    def reset(self) -> bool:
        """Recreate the file: nothing an earlier Governor or game left there is read as current."""
        self.close(remove=True)
        self._fresh, self._policy = True, None
        return self.open()

    def close(self, remove: bool = False) -> None:
        if self._map is not None:
            self._map.close()
        if self._fd is not None:
            os.close(self._fd)
        self._map = self._fd = None
        if remove:
            try:
                self.path.unlink()
            except OSError:
                pass

    def write_policy(self, *, enabled: bool, real_hz: float, tick_shaping: bool = True, pacing: bool = True,
                     margin_ms: float = 0.0, max_wait_ms: float = 0.0, mode: str = "observe",
                     generation: int = 0) -> bool:
        if not self.open():
            return False
        m = self._map
        seq = SEQ.unpack_from(m, POLICY_SEQ_OFF)[0]
        if seq % 2:
            seq += 1                                    # a crashed writer left it odd
        SEQ.pack_into(m, POLICY_SEQ_OFF, (seq + 1) & 0xFFFFFFFF)
        POLICY.pack_into(m, POLICY_OFF, int(enabled), int(tick_shaping), int(pacing), MODES[mode],
                         float(real_hz), float(margin_ms), float(max_wait_ms), int(generation) & 0xFFFFFFFF, 0,
                         time.monotonic_ns())
        SEQ.pack_into(m, POLICY_SEQ_OFF, (seq + 2) & 0xFFFFFFFF)
        self._policy = dict(enabled=enabled, real_hz=real_hz, tick_shaping=tick_shaping, pacing=pacing,
                            margin_ms=margin_ms, max_wait_ms=max_wait_ms, mode=mode, generation=generation)
        return True

    def heartbeat(self) -> bool:
        """Rewrite the last policy with a new timestamp (the layer drops a policy 2 s old)."""
        return self.write_policy(**self._policy) if self._policy is not None and self._map is not None else False

    def read_telemetry(self, retries: int = 8) -> Optional[Dict[str, Any]]:
        if not self.open():
            return None
        m = self._map
        for _ in range(retries):
            before = SEQ.unpack_from(m, TELEMETRY_SEQ_OFF)[0]
            if before % 2:
                continue
            values = TELEMETRY.unpack_from(m, TELEMETRY_OFF)
            if SEQ.unpack_from(m, TELEMETRY_SEQ_OFF)[0] == before:
                (frames, hits, misses, p50, q, margin, delay, fresh, iv50, iv95, last, gen,
                 recreations, hold, acquire_block, last_return, passthrough, _rsv, engine) = values
                pid = HEADER.unpack_from(m, 0)[3]
                return {"frames": frames, "hits": hits, "misses": misses, "cost_p50_ms": p50,
                        "cost_q_ms": q, "margin_ms": margin, "avg_delay_ms": delay,
                        "freshness_ms": fresh, "present_interval_p50_ms": iv50,
                        "present_interval_p95_ms": iv95, "last_present_ns": last,
                        "applied_generation": gen, "swapchain_recreations": recreations,
                        "present_hold_ms": hold, "acquire_block_ms": acquire_block,
                        "last_present_return_ns": last_return, "passthrough": bool(passthrough),
                        "engine": engine.split(b"\0", 1)[0].decode("ascii", "replace"),
                        "writer_pid": pid,
                        "live": last > 0 and abs(time.monotonic_ns() - last) <= LIVE_NS and pid_alive(pid)}
        return None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True
