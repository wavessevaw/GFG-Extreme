"""Policy Coordinator: the one place that tells the KEDAVRA Gamescope what to do.

Every second the service hands it the policy it wants (multiplier, base frame cap, filters,
HUD path) and the engine status. The coordinator sends the convars only when the wanted policy
differs from what the engine reports, finishes each send with ``kfg_policy=<revision>``, and
calls the policy applied only when the engine echoes that revision back with the same
requested values. So the panel never shows a mode the engine did not take.

States:
  offline    no engine status (stock Gamescope, or the engine is not installed or not running)
  outdated   the engine runs but is too old to confirm a policy (no "policy" in its status)
  hold       the status is stale: nothing is sent until it is fresh again
  applying   sent, waiting for the engine to confirm
  confirmed  the engine reports the wanted policy
  conflict   something else keeps changing the engine's settings (another plugin, a script);
             the coordinator backs off instead of fighting it
  error      gamescopectl failed; retried with a growing delay

There is exactly one owner of the frame-rate limit: the engine's base cap. GFG never sets
Steam's own frame limiter.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Optional
from collections import deque

CONFIRM_TIMEOUT_S = 3.0
BACKOFF_MAX_S = 30.0
DRIFT_WINDOW_S = 60.0
DRIFT_LIMIT = 3
CONFLICT_BACKOFF_S = 30.0
CONFLICT_BACKOFF_MAX_S = 120.0
REAPPLY_MIN_S = 5.0


@dataclass(frozen=True)
class Policy:
    multiplier: int = 0  # 0 off, 1 auto, 2, 3
    base_fps: int = 0    # 0 = none / chosen by the engine
    post: str = ""
    hud_path: str = ""
    auto_floor: int = 0  # lowest cap Auto may use; 0 = refresh / 3 (x3), 24 at 90 Hz = x3.75
    hdr: bool = True     # generate and filter HDR games (kfg_hdr); False = they pass through

    def key(self) -> tuple:
        return (self.multiplier, self.base_fps, self.post, self.hud_path, self.auto_floor, self.hdr)


@dataclass
class _Attempt:
    rev: int
    policy: Policy
    sent_at: float
    status_time_ns: int


@dataclass
class CoordinatorState:
    state: str = "offline"
    message: str = ""
    rev: int = 0
    confirmed_rev: int = 0
    applied: Optional[Policy] = None
    epoch: int = 0  # bumps whenever multiplier or cap change: measurement windows restart
    errors: int = 0
    conflicts: int = 0  # conflicts in a row: the back-off doubles
    drifts: Deque[float] = field(default_factory=deque)


class PolicyCoordinator:
    def __init__(self, ctl: Any, clock: Callable[[], float] = time.monotonic, journal: Optional[Callable[..., None]] = None) -> None:
        self.ctl = ctl
        self.clock = clock
        self.journal = journal
        self.s = CoordinatorState()
        self.wanted: Optional[Policy] = None
        self.pending: Optional[_Attempt] = None
        self.retry_at = 0.0
        self.last_apply_at = -1e9
        # Boost (3.1.1) sends the base cap itself for a camera turn and puts it back after: until
        # then the coordinator neither sends nor counts the difference as somebody else's drift.
        self.hold_until = -1e9
        # The engine's policy revision restarts at 0 with Gamescope; ours keeps counting.
        self.next_rev = int(time.time()) % 1_000_000 + 1

    # ------------------------------------------------------------------ helpers
    def _note(self, kind: str, **fields: Any) -> None:
        if self.journal:
            try:
                self.journal(kind, **fields)
            except Exception:
                pass

    @staticmethod
    def _matches(want: Policy, st: Dict[str, Any]) -> bool:
        try:
            return (int(st.get("req_multiplier", -1)) == want.multiplier
                    and int(st.get("req_base_fps", -1)) == want.base_fps
                    and int(st.get("req_auto_floor", -1)) == want.auto_floor
                    and bool(st.get("hdr_enabled")) == want.hdr
                    and str(st.get("post", "")) == want.post)
        except (TypeError, ValueError):
            return False

    def engine_runs(self, policy: Optional[Policy], st: Dict[str, Any]) -> bool:
        """The engine's status shows this policy, confirmed by its revision (not just remembered)."""
        return (policy is not None and self.s.applied is not None and self.s.applied.key() == policy.key()
                and bool(st.get("fresh")) and int(st.get("policy") or 0) == self.s.confirmed_rev
                and self._matches(policy, st))

    def _set(self, state: str, message: str = "") -> None:
        if state != self.s.state:
            self._note("policy-state", state=state, was=self.s.state, message=message)
        self.s.state = state
        self.s.message = message

    # ------------------------------------------------------------------ API
    def want(self, policy: Policy) -> None:
        if self.wanted is None or policy.key() != self.wanted.key():
            if self.wanted is None or (policy.multiplier, policy.base_fps, policy.auto_floor, policy.post, policy.hdr) != (
                    self.wanted.multiplier, self.wanted.base_fps, self.wanted.auto_floor, self.wanted.post, self.wanted.hdr):
                self.s.epoch += 1
            self.wanted = policy
            self.retry_at = 0.0  # a new wish is sent now, not after an old back-off
            self.s.errors = 0
            if self.s.state == "conflict":
                self.s.drifts.clear()

    def tick(self, st: Dict[str, Any]) -> Dict[str, Any]:
        now = self.clock()
        if self.wanted is None:
            return self.snapshot()
        if not st or st.get("engine") == "absent":
            self.pending = None
            self._set("offline", "Gamescope KEDAVRA is not running")
            return self.snapshot()
        if not st.get("fresh"):
            self._set("hold", "Engine status is stale: waiting before sending anything")
            return self.snapshot()
        if "policy" not in st or "req_auto_floor" not in st or "hdr_enabled" not in st:
            self._set("outdated", "The running Gamescope KEDAVRA is older than GFG Extreme 3.0: reinstall the engine and reboot")
            return self.snapshot()
        if now < self.hold_until:
            return self.snapshot()
        want = self.wanted
        engine_rev = int(st.get("policy") or 0)
        time_ns = int(st.get("time_ns") or 0)

        if self.pending is not None:
            p = self.pending
            if engine_rev == p.rev and self._matches(p.policy, st) and time_ns > p.status_time_ns:
                self.pending = None
                self.s.confirmed_rev = p.rev
                self.s.applied = p.policy
                self.s.errors = 0
                if now - p.sent_at < CONFIRM_TIMEOUT_S and not self.s.drifts:
                    self.s.conflicts = 0
                self._set("confirmed")
                self._note("policy-confirmed", rev=p.rev, multiplier=p.policy.multiplier,
                           base_fps=p.policy.base_fps, post=p.policy.post)
            elif now - p.sent_at > CONFIRM_TIMEOUT_S:
                self.pending = None
                self._fail(now, "The engine did not confirm the policy in time")
            else:
                return self.snapshot()

        if self.s.state == "conflict" and now < self.retry_at:
            return self.snapshot()
        in_sync = (self.s.applied is not None and self.s.applied.key() == want.key()
                   and engine_rev == self.s.confirmed_rev and self._matches(want, st))
        if in_sync:
            if self.s.drifts and now - self.s.drifts[-1] > DRIFT_WINDOW_S and now - self.last_apply_at > DRIFT_WINDOW_S:
                self.s.drifts.clear()
                self.s.conflicts = 0  # a quiet minute since our last send: whoever fought has stopped
            if self.s.state != "confirmed":
                self._set("confirmed")
            return self.snapshot()
        if self.s.applied is not None and self.s.applied.key() == want.key():
            # Was confirmed, now the engine differs: Gamescope restarted (revision back to 0)
            # or someone else changed a convar.
            self.s.drifts.append(now)
            while self.s.drifts and now - self.s.drifts[0] > DRIFT_WINDOW_S:
                self.s.drifts.popleft()
            self._note("policy-drift", engine_rev=engine_rev, rev=self.s.confirmed_rev,
                       req_multiplier=st.get("req_multiplier"), req_base_fps=st.get("req_base_fps"))
            self.s.applied = None
            # After a conflict, one more drift right after our send is enough to back off again.
            if len(self.s.drifts) > (DRIFT_LIMIT if self.s.conflicts == 0 else 0):
                delay = min(CONFLICT_BACKOFF_MAX_S, CONFLICT_BACKOFF_S * 2 ** self.s.conflicts)
                self.s.conflicts += 1
                self.retry_at = now + delay
                self._set("conflict", "Another tool keeps changing the frame generation settings "
                          f"(is the standalone GSF Kedavra plugin active?). GFG backs off for {delay:.0f} s.")
                return self.snapshot()
        if now < self.retry_at or now - self.last_apply_at < (REAPPLY_MIN_S if self.s.drifts else 0.0):
            return self.snapshot()
        self._apply(now, want, time_ns)
        return self.snapshot()

    def _fail(self, now: float, message: str) -> None:
        self.s.errors += 1
        delay = min(BACKOFF_MAX_S, 2.0 ** (self.s.errors - 1))
        self.retry_at = now + delay
        self._set("error", f"{message} (retry in {delay:.0f} s)")

    def _apply(self, now: float, want: Policy, status_time_ns: int) -> None:
        rev = self.next_rev
        self.next_rev += 1
        self.last_apply_at = now
        try:
            # HUD first (harmless), HDR switch, filters, cap, then the multiplier; the revision last, so its
            # echo proves that everything before it arrived.
            if want.hud_path:
                self.ctl.set_var("kfg_hud", want.hud_path)
            self.ctl.set_var("kfg_hdr", 1 if want.hdr else 0)
            self.ctl.set_var("kfg_post", want.post)
            self.ctl.set_var("kfg_auto_floor", want.auto_floor)
            self.ctl.set_var("kfg_base_fps", want.base_fps)
            self.ctl.set_var("kfg_multiplier", want.multiplier)
            self.ctl.set_var("kfg_policy", rev)
        except Exception as error:  # gamescopectl missing, timed out, refused
            self._note("policy-send-failed", rev=rev, error=str(error)[:300])
            self._fail(now, f"Could not send the policy: {error}")
            return
        self.pending = _Attempt(rev, want, now, status_time_ns)
        self.s.rev = rev
        self._set("applying", "Waiting for the engine to confirm")
        self._note("policy-sent", rev=rev, multiplier=want.multiplier, base_fps=want.base_fps, post=want.post)

    def take_over(self) -> None:
        """The player pressed "Take over" (or removed the other tool): send now, forget the conflict."""
        self.s.drifts.clear()
        self.s.conflicts = 0
        self.retry_at = 0.0
        self.s.applied = None
        if self.s.state == "conflict":
            self._set("error", "Taking over")

    def snapshot(self) -> Dict[str, Any]:
        w = self.wanted
        a = self.s.applied
        return {
            "state": self.s.state,
            "message": self.s.message,
            "rev": self.s.rev,
            "confirmed_rev": self.s.confirmed_rev,
            "epoch": self.s.epoch,
            "wanted": None if w is None else {"multiplier": w.multiplier, "base_fps": w.base_fps,
                                              "auto_floor": w.auto_floor, "post": w.post},
            "applied": None if a is None else {"multiplier": a.multiplier, "base_fps": a.base_fps,
                                               "auto_floor": a.auto_floor, "post": a.post},
        }
