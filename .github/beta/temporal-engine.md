# GFG Extreme 2.1.2-te.8 — generator correctness and frame cost

Experimental pre-release based on te.7. This release fixes generation failures and cost accounting; it does not claim measured 90 FPS or battery improvements on a Steam Deck.

## What changed

- **Bounded waits actually stay bounded.** Readiness uses one deadline across the CPU fit worker and GPU fences. Nonblocking submission no longer secretly drains the worker. A delayed-source regression test verifies timely return and later correct completion.
- **No fake completed frames after a submission failure.** The worker propagates its error instead of treating a cleanup fence as finished generation.
- **Cost includes the missing waits.** Diagnostics now show CPU fit, analysis-to-first-output and analysis-to-last-output spans, missed pair intervals and the actual LMC GPU-share budget. The unrelated tile cap of 2 ms is no longer presented as LMC's cap.
- **Overload no longer means 120 repeated pairs.** LMC checks GPU cost and full-pair readiness, reacts in milliseconds rather than frame counts, tries cheaper tiers first and limits its final repeat fallback to one pair before measuring again. The submitted hold is correctly recorded.
- **Fewer false motion vectors on coloured repeated textures.** Four coarse chroma probes reject gross colour aliases; a deadband preserves small reflection/lighting changes. Finest search stays unchanged. Full-resolution composition also checks its own source bounds.
- **Less unnecessary work.** CPU fitting prunes hypotheses that cannot win and skips zero matrix products. Field search stops where the remaining candidates cannot beat the current match. These changes do not lower the fitting thresholds.
- **The requested goal remains visible.** Experimental Autopilot keeps the supported display target (90 on a 90 Hz OLED configuration) instead of silently lowering it to 45. An unmet target remains an unmet target; power, thermal and display limits still apply.

GFG Shell remains the same 0.3.0 bundle as te.7.

## Evidence versus te.7

Local backend: **1258 tests, one skipped**. Native engine: **168 checks, zero failures**. Renderer: **50 CTest tests**, plus image/integration checks. Frontend: **117 screens**. CPU fitting produced **96 bit-identical model comparisons**; coherent camera/plane cases took roughly **25–31% less host CPU time**, while the noise-only case was about 6% slower.

Three counterbalanced runs on the existing 1280×800 Godot sword/walk/specular scenes showed approximately **8–13% lower GPU-stage timestamp spans** and **28–41% lower field-pass spans** on software Vulkan. Image error on those short segments stayed close to te.7 (mean FLIP changes −0.31%, −0.23%, +0.22%). These are CPU Vulkan results, **not Deck GPU measurements**.

Special colour-alias fixtures improved substantially, but the analytic thin-post case regressed by about **3%**. Every result, including regressions and timing outliers, is retained in [the comparison report](https://github.com/wavessevaw/GFG-Extreme/blob/v2.1.2-te.8/docs/TEMPORAL_ENGINE_TE8.md). This is a hardware-trial build, not a claim that every game now looks better or reaches 90 FPS.

![Synthetic colour-alias regression fixture](https://raw.githubusercontent.com/wavessevaw/GFG-Extreme/v2.1.2-te.8/docs/img/te8-colour-alias.png)

## Install and compare

Install **GFG-Extreme-v2_1_2-te_8.zip** through Decky, then **Settings → System → Update engine** and restart the game through `/home/deck/.local/bin/gfg %command%`. The bundled renderer identifies as `4.0.0-gfg.fusion.4-te.8` and TE as `0.2.4-exp`.

Use the same scene and settings for **Off → Experimental → Off** (at least three minutes each after warmup). Keep the FPS target, mode, power settings, scaling and camera route fixed. Record a log and inspect real/output FPS, frame-time tails, new ready/CPU metrics, tier changes and holds. Off uses the regular generator. The full external-semaphore import path and physical display delivery still require device validation.

SHA-256: `<sha256>` — also see **SHA256SUMS.txt**.
