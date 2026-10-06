# GFG Extreme interface (v0.0.14)

The interface answers four questions: what is GFG doing, is the game healthy, how much power is it using, and why. Everything else is reachable but out of the way.

## Navigation

```
Home                         target ring · Real → GFG → Output · Run/Stop · Mode (Battery/Balanced/Quality)
 ├─ (contextual) launch command       only while the game is not attached to GFG
 ├─ (contextual) Record a log         only while the Governor is paused or cannot reach the target
 ├─ Details                           decision, health (bottleneck, temperature, frametime, battery draw), rules, limits
 └─ Settings
     ├─ In-game overlay · Profile · Launch command · Frame generation backend · Scaling
     └─ Support: Diagnostics (Record log, Journal) · System (engine, Flatpak) · All settings
```

## Rules

- **Controller first.** Every action is a `Focusable` that handles `onActivate`/`onOKButton` (A button) as well as touch.
- **No silent failures.** A backend call that fails shows a banner naming the call; status polling never has more than one call in flight and times out after 10 s.
- **Contextual instead of permanent.** Help that is only useful in one situation appears in that situation.
- **Plain language.** State and reason codes are translated (`describe()` and `PAUSED_TEXT` in `frontend/src/app.js`).
- **Source** lives in `frontend/src`, `dist/index.js` is built by `npm run build`; CI fails if it is stale. `npm test` runs the backend tests and the frontend smoke test (`frontend/harness`, headless Chromium with mock Decky globals).
