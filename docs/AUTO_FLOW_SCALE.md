# Automatic flow scale

One step per confirmed context: Battery/Extreme/Balanced try Saved minus 0.1 (floors 0.65/0.60/0.70), Quality tries Saved plus 0.1 (maximum 1.0). Values already beyond the policy boundary are left alone. No model toggle or ultra-performance switch is automated.

Eligibility needs a locked generated-frame point, thirty seconds in the same context, a fresh same-context applied-flow report, known TDP, healthy temperature, fresh FPS, and no simultaneous Frame OS Act/CPU trial. Unknown telemetry opts out.

A1, B and A2 each contain at least eight fresh FPS samples spanning eight seconds, with three-second settling after each ACK. A change must be acknowledged after its request within fifteen seconds. Scene load/temperature drift, output starvation, stale telemetry, heat, mode/profile/session/point/cap changes and edits to Saved trigger a rollback. Only one attempt is made per context; no rapid rebuild loop.

Battery requires measured draw savings, Balanced requires draw/cadence benefit, Extreme requires cadence or GPU headroom with no draw increase, Quality permits a higher flow resolution within a ten-percent draw cost. B must preserve the real/output floor and present-interval p95 when available. These local windows are not an independent visual-quality or input-latency test.

Power and CPU probes cannot overlap the comparison. New power/point contexts restore Saved flow; memory learned under a temporary flow change is discarded rather than reused for the Saved profile. The diagnostics timeline records requested/confirmed flow, phase and local-window evidence separately.

Disable Automatic flow scale in Settings to retain the profile's manual value. Frame OS Act, lighter performance and ultra-performance profiles are excluded from automatic flow trials.

Freshness applies to host sensors as well as FPS. A confirmed lighter-model flag is required. If Saved flow cannot be restored and the last confirmed value is still different, probing stays paused and the Saved value is retried at fifteen-second intervals until acknowledged or the context is released.
