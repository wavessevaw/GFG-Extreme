# Governor 2.1.3 causal recovery review

This PR contains source changes, synthetic tests and reusable offline tools only. Private diagnostic inputs, log-derived records, historical filenames and source registers are excluded. The detailed nine-document audit package is delivered separately to the repository owner. The full audit is not declared complete.

## Corrected code counterexamples

- Deep active frame generation is no longer treated as loading solely because Real FPS is below half the cap.
- Confirmed locked playback refreshes working-power memory. Entries carry cadence/scale context, expire after 900 seconds and are bounded to 128 entries.
- Fast requested power does not become last_good until two fresh healthy windows. Pending validation blocks premature stable dwell and probes.
- Severe slow economy failures may restore reachable same-context working watts without a draw sensor. Moderate failures use the exact rollback point, avoiding a heavy-scene watt jump in light play.
- Non-finite/bool draw cannot prove a binding cap. Hot APU cannot use the fast watt-increase path. Old draw is discarded on a new TDP write.
- Unreachable historical watts cannot hold the target forever. Recovery consumes and clears pre-recovery downshift evidence. A lower policy goal remains consistent while its power recovers; TargetPolicy owns upward retries.
- Existing events connect decision ids, sample boundaries and requested/applied watts. An actuator acknowledgment is explicitly not a performance result.

## Reproduction and validation

`tests/test_governor_causal_audit.py` contains 14 counterexample tests. `tools/governor_scenario_bench.py` runs 22 deterministic closed-loop plant scenarios; 3 tests cover trajectory invariants, bounded model recovery and deterministic replay. `tests/test_governor_history_audit.py` checks byte deduplication, damaged rows, unknown telemetry and evidence references using synthetic inputs.

Run the full Backend CI, Temporal Engine and Frame Fusion checks on this PR. Local results are tracked in the PR description and a subsequent validation note. No Steam Deck hardware validation or battery-life benefit is claimed.

## Open limitations

The historical source search and all requested causal detector classes are not complete. Point context is not a full scene fingerprint. Fast summaries are sliding; native loading remains heuristic. Universal per-action efficacy/rollback transactions remain future work. The plant models application and sensor delays rather than emulating SteamOS/Vulkan. Hardware QAM/clock restore, temperature and frame delivery still require device tests.

The repository owner subsequently authorized merging the verified Governor fixes and publishing software release 2.1.3. That release authorization does not turn the incomplete full audit or missing hardware validation into completed work. Diagnostic input files and private audit exports remain excluded from the public release.
