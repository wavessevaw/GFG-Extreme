# GFG Extreme code audit — 2026-10-07

Audit target: `main` at `116cd6a036ac67919905476bc4c920d9fbb4a0a6` (Governor v0.0.8).

Scope reviewed:
- release/build workflow
- packaging metadata
- Governor lifecycle and live overlay path
- TDP control / privileged helper
- frontend RPC behavior
- tests and known limitations
- recent PR/release history

This is an audit report only. No production code was changed in this branch.

## Executive summary

No P0 issue was found in the inspected paths. The largest current risk is the release pipeline: it can skip tests entirely for commits that keep an already-tagged version, and it does not independently rebuild/test the frontend before packaging the committed `dist/index.js`.

Runtime code has much better defensive coverage than earlier releases, but there are still several failure modes that can become silent or hang indefinitely.

## Findings

### P1 — Release workflow can skip all validation after a version tag exists

File: `.github/workflows/release.yml`

The workflow computes a Governor tag from `package.json`. If that tag already exists, almost every meaningful step is gated by:

```
if: steps.version.outputs.exists == 'false'
```

That condition controls:
- Python setup
- backend tests
- payload retrieval
- zip build
- release publishing

Consequence: after `v0.0.8-governor` exists, a later fix merged into `main` while `package.json` is still `0.0.8` can pass the workflow without running the test suite at all.

Recommended fix:
1. Split CI from release publishing.
2. Always run generated-config checks, backend tests, frontend build and frontend smoke on every PR and every push to `main`.
3. Gate only the release/publish job on tag absence.
4. Add a required branch check so merges cannot bypass the validation job.

Suggested structure:
- `ci.yml`: PR + push, always runs validation.
- `release.yml`: depends on the same validation job and publishes only when the tag does not exist.

### P1 — Release does not rebuild or test the frontend before packaging

Files:
- `.github/workflows/release.yml`
- `scripts/build_release.sh`
- `frontend/build.mjs`
- `dist/index.js`

The release workflow runs backend tests only. It does not:
- install Node dependencies,
- run `npm run build`,
- verify that regenerated `dist/index.js` matches the committed bundle,
- run `npm run test:frontend`.

`scripts/build_release.sh` archives the repository as-is, so the shipping frontend is the committed `dist/index.js`.

Consequence: `frontend/src/app.js` can be correct while `dist/index.js` is stale, or the inverse. A release can be green while shipping a frontend bundle never rebuilt in CI.

Recommended fix:
- run `npm ci`
- run `npm run build`
- fail if `git diff --exit-code -- dist/index.js` is non-zero
- run `npm run test:frontend`
- optionally run `node --check dist/index.js` as an additional syntax check, not as a substitute for the build/smoke test.

### P2 — Privileged TDP helper client can block indefinitely

File: `py_modules/gfg_plugin/privileged_power.py`

`PrivilegedCapWriter.write()` performs blocking `os.write` / `os.read` calls on pipes with no timeout. The read loop waits until a newline arrives.

`PrivilegedCapWriter.close()` also performs a blocking `os.waitpid(self.pid, 0)` with no timeout.

Consequence: if the root helper remains alive but wedges during a sysfs operation or otherwise stops replying, a worker thread can block forever. Shutdown can also hang waiting for the helper.

This contrasts with `steamos_tdp.py`, where subprocess operations explicitly use a 4-second timeout.

Recommended fix:
- make request/reply FDs nonblocking or poll/select them with a bounded deadline;
- return a typed timeout error to the Governor;
- on close, wait with a deadline, then terminate/kill the helper if needed;
- add failure-injection tests for “helper alive but never replies”.

### P2 — Frontend profile edits silently swallow RPC failures

File: `frontend/src/app.js`

Current pattern in `Content`:

```js
const patch = async (c) => {
  setCfg({ ...(cfg || {}), ...c });
  try { await rpc.patch(profile, c); } catch (e) {}
  loadCfg(profile);
};
```

The UI performs an optimistic update, catches the RPC exception, discards it, then reloads configuration.

Consequence: a rejected write, backend exception, permission problem, or transport failure can appear to the user as a control briefly changing and reverting with no explanation. This is especially bad for a tool whose current debugging story already depends heavily on diagnostics.

Recommended fix:
- inspect the RPC response for `success === false`;
- surface a visible error/banner;
- only keep the optimistic value if the backend confirms it;
- record the failed action in the activity journal.

### P2 — Runtime status still advertises obsolete relaunch behavior

File: `py_modules/gfg_plugin/governor_service.py`

`_base_status()["limitations"]` still includes:

> a game must be (re)launched after Governor is enabled to use the overlay and diagnostics

That contradicts the v0.0.8 live-attach implementation and release notes.

The frontend renders `s.limitations` in the Governor page, so this is not only stale documentation. It can be presented as live product status.

Recommended fix:
replace the limitation with the actual v0.0.8 boundary:
- managed games launched with the current wrapper can attach Governor live;
- process-static FG provisioning and Scaling Engine changes still require relaunch;
- games launched before v0.0.8 / without the GFG launch command / while the plugin was unavailable may require one relaunch.

Add a regression test asserting the public status limitation text does not contradict live-attach capability.

### P2 — Release validation is not a required PR check

Observed on the current head: the repository has a successful Release workflow run, but the connector reports no commit status contexts for the head. The repository metadata also does not indicate an independent CI workflow.

Risk: release testing is coupled to a post-merge push workflow instead of being a pre-merge quality gate.

Recommended fix:
- add a dedicated PR validation workflow;
- make it required on `main`;
- validate backend, frontend, generated artifacts and packaging metadata before merge.

### P3 — Project metadata still points users to upstream MAKO

Files:
- `package.json`
- `plugin.json`

Examples:
- `package.json.repository.url` points to `eugeniosegala/MAKO`
- `bugs.url` points to MAKO issues
- `homepage` points to MAKO
- author metadata is still upstream MAKO
- `plugin.json.author` is still upstream MAKO

The codebase clearly preserves MAKO lineage and licensing, which is good, but package support/discovery metadata should identify the current GFG Extreme repository while retaining upstream attribution in `THIRD_PARTY_NOTICES.md`, README and provenance files.

Consequence: users and automated tooling can report GFG-specific bugs to the wrong repository.

Recommended fix:
- repository: `https://github.com/wavessevaw/GFG-Extreme`
- bugs: current repository issues
- homepage: current repository README/releases
- keep explicit “based on / derived from MAKO” attribution separately.

### P3 — Known-limitations document contains version-stale items

File: `docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md`

The file includes statements tied to older planned releases, including restart/live-attach assumptions that changed in v0.0.8 and references such as a full Guard being planned for earlier version milestones.

Consequence: agents and humans can make wrong implementation decisions from a file that appears authoritative.

Recommended fix:
- give the document a “verified against version/commit” header;
- remove resolved limitations;
- separate “confirmed limitation”, “unverified hardware assumption”, and “future work”.

## Positive observations

The recent runtime work has several good properties worth preserving:

- Saved profile values and runtime Governor overlays are separated.
- Overlay writes use ownership/lease semantics instead of blindly editing Saved state.
- Recent v0.0.8 changes attempt to keep standby overlays synchronized without rewriting active in-flight point overlays.
- Diagnostics and event journals are size-bounded.
- TDP manager operations avoid shell invocation and use explicit subprocess timeouts.
- The root helper allowlists resolved `/sys/devices/.../hwmon/.../power*_cap` paths and integer ranges.
- There is meaningful unit/replay coverage around Governor decisions, telemetry, overlays, TDP and wrapper behavior.

## Hardware-validation gap

The release notes correctly state that the current implementation has not yet completed real Steam Deck hardware validation for the Governor integration. In particular, the following remain important to verify on-device:

- real cadence and reliability of renderer `fixed-plan` telemetry;
- native/x1 evidence when FG is off;
- live MangoHud config refresh behavior across real games;
- live overlay reconfiguration behavior in the Renderer;
- SteamOS manager + direct hwmon fallback interaction on OLED/LCD;
- Flatpak wrapper/overlay access;
- Dock transitions and display ownership.

This is not itself a code defect, but it should block calling the Governor production-stable.

## Recommended order for the next agent

1. Fix CI first.
2. Add frontend build reproducibility check.
3. Add timeout handling to the privileged TDP helper.
4. Stop swallowing frontend RPC errors.
5. Correct live status / known-limitation text.
6. Fix repository metadata.
7. Only then continue feature work toward v0.0.9/v0.0.10.

Reason: adding more Governor behavior before the repository has a reliable pre-merge validation gate increases the chance of shipping a regression that the current workflow can literally skip testing.

## Audit provenance

Inspected repository:
- `wavessevaw/GFG-Extreme`
- base branch: `main`
- commit: `116cd6a036ac67919905476bc4c920d9fbb4a0a6`
- current package version: `4.0.0-gfg.4-governor.0.0.8`
- current pre-release tag observed: `v0.0.8-governor`

Primary inspected paths:
- `.github/workflows/release.yml`
- `scripts/build_release.sh`
- `package.json`
- `plugin.json`
- `frontend/build.mjs`
- `frontend/src/app.js`
- `py_modules/gfg_plugin/plugin.py`
- `py_modules/gfg_plugin/governor_service.py`
- `py_modules/gfg_plugin/governor_overlay.py`
- `py_modules/gfg_plugin/configuration.py`
- `py_modules/gfg_plugin/privileged_power.py`
- `py_modules/gfg_plugin/steamos_tdp.py`
- `py_modules/gfg_plugin/wrapper_generation.py`
- `tests/*`
- recent PRs/releases through Governor v0.0.8
