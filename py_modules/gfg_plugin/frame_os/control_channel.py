"""Governor side of the gfg-pacer control channel (``engine/gfg-pacer/src/control.h``).

Same 136-byte layout, same seqlock protocol: the Governor writes the policy block, the layer
writes the telemetry block.  The Deck is x86-64 (stores are not reordered with stores), so the
odd/even sequence writes through ``mmap`` are enough for the layer's reader.
"""
from __future__ import annotations

import mmap
import os
import struct
from pathlib import Path
from typing import Any, Dict, Optional

MAGIC = 0x43474647          # "GFGC"
VERSION = 2
SIZE = 176
HEADER = struct.Struct("<IIII")                # magic, version, size, writer_pid      @0
POLICY_SEQ_OFF = 16
POLICY_OFF = 24
POLICY = struct.Struct("<IIIIdddII")         # enabled, tick_shaping, pacing, mode, hz, margin, max_wait, generation, rsv
TELEMETRY_SEQ_OFF = 72
TELEMETRY_OFF = 80
# frames, hits, misses, cost p50, cost q, margin, avg_delay, freshness, interval p50, interval p95,
# last_present_ns, applied_generation, swapchain_recreations
TELEMETRY = struct.Struct("<QQQdddddddqII")
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

    def open(self) -> bool:
        if self._map is not None:
            return True
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
                         float(real_hz), float(margin_ms), float(max_wait_ms), int(generation) & 0xFFFFFFFF, 0)
        SEQ.pack_into(m, POLICY_SEQ_OFF, (seq + 2) & 0xFFFFFFFF)
        return True

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
                 recreations) = values
                return {"frames": frames, "hits": hits, "misses": misses, "cost_p50_ms": p50,
                        "cost_q_ms": q, "margin_ms": margin, "avg_delay_ms": delay,
                        "freshness_ms": fresh, "present_interval_p50_ms": iv50,
                        "present_interval_p95_ms": iv95, "last_present_ns": last,
                        "applied_generation": gen, "swapchain_recreations": recreations,
                        "writer_pid": HEADER.unpack_from(m, 0)[3]}
        return None
