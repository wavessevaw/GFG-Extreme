# Governor stable-floor eligibility experiment

Status before execution: EXPERIMENTAL; no Stable approval.

The reproduction test `test_cooldown_does_not_hide_an_untried_watt` fails on main product code: after the failed 13 W probe and restoration to 15 W, no 14 W probe occurs. Existing fake-actuator cooldown coverage uses a low draw value, which triggers the lighter-scene path and does not exercise the binding-power stable lock.

Hypothesis: Autopilot and Battery, which already use one-watt probes near a failed level, may lock only within one probe step of that failed level. The existing 2.5 W proximity is too wide for those modes. Balanced keeps its existing margin; Quality keeps its no-probe behavior. The cooldown duration, backoff and ownership rules are unchanged. This differs from the rejected high-TDP-only hypothesis: eligibility follows the controller's probe resolution, including below 14.5 W and Battery.

Predeclared checks: the reproduction must pass while enforcing at least 30 seconds before the next probe, exactly one subsequent down probe, a stable 14 W limit, and restoration on stop. Run all unit tests, all sandbox scenarios and stress with seeds 1–30. Do not alter existing assertions or thresholds. Preserve failures. Compare the existing 20-case matched-point matrix against both stored historical and current-main reports, retaining every seed and both Auto and fixed-x3 arms. Report modeled session energy, source rate, below-27.9-fps seconds and TDP writes individually; do not trade a lost source frame for lower energy or treat changed caps as equivalent work. Any worsening blocks an optimization claim and requires separate investigation. No numeric acceptance allowance is introduced. Frame pacing, quality, latency and hardware energy remain UNVERIFIED regardless of model results.

Risks include additional probes in Battery/Autopilot, temporary shortfalls, energy overhead of retained cooldown, interaction with remembered points and more writes. This experiment cannot certify the installer, engine integration, historical scenario changes or the unfinished candidate. No merge or release is authorized.
