"""Executable lease protocol example, NOT a hardware controller or energy model."""
from dataclasses import dataclass
from enum import Enum


class Phase(Enum):
    IDLE = 'idle'
    APPLY = 'apply-pending'
    VERIFY = 'verify'
    RESTORE = 'restore-pending'
    USER = 'user-owned'


@dataclass(frozen=True)
class Command:
    token: int
    axis: str
    value: float
    restore: bool = False


class Coordinator:
    def __init__(self):
        self.phase = Phase.IDLE
        self.serial = 0
        self.command = None
        self.original = None
        self.deadline = None
        self.epoch = None

    def propose(self, *, axis, value, observed, epoch, now, timeout, fresh, healthy, owned):
        if self.phase != Phase.IDLE or not (fresh and healthy and owned):
            return None
        if timeout <= 0 or value == observed:
            return None
        self.serial += 1
        self.original, self.epoch, self.deadline = observed, epoch, now + timeout
        self.command = Command(self.serial, axis, value)
        self.phase = Phase.APPLY
        return self.command  # adapter persists intent BEFORE sending this command

    def applied(self, token, readback):
        if self.phase != Phase.APPLY or token != self.command.token:
            return False
        if readback != self.command.value:
            self.abort()
            return False
        self.phase = Phase.VERIFY
        return True

    def abort(self):
        if self.phase not in (Phase.APPLY, Phase.VERIFY):
            return self.command if self.phase == Phase.RESTORE else None
        self.serial += 1
        self.command = Command(self.serial, self.command.axis, self.original, True)
        self.phase = Phase.RESTORE
        return self.command  # never erase pending restore just because a deadline elapsed

    def observe(self, *, epoch, now, fresh, healthy, external_change=False):
        if external_change:
            self.phase = Phase.USER
            self.command = None  # never overwrite a user's new value with our original
            return None
        if self.phase in (Phase.APPLY, Phase.VERIFY):
            if epoch != self.epoch or not fresh or not healthy or now >= self.deadline:
                return self.abort()
        return self.command if self.phase == Phase.RESTORE else None

    def restored(self, token, readback):
        if self.phase != Phase.RESTORE or token != self.command.token or readback != self.original:
            return False
        self.phase, self.command = Phase.IDLE, None
        return True

    def commit(self, *, epoch, now, complete_evidence, fresh, healthy, owned):
        if (self.phase != Phase.VERIFY or epoch != self.epoch or now >= self.deadline
                or not (complete_evidence and fresh and healthy and owned)):
            return False
        # Session-level ownership must retain the user's original after a successful trial.
        # This example deliberately does not replace the actuator's restoration journal.
        self.phase, self.command = Phase.IDLE, None
        return True
