"""Pure deterministic hypotheses, not causal proof or an actuation policy."""
from .contracts import Bottleneck as B, Config, Perception, Snapshot, number


def perceive(snapshot: Snapshot, now: float, config: Config = Config()) -> Perception:
    def result(primary=B.UNKNOWN, reason="insufficient-evidence", confidence=0.0,
               secondary=(), evidence=(), missing=(), stale=False, since=None, expiry=None):
        return Perception(primary, tuple(secondary), confidence, tuple(evidence),
                          tuple(missing), reason, now if since is None else since,
                          now if expiry is None else expiry, snapshot.session_key, stale)

    if number(now) is None:
        raise ValueError("finite monotonic time required")
    if snapshot.backend != "gfg":
        return result(reason="external-backend-observe-only", missing=("actuator-contract",))
    if snapshot.blocked_reason:
        return result(reason=snapshot.blocked_reason)
    if not snapshot.session_key or not snapshot.context:
        return result(reason="identity-unavailable", missing=("session/context",))
    age = now - snapshot.timestamp_mono
    if number(snapshot.timestamp_mono) is None or not 0 <= age <= config.max_age_s:
        return result(reason="snapshot-stale", stale=True)
    samples = snapshot.samples
    if not samples:
        return result(missing=("renderer-measurements",))
    # Reject malformed/reordered/cross-context data rather than repairing evidence.
    if any(number(s.timestamp_mono) is None or s.context != snapshot.context
           or not 0 <= now - s.timestamp_mono <= config.window_s
           or not isinstance(s.seq, int) or s.seq < 1 for s in samples):
        return result(reason="invalid-sample-context", stale=True)
    if any(b.seq <= a.seq or b.timestamp_mono <= a.timestamp_mono
           for a, b in zip(samples, samples[1:])):
        return result(reason="non-independent-samples")
    if now - samples[-1].timestamp_mono > config.max_age_s:
        return result(reason="renderer-stale", stale=True)
    if any(b.timestamp_mono - a.timestamp_mono > config.max_gap_s
           for a, b in zip(samples, samples[1:])):
        return result(reason="sample-gap-rebaseline")
    ids = tuple(f"{snapshot.session_key}:renderer:{s.seq}" for s in samples)
    if len(samples) < config.min_samples or samples[-1].timestamp_mono - samples[0].timestamp_mono < config.min_span_s:
        return result(reason="baseline-incomplete", evidence=ids, missing=("independent-window",))
    if any(number(s.real_fps) is None or number(s.output_fps) is None for s in samples):
        return result(reason="measured-fps-unavailable", evidence=ids,
                      missing=("independent-real-and-output-fps",))
    host = snapshot.host
    if host is None or number(host.timestamp_mono) is None or not 0 <= now - host.timestamp_mono <= config.max_age_s:
        return result(reason="host-stale-or-missing", evidence=ids, missing=("fresh-host",), stale=True)
    gpu, cpu = number(host.gpu_busy_pct), number(host.cpu_top_core_pct)
    if gpu is None or cpu is None or gpu > 100 or cpu > 100:
        return result(reason="host-load-unavailable", evidence=ids, missing=("cpu/gpu-load",))
    target = number(snapshot.target_fps)
    if target is None or target <= 0:
        return result(reason="target-unavailable", evidence=ids, missing=("delivery-target",))
    ids += (f"{snapshot.session_key}:host:{host.seq}",)
    expiry = min(snapshot.timestamp_mono, samples[-1].timestamp_mono, host.timestamp_mono) + config.max_age_s
    since = samples[0].timestamp_mono
    short = all(s.output_fps < target * config.delivery_ratio for s in samples)
    stable = all(s.output_fps >= target * config.delivery_ratio and s.real_fps > 0 for s in samples)
    pressure = tuple(p for p in snapshot.pressure
                     if p[2] == snapshot.context and since <= p[1] <= now
                     and now - p[1] <= config.max_age_s)
    pressure_ids = {p[0] for p in pressure}
    causes = []
    temp, limit = number(host.temp_c), number(host.thermal_limit_c)
    draw, cap = number(host.apu_draw_w), number(host.verified_cap_w)
    if temp is not None and limit is not None and limit > 0 and temp >= limit:
        causes.append(B.THERMAL_LIMITED)
    if short and len(pressure_ids) >= config.pressure_events:
        causes.append(B.FG_LIMITED)
        ids += tuple(f"{snapshot.session_key}:pressure:{p}" for p in sorted(pressure_ids))
    if short and cap is not None and cap > 0 and draw is not None and draw >= cap * config.delivery_ratio:
        causes.append(B.POWER_LIMITED)
    # A saturated component alone is not enough; sustained delivery deficit plus
    # spare capacity on the other component is necessary. These remain hypotheses.
    if short and gpu >= config.busy_pct and cpu < config.other_idle_pct:
        causes.append(B.GPU_LIMITED)
    if short and cpu >= config.busy_pct and gpu < config.other_idle_pct:
        causes.append(B.CPU_LIMITED)
    if causes:
        return result(causes[0], "correlated-limitation-hypothesis", .6, causes[1:], ids,
                      since=since, expiry=expiry)
    if stable and not pressure:
        return result(B.STABLE, "delivery-target-sustained", .7, evidence=ids,
                      since=since, expiry=expiry)
    return result(reason="cause-not-established", evidence=ids,
                  missing=("causal-evidence",), since=since, expiry=expiry)
