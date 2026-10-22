"""Governor 2.0, shadow stage: one experiment at a time, watched (docs/governor2/CONCEPT.ru.md).

Three loops can change the game's workload on purpose: the Governor stepping the TDP down
("tdp"), Power Split trying a CPU clock level ("cpu") and the GPU clock ceiling trying a step
("gpu"). 3.0 already keeps them apart through its interlocks (Split and the GPU ceiling start
only while the Governor is settled, the Governor freezes while either one tries a step, the GPU
ceiling waits for Split). This module does not decide anything yet. Every second it is told
which experiments run and keeps the record a 2.0 coordinator would keep:

  lease-start / lease-end   one transaction per experiment: id, axis, duration, outcome
  lease-conflict            two experiments at once: the 2.0 coordinator would have refused the
                            second (the first holder keeps the lease)
  lease-overrun             an experiment past its deadline: 2.0 would have rolled it back

On the Deck these lines show whether the interlocks really keep one experiment at a time before
the coordinator takes the decisions over (limited actuation, the next stage).
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

DEADLINE_S = {"tdp": 30.0, "cpu": 90.0, "gpu": 60.0}


class ExperimentLease:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 journal: Optional[Callable[..., None]] = None) -> None:
        self.clock = clock
        self.journal = journal
        self.serial = 0
        self.holder: Optional[str] = None
        self.since = 0.0
        self.overrun = False
        self.conflicts = 0
        self._conflicting: set = set()

    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    def observe(self, running: Dict[str, bool]) -> Dict[str, Any]:
        """running: axis -> that loop has an experiment on now."""
        now = self.clock()
        active = {a for a, on in running.items() if on}
        if self.holder is not None and self.holder not in active:
            self._note("lease-end", id=self.serial, axis=self.holder, seconds=round(now - self.since, 1),
                       overrun=self.overrun)
            self.holder = None
        if self.holder is None and active:
            # Several starting in the same second: a fixed order picks the holder (TDP first).
            self.holder = next(a for a in ("tdp", "cpu", "gpu") if a in active) if active & {"tdp", "cpu", "gpu"} else sorted(active)[0]
            self.serial += 1
            self.since, self.overrun = now, False
            self._note("lease-start", id=self.serial, axis=self.holder)
        others = active - {self.holder} if self.holder else set()
        for axis in others - self._conflicting:
            self.conflicts += 1
            self._note("lease-conflict", id=self.serial, holder=self.holder, axis=axis,
                       held_s=round(now - self.since, 1))
        self._conflicting = others
        if self.holder is not None and not self.overrun and now - self.since > DEADLINE_S.get(self.holder, 60.0):
            self.overrun = True
            self._note("lease-overrun", id=self.serial, axis=self.holder, seconds=round(now - self.since, 1))
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {"mode": "shadow", "holder": self.holder, "id": self.serial if self.holder else None,
                "held_s": round(self.clock() - self.since, 1) if self.holder else None,
                "conflicts": self.conflicts, "overrun": self.overrun}
