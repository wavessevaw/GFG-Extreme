# Recorded virtual Deck baseline

Source `92b557f678d118ae97948673c26e2498b7a28467`, Python 3.12.14, Windows 11 build 26200, `PYTHONUTF8=1`, recorded 2026-10-30. The checkout was clean when the commands ran. No real Steam Deck was used.

* `sandbox.json`: `python -m sandbox.run --json ... --report ...`, 39 scenarios and 136 checks passed. SHA256 `06c6a4e8a2903a0157caf35b963dc524ea6554b220bd2472f364f4732aed25ad`.
* `stress.json`: `python -m sandbox.stress --seeds 30 --json ...`, seeds 1–30 plus nine named runs passed. SHA256 `a926da438a22048174b669eb936079be2403e7d03c3b978fa76e335bcf1190eb`.

These are saved observations, not a guarantee about other hosts or the engine. See `../BASELINE_3_2_2.md` and `../SANDBOX_REPORT.md` for scope and limitations. The hashes detect accidental alteration only if reviewed independently; they do not enforce repository protection.

`python tools/compare_sandbox.py baseline.json stable.json candidate.json --output comparison.json` checks names and outcomes across three saved runs. It exits 1 on a missing scenario/check or any failed check; an otherwise clean comparison remains UNVERIFIED. Identical labels do not prove the same predicate or thresholds. A quantitative comparison requires a separately specified method and measurements; this script does not compare performance or images. CI compares the recorded baseline to its current run and uses that same run as the third input; it does not claim an independent latest-stable comparison.

At `94739b1f462ff1bd4411d8c8514bcde4d2dcb222`, the two checks for low-battery points and two for normalization of fixed x3/off have been replaced in `battery_drains_autopilot` and `fixed_x3_too_heavy`. The gate deliberately returns BLOCKED until the original requirements and replacements are assessed. Two additional scenarios are present. This finding does not by itself establish a runtime regression.

The same host and seeds on that current commit produced 41/41 sandbox scenarios but only 38/39 stress runs: `autopilot_heavy` reported 313 seconds at x3.75 in both 34-fps cases, above its 120-second bound, whereas the baseline passed. The stress source itself is unchanged. This is a reproducible model finding on this host, not a hardware measurement; the precise root cause and whether the criterion remains appropriate require investigation. The CI stress gate must not be weakened to hide it.
