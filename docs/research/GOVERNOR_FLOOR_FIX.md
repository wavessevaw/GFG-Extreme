# Governor stable-floor eligibility experiment

Status before execution: EXPERIMENTAL; no Stable approval.

The reproduction test `test_cooldown_does_not_hide_an_untried_watt` fails on main product code: after the failed 13 W probe and restoration to 15 W, no 14 W probe occurs. Existing fake-actuator cooldown coverage uses a low draw value, which triggers the lighter-scene path and does not exercise the binding-power stable lock.

Hypothesis: Autopilot and Battery, which already use one-watt probes near a failed level, may lock only within one probe step of that failed level. The existing 2.5 W proximity is too wide for those modes. Balanced keeps its existing margin; Quality keeps its no-probe behavior. The cooldown duration, backoff and ownership rules are unchanged. This differs from the rejected high-TDP-only hypothesis: eligibility follows the controller's probe resolution, including below 14.5 W and Battery.

Predeclared checks: the reproduction must pass while enforcing at least 30 seconds before the next probe, exactly one subsequent down probe, a stable 14 W limit, and restoration on stop. Run all unit tests, all sandbox scenarios and stress with seeds 1–30. Do not alter existing assertions or thresholds. Preserve failures. Compare the existing 20-case matched-point matrix against both stored historical and current-main reports, retaining every seed and both Auto and fixed-x3 arms. Report modeled session energy, source rate, below-27.9-fps seconds and TDP writes individually; do not trade a lost source frame for lower energy or treat changed caps as equivalent work. Any worsening blocks an optimization claim and requires separate investigation. No numeric acceptance allowance is introduced. Frame pacing, quality, latency and hardware energy remain UNVERIFIED regardless of model results.

Risks include additional probes in Battery/Autopilot, temporary shortfalls, energy overhead of retained cooldown, interaction with remembered points and more writes. This experiment cannot certify the installer, engine integration, historical scenario changes or the unfinished candidate. No merge or release is authorized.

## Observed result: BLOCKED for acceptance

Product commit `19f86dbae9a4d8a7b36008ea58f333e87b3e3dfa` locally and GitHub commit `e6a96a7706b844ef4a88b050525ee068b8de5739` have the identical tree `063735c8e63ad8a31789ee78878bf06fe2d0a59e`. The next evidence-only commit does not change product or scenario code.

[Linux CI 41149368199](https://github.com/wavessevaw/GFG-Extreme/actions/runs/41149368199) passed 224 unit tests, all 41 current scenarios, all 39 stress runs with seeds 1–30 (including the formerly failing `autopilot_heavy`), npm ci/build, committed-dist comparison and frontend smoke. The two historical assertion/source guards still fail on pre-existing scenario changes, so the overall run is failed. No guard was weakened.

Windows results are retained separately: 224 unit tests ended with 2 failures and 11 errors involving POSIX permissions/path semantics, missing `sh` and `os.chown`. The first sandbox invocation completed scenario evaluation but could not write its Markdown report using cp1251. Repeating with `-X utf8` saved 41/41 results; local stress saved 39/39. These failures were not recast as passing tests or silently skipped.

The 20-case comparison retained all five seeds, both SteamOS limits and both arms. In all ten Auto cases the candidate has zero cap-24 seconds in the final 800 seconds; main had 307 seconds in nine cases. In all ten isolated-x3 cases the cap stays at 30 throughout that tail. Relative to main, no case adds below-27.9-fps seconds. Nine fixed-x3 cases add one TDP write while reducing modeled energy; this is explicitly a cost, not an unqualified improvement.

Relative to historical 3.2.2, modeled Auto session-energy changes range from -0.07848% to +0.13352%; fixed-x3 changes range from +0.00642% to +0.17632%. No case adds TDP writes relative to 3.2.2. One Auto case (seed 3, limit 18 W) has 51 rather than 50 seconds below 27.9 fps, exactly as on pre-fix main. The isolated-x3 arm bypasses historical profile normalization as described in `AUTOPILOT_MATCHED_POINT.md`; it is not a historical UI test. All percentages describe this deterministic model, not hardware measurement noise or an accepted tolerance.

Consequently, the targeted functional defect is corrected in this experiment, but the predeclared screen does not permit an optimization or no-regression claim. Additional probing, retained cooldown overhead and the pre-existing seed-3 difference remain visible. Keep this PR experimental and do not integrate it into a Stable candidate as an accepted fix. Investigate whether a control strategy can avoid the failed first probe without removing the cooldown or changing protected requirements; do not relax thresholds after seeing these results.

The archive `governor-floor-fix-evidence.zip` (SHA256 `190afb0b74a2b273fa622a83113a80d9a221f99a2943f0e67fd887b7785cc6c8`) preserves the candidate matrix, Windows results (including failures), Linux CI log and a SHA256 manifest linking local/GitHub source trees. Full hardware quality, latency and energy verification remains UNVERIFIED.
