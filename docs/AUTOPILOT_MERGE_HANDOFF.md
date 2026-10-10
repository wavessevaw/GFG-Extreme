# Autopilot handoff for merge

Date: 2026-10-10. Tip: `autopilot/merge-ready-20261010`.
Base: `main` at `9c94cea` (release 1.6.9). Main had no newer commits at handoff.
This document is the merge instruction. Do not merge the intermediate draft PRs.

## Next version is 2.0.0

The owner marked this for the merging agent: the next published version is
**2.0.0**. Do not name it 1.6.10, 1.7.0, or any other 1.x number.

This pull request does not bump the version. `main` stays 1.6.9 until the
release commit. When that release is cut, set it with:

```sh
python3 scripts/bump_version.py 2.0.0
```

That script writes `package.json`, `package-lock.json`, `VERSION` in
`governor_service.py`, the startup line in `plugin.py`, the session recorder
label, and `CURRENT_VERSION` in `log_report.py`. Do not edit those by hand.
Do not tag or publish the ZIP until the owner asks for the release.

## HUD when Autopilot is enabled

The owner marked this for the merging agent. Do not build it in this pull
request, and do not enable either Autopilot flag to preview it.

When Autopilot is actually switched on, the ordinary HUD must be replaced by
an Autopilot HUD. The same switch applies to the ring HUD. Both have to show
the primary readings, not the current Governor layout.

The two publishers today are:

- Text HUD: `GovernorService._sync_hud` and the HudWriter path. This is the
  standard HUD.
- Rings: `hud_rings.items_for` and `GovernorService._publish_ring_hud`.
  The picture is redrawn twice a second (`RING_HUD_PERIOD_S = 0.5`).

While the flags stay false, both stay exactly as they are. A user who did not
turn Autopilot on must not see the new layout.

The Autopilot layout, on both the text HUD and the rings, leads with the
primary readings: measured real FPS, measured output FPS, and power draw
against the verified ceiling. Unavailable stays unavailable. Do not put a
planned FPS, a copied-frame count, or an uncomputed confidence interval in
those primary slots. The current decision (HOLD, TRIAL, or RESTORE) and its
reason are secondary, not a substitute for the three readings.

## Review on PR #114

The six comments on that pull request are fixed on this tip:

- A raised power cap stays through the treatment window. It is not undone on the next tick.
- Returning to the first baseline calls the scheduler ACK, so the second baseline can run.
- With a flag on, the service still polls the renderer and still follows a profile change before it skips the old mode writers.
- A repeated poll does not count as a new sample. The sample's own sequence and time are used.
- A profile switch writes the old profile's Saved flow back to that profile. It does not copy that scale onto the new profile. A stale matching receipt does not finish a restore.
- Pareto fidelity uses the fidelity tolerance, so a low-fidelity point cannot erase a safe one.

The three later comments are fixed on this tip as well:

- The flag-on path refreshes the launch probe and the display target, so a
  healthy stream does not become `launch-probe-stale` after six seconds.
- A failed Autopilot rollback retries the pre-trial cap and keeps ownership.
  It does not call `restore_if_owned` and does not put back the user's original PPT.
- A profile switch restores the old profile through the verified overlay
  release. It does not wait for a renderer ACK the new profile cannot send.

The four comments after that are fixed on this tip as well:

- A profile change verifies the pre-trial cap while power is still owned,
  and only then releases the user's original PPT.
- Turning on the second flag restores the tool that already wrote. It does
  not leave that change in place.
- A cross-profile flow change uses that same verified overlay release.
- Flags on from a cold start are documented below as not a usable controller.

Turning the flags off restores an applied watt before the ordinary Governor
runs. A flow scale put back to Saved keeps reading the renderer until that
receipt arrives, so a cached sample cannot leave the Governor blocked after
the renderer has already applied 0.8. A new game session is stored only after
the previous point is released, so an old configuration is not treated as
current for the next game. This restore path is not device-verified.

## Flags on are not a usable Autopilot

The owner asked for a sleeping merge. With either development flag set on a
fresh service, Autopilot still has no power lease and no locked point. The
flag path returns before the old planner claims either, so power stays
unowned and flow reports `no-locked-point`. That is not a controller.

Do not add a UI switch. Do not turn the flags on in a user build. A later
change that wants a real session must claim the ceiling and establish one
point itself, then prove it from a clean startup. This pull request does not.

## Merge this, and nothing else

Open one draft pull request from this branch to `main`. Intermediate drafts
#98 and #102–#113 are the same history stacked on each other. Merging any of
them alone, or merging them out of order, duplicates commits or drops the
later fixes. Do not merge `handoff/gfg-open-field-logs-20261009` (data only).

Do not tag a release or publish a Decky ZIP in this merge.
The owner has not accepted a release. Device verification is `NOT_TESTED`.
When a release is accepted, its version is 2.0.0, set only through
`scripts/bump_version.py`.

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

Confirm the diff against `main` does not change the mode list or the default
of either Autopilot flag. This merge stays on 1.6.9. The following release
is 2.0.0 and is a separate commit.

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
