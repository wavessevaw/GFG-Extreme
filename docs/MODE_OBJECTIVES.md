# Battery, Balanced and Quality — 2.0.2

| Mode | Primary objective | Allowed trade-off | Protection |
| --- | --- | --- | --- |
| Battery | Lowest verified feasible TDP across compatible normal cadence/scale choices. Searches the reported device minimum, including below 6 W. | Normally at least 24 real FPS; lower cadence/scale may buy fewer watts. Emergency cadence is recovery only. | Each point needs renderer confirmation and healthy windows; failed power/cadence trials restore known-good settings and back off. Ignored caps cannot prove savings. |
| Balanced | Stable output with at least 30 real FPS, then useful image quality and power savings within the normal power range. | Starts near 45 real FPS at 90 Hz (30 at 60 Hz); can give up quality to recover cadence. | Never uses the emergency point or power range. At a power floor, periodically checks a finer ratio; heat and failed-trial cooldowns still apply. |
| Quality | Saved render resolution and the fewest generated frames that deliver the output goal. Then reduces TDP for that point. | A deeper frame ratio is allowed when a finer one fails; automatic resolution reduction is excluded from both recommendation and actual trials. | After five minutes of clean play, trial one finer ratio with the saved power budget. Keep the previous point for rollback, and retain a ten-minute failed-point cooldown. No upgrade during heat or another resource trial. |

Battery still starts with a confirmed integer cadence near 30 real FPS. Once
the local power floor is found, it can test a cheaper compatible normal point
at the known-good watts, confirm it, and continue lowering power. It does not
raise power merely to improve image quality. At the final watt floor it can
retain better image quality if it costs no extra watts. When device minimum
is unknown, the previous 6 W fallback is retained.

The stronger minimum-power goal also applies to Autopilot's Battery preference.
Other Autopilot preferences keep their existing policy. Per-game failure memory,
renderer capacity, Steam menu, stale data, mode exit and external-control guards
remain in place.

`tests/test_mode_objectives.py` includes CPU-independent toy-APU scenarios:
7 W at a 30-real comfort point versus 6 W with a legal cheaper cadence;
3 W in a sufficiently light scene on a device reporting 3 W minimum;
capacity limited to x3; ignored caps; rollback on failed economy probes;
Balanced recovery and heat; Quality resolution, cooldown, real service
activation, saved-budget retry and rollback. These are algorithm tests, not
hardware performance measurements. Full Linux CI, native Vulkan/HUD and
frontend checks are the release gate. Physical game/Deck validation remains
necessary.
