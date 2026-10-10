# Autopilot handoff for merge

Date: 2026-10-10. Tip: `autopilot/merge-ready-20261010`.
Base: `main` at `9c94cea` (release 1.6.9). Main had no newer commits at handoff.
This document is the merge instruction. Do not merge the intermediate draft PRs.

## Merge this, and nothing else

Open one draft pull request from this branch to `main`. Intermediate drafts
#98 and #102–#113 are the same history stacked on each other. Merging any of
them alone, or merging them out of order, duplicates commits or drops the
later fixes. Do not merge `handoff/gfg-open-field-logs-20261009` (data only).

Do not bump the plugin version, tag a release, or publish a Decky ZIP.
The owner has not accepted a release. Device verification is `NOT_TESTED`.

## What stays off after merge

Both development switches are set false in `GovernorService.__init__` and
nothing in the UI turns them on:

- `_autopilot_power_enabled = False`
- `_autopilot_flow_enabled = False`

With both false, `_run_autopilot_exclusive` returns immediately. Battery,
Balanced, Quality and Extreme keep their current writers. Extreme stays a
mode in the selector. There is no Autopilot mode.

Details shows one diagnostic card, `autopilot_observation`, labeled observe
only. It reports a hypothesis, not a proven bottleneck and not a learned
result. Do not add a selector, a Start button, or a confidence interval.

## What does change for current users

Two fixes are on the normal path, not behind the flag.

1. Restore barrier. A failed power or CPU undo blocks later writers and
   profile changes until the undo is verified. This is already covered by
   the governor runtime tests.
2. Flow context change. If the tuner has moved `flow_scale` and the context
   changes, it no longer calls `reset()` and no longer writes the base
   overlay without the Saved scale. It writes the Saved scale and keeps the
   old context until the renderer ACK. Only then is the new context adopted.

## What the flag would do if someone turns it on

Do not turn it on for a user build.

- Power flag: one owned +1 W step inside the verified ceiling. The expected
  FPS gain is not invented. The verdict cannot be ACCEPT, and memory does
  not store it. Undo writes the pre-trial cap through `set_tdp_w` and does
  not call `restore_if_owned`, so the Governor lease stays.
- Flow flag: the existing tuner may run, but only in the one shared slot.
  Stopping it writes the Saved scale and waits for the renderer ACK before
  the slot is released.
- Both flags together: no write, reason `two-tools-requested`.
- A pending restore blocks the next trial.

## Checks before pressing merge

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

That is the CI command in `.github/workflows/ci.yml`. On 2026-10-10 the
Autopilot suite was 80 tests and `test_governor_runtime` was 283, both
passing on this tip. A sandbox cannot `chown` and may fail
`test_governor_wrapper_diagnostics` for that reason; CI on GitHub is the
authority for that one test.

Confirm the diff against `main` does not change the mode list, the version
in `plugin.json`, or the default of either Autopilot flag.

## Do not do this in the merge

- Do not replace Extreme.
- Do not enable either flag in the default build.
- Do not record an Autopilot lesson. No trial here has a confidence interval,
  and `learned` stays false.
- Do not treat output near 90 as smoothness. The 8–9 October field logs show
  output near 90 while real frames stayed near 30 and Open was in
  passthrough. That is a separate renderer problem. It is not a reason to
  change this merge and not a reason to add watts.
- Do not ask the owner for another Deck log in order to finish this merge.
