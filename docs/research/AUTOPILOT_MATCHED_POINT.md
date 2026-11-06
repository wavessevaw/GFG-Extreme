# Autopilot versus isolated x3 controllers

Status: **BLOCKED** for the existing Autopilot regression; hardware **UNVERIFIED**.
This is diagnostic evidence, not a proposed product change or a passed release gate.

## Reproduction

Run `tools/experiments/autopilot_matched_point.py --root <checkout> --source <commit> --output <new.json>` with Python 3.12.14. The runner checks tracked product/sandbox content and rejects dirty or untracked source, existing output, and an existing cache-isolation directory. It disables bytecode writes and redirects imports away from historical caches. Use separate processes for the two source revisions:

* Historical: `92b557f678d118ae97948673c26e2498b7a28467`.
* Current main: `94739b1f462ff1bd4411d8c8514bcde4d2dcb222`.

Before running, the script fixed five seeds (1–5), simulated capability 34 fps at 15 W, SteamOS limits 15 and 18 W, Auto and fixed x3, 1,200-second sessions, 90 Hz, battery 70%, ambient 30 C and above-x3 enabled. All 20 cases per revision are retained. Full sessions and the last 800 seconds are reported separately; startup is not silently discarded. There is no proposed acceptance tolerance or optimization claim.

3.2.2 normalizes a saved fixed-x3 setting to Auto. Therefore the fixed arm explicitly overrides the in-memory profile **after normalization**, on both revisions. It measures controller isolation and does not represent the historical settings/UI path. Auto retains the normal settings path. Both normalized and observed modes are recorded. An initial diagnostic without this override remains locally under `baseline-evidence/autopilot-matched-*.json`; its fixed arm is not a valid matched-mode comparison and is not used below.

Unlike the earlier floor experiment's pre-step hook, this runner samples energy after each engine step, so it includes the final second and does not include an initial zero sample. It also counts the engine's cap, rather than the pilot's requested point. Values such as 307 cap-seconds must not be confused with the earlier 313 requested-point-seconds. Historical raw observations are unchanged.

## Observations

In 9/10 Auto cases, main spends 307 of the final 800 seconds at cap 24; historical source spends zero. Seed 3 with an 18 W limit is the exception: neither revision spends tail time at cap 24. This is reproducible across several seeds, but is not universal even within this small model sample.

In every isolated-x3 case both revisions spend all final 800 seconds at cap 30. Main consumes more modeled session energy in 9/10 of these cases (roughly 4.59 versus 4.47 Wh); seed 3 at 15 W is approximately 4.31 Wh on both. These do not prove equivalent image quality or hardware energy performance.

The seed-1, 15 W fixed-x3 journal localizes the divergence (the virtual clock starts at 1000):

| Event | Historical | Main |
|---|---|---|
| Probe 13 W from 15 W | t=1007 | t=1007 |
| Failed probe; restore 15 W | t=1013 | t=1013 |
| Probe 14 W | t=1019 | absent |
| Declare stable | 14 W at t=1050 | 15 W at t=1044 |

Main's cooldown accumulates successful windows while `_stable_check` is called before the cooldown guard. The stable-floor distance accepts 13 W as sufficiently close to 15 W, so the later one-watt probe is never attempted. The Auto pilot subsequently interprets sustained high TDP as an expensive point. The two arms expose the same Governor divergence without relying on the Auto demotion to explain lower energy.

For this fixed case, main has 2 TDP writes versus historical 3. Session energies are 4.585186609116988 and 4.473792576016974 Wh respectively; mean source rates are 29.994217357323244 and 29.97131224873683 fps. Both have two seconds below 27.9 fps and no such seconds in the tail. Thus even the matched cap does not make every source-frame observation identical. No input latency, real presentation timing or image quality was measured.

## Evidence and next implementation gate

`autopilot-controller-evidence.zip` contains both full JSON reports, including event journals, source commits, environment, script digest and a manifest of per-file SHA256 values. Archive SHA256: `f76f30a4ed86b3abd93087743f28d99ba48a9c0cf640089558bf4361b1a43a7f`. The evidence test verifies the archive, both revisions, all cases, modes and fixed-cap tail coverage.

The earlier floor hypothesis remains rejected under its declared screen. The next implementation should address stable-lock eligibility after cooldown without removing the anti-oscillation delay, and must first declare its own comparison methodology. Keep the historical and present main comparisons separate; main's lower energy at 24 fps cannot alone justify retaining the demotion. Run all historical stress/scenario protections, scene-churn, user-limit, stale-data and ownership checks after any product change. Installer recovery and other open candidate blockers remain independent. No new Stable release is authorized by these observations.
