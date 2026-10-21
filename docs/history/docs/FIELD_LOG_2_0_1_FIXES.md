# Control conflicts from 20261012-003441

Source: [original diagnostics ZIP](https://github.com/wavessevaw/GFG-Extreme/blob/db76715a9deb6c068cdf0dced4f5a412d2c87074/docs/field-logs/20261012-003441/GFG-Extreme-log-20261012-003441.zip). Recorded version: 2.0.1; approximately 15 minutes; Balanced followed by Autopilot Auto at a 90 FPS goal.

The recording contained 246 `baseline-overlaps-transition` shading skips and 56 `resource-controller-busy` skips. Emergency TDP reached 20 W. After Act injection started, 223 active snapshots held nearly 90 output FPS at that same 20 W cap. Spatial scaling advertised a smaller source while the game kept 1280x800.

## Separate evidence ownership

`_evaluation_after_seq` consumes non-overlapping Budget windows; it cannot identify an actual settings transition. The new `_autopilot_transition_seq` advances on renderer writes, applied TDP, confirmed point acceptance, menu resume, restoration and session invalidation. Identical overlay reconciliation does not advance it. Resource baselines are filtered after the transition, leaving normal Budget evaluation independent.

The output-goal policy separately filters after its own last consumed sample sequence. Waiting to collect a complete new goal window preserves earlier misses; actual telemetry loss or a Steam menu interrupts them. A changed display goal remains effective during collection.

## Emergency recovery and Act

Outside Extreme, an emergency cap exceeds the controller's normal ceiling. Ordinary HOLD and proposed resource trials yield to existing Budget recovery while real safety pauses and in-progress resource trials retain priority. Recovery still needs fresh healthy windows, the usual dwell and failed-floor backoff. A failed lower-cap probe restores known-good watts.

Act cannot begin at an emergency cap and yields an existing injected overlay if it reaches that state. At normal power it periodically gives Budget a 120-second research interval after five minutes. Research itself does not count as output starvation and does not lock out Act. Extreme remains driven by its user-selected ceiling.

## Scale refusal

The exact renderer reason `application-extent-override-no-source-presentation-split` blocks scaled rungs even before a trial. Merely reporting an inactive scaler at native resolution does not establish permanent game incompatibility. A consumed refusal event is not reapplied immediately after the user resets learned game data.

Fourteen cases in `tests/test_field_log_2_0_1.py` cover these paths. Existing menu, stale telemetry, scale acknowledgement, capacity, restoration and mode-objective tests remain applicable. Physical Deck validation of 2.0.3 is still required; the original recording does not measure the new build's savings.
