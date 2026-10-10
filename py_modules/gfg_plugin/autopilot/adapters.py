"""C1 adapter from already-read Governor caches. No files, probes or writers."""
from dataclasses import asdict
import json
from .contracts import Config, Host, Snapshot, number
from .perception import perceive


class ObservationMonitor:
    def __init__(self, config=Config()):
        self.config = config
        self.key = None
        self.after_seq = 0
        self.last_tick = None
        self.focus_epoch = 0.0
        self.snapshot = Snapshot("", 0.0, blocked_reason="waiting-for-session")

    def update(self, *, now, stream, generation, profile, backend, launch,
               launch_at, target, sensors, focus, focus_at, runtime_state,
               restore_pending=False, poll_error=None):
        launch_key = launch.get("launch_key")
        identity_ok = (isinstance(launch_key, (tuple, list)) and len(launch_key) >= 3
                       and all(isinstance(x, (str, int, float)) and not isinstance(x, bool)
                               for x in launch_key))
        key = (profile, backend, tuple(launch_key) if identity_ok else (),
               generation, stream.context, target)
        interrupted = (self.last_tick is not None
                       and not 0 <= now - self.last_tick <= self.config.max_gap_s)
        if key != self.key or interrupted:
            self.after_seq = stream.seq
            # Focus is parsed before the monitor runs in the same iteration.
            # Use the previous receipt boundary, not the later monitor time.
            self.focus_epoch = (self.last_tick if self.last_tick is not None and not interrupted
                                else max(0.0, now - self.config.max_age_s))
        self.key, self.last_tick = key, now
        reason = ""
        if backend != "gfg":
            reason = "external-backend-observe-only"
        elif not profile or not identity_ok or not launch.get("running"):
            reason = "launch-identity-unavailable"
        elif number(launch_at) is None or not 0 <= now - launch_at <= 6.0:
            reason = "launch-probe-stale"
        elif launch.get("renderer_loaded") is not True:
            reason = "renderer-not-confirmed"
        elif poll_error:
            reason = "renderer-read-failed"
        elif restore_pending:
            reason = "restore-pending"
        elif runtime_state in ("PAUSED", "DISABLED", "RESTORING", "RESTORE_PENDING"):
            reason = "runtime-not-observing"
        elif focus is not True or number(focus_at) is None or not self.focus_epoch <= focus_at <= now:
            reason = "focus-unconfirmed-or-menu"
        if reason:
            # Returning from menus/disabled/external state requires a new window.
            self.after_seq = stream.seq
        samples = tuple(s for s in stream.samples
                        if s.seq > self.after_seq and now - s.timestamp_mono <= self.config.window_s)
        # Multiple log lines read together are not independent time samples.
        independent = {}
        for sample in samples:
            independent[sample.timestamp_mono] = sample
        host = None
        at = number(sensors.get("sample_monotonic"))
        seq = sensors.get("sample_seq")
        if at is not None and isinstance(seq, int) and seq > 0:
            host = Host(at, seq, number(sensors.get("gpu_busy_pct")),
                        number(sensors.get("cpu_top_core_pct")), number(sensors.get("temp_c")))
        session = json.dumps(key, ensure_ascii=True, separators=(",", ":"))
        self.snapshot = Snapshot(session, now, tuple(independent.values()), host,
                                 tuple(p for p in stream.pressure if p[0] > self.after_seq),
                                 number(target), reason, backend, stream.context)

    def status(self, now, requested_profile=""):
        snapshot = self.snapshot
        result = perceive(snapshot, now, self.config)
        mismatch = bool(requested_profile and (not self.key or requested_profile != self.key[0]))
        if mismatch:
            result = perceive(Snapshot("", now, blocked_reason="profile-not-active"), now, self.config)
        latest = snapshot.samples[-1] if snapshot.samples and not mismatch else None
        fresh = (latest is not None and not snapshot.blocked_reason
                 and 0 <= now - snapshot.timestamp_mono <= self.config.max_age_s
                 and 0 <= now - latest.timestamp_mono <= self.config.max_age_s)
        return {
            "stage": "C1", "state": "OBSERVE_ONLY", "action": "OBSERVE",
            "control_enabled": False, "perception": asdict(result),
            "real_fps": latest.real_fps if fresh else None,
            "output_fps": latest.output_fps if fresh else None,
            "fps_source": "renderer-reported" if fresh else "unavailable",
            "sample_count": len(snapshot.samples) if not mismatch else 0,
            "measurement_clock": "log-receipt; producer age unavailable",
            "capabilities": {
                "observation": "supported",
                "actuation": "unavailable",
                "apu_draw": "unavailable",
                "physical_input_latency": "unavailable",
                "visual_quality": "unavailable",
                "present_interval": "unavailable",
            },
            "limitation": "Correlated hypotheses; scene changes and producer age are not measured. No Autopilot control or learning.",
        }
