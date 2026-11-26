# GFG Extreme 3.0 Steam Deck test protocol

**Historical protocol.** For Stable 3.2.2 and later comparative qualification use
[`DECK_TEST_PROTOCOL_3_2_2.md`](DECK_TEST_PROTOCOL_3_2_2.md). The original checks below are
retained for traceability; their Custom selector instructions do not describe the 3.2.2 Dash.

Results count only from a Steam Deck run. Each item: what to do, what to send (Save report to
Desktop + Pace capture files), pass condition.

1. **Install and reboot**: Setup shows all engine checks green after the reboot.
2. **Pacing ×2 / ×3 / ×3.75** (Custom 45, 30, 24 at 90 Hz), 10 min each, Pace capture:
   P95 error ≤ 1 ms, P99 ≤ 2 ms, missed < 0.5 %.
3. **Auto / Autopilot** in a game with a heavy scene: the point steps down within 20 s and comes
   back; no conflict in the log.
4. **HDR**: one HDR10 game with generation on: no colour shift, HUD readable, pacing as in 2.
5. **Power Split** (GPU-bound game, Balanced, 15 min): `power-split` events in activity.jsonl,
   CPU caps restored after quitting (`scaling_max_freq` back to the original).
6. **GPU clock ceiling** (CPU-bound game, e.g. a strategy game, Quality, 15 min): `gpu-clock-kept`
   events; after quitting the QAM GPU clock is back to Auto (or your own manual value).
7. **Battery mode** 30 min unplugged: energy (Wh) against Balanced in the same scene.
8. **HUD**: four corners, Minimal / Standard; battery shows time left on battery and AC on charger.
9. **Dock**: the chip shows Dock; generation fills the external display's refresh.
10. **Uninstall** from Setup → Remove → reboot: stock Gamescope back.
