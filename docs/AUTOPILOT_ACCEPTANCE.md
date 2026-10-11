# Autopilot 2.0.1 acceptance

Current maintenance candidate: PR #120, based on official 2.0.0. This document
supersedes the earlier experimental 2.0.1/2.0.2 reports: those package hashes and
disabled-clock statements do not describe this release. See
`RELEASE_AUDIT_2_0_1.md` for the diagnostics evidence and its limits.

All strategies remain available through their existing settings. Autopilot
selects appropriate actions from measurements; it does not enable every actuator
at once. A skipped incompatible action is not a successful hardware trial.

| Mode or tool | Activation and behavior | Software checks |
| --- | --- | --- |
| Auto | Uses the confirmed FPS goal; searches power points when justified and holds an efficient stable point. Stable CPU/GPU bottlenecks can reach clock/VRS trials. | `PlannerTests`, `RuntimeAdmissionTests` |
| Battery | Searches a lower power point at stable cadence; retries a lower FPS goal only on independent windows, with guarded recovery to the display goal. | `HoldAndTargetTests`, `GoalAndPauseTests`, preference-switch regression |
| Smoothness | Holds good real-frame timing; uses Balanced Governor behavior for point selection when recovery is needed. | `ColorAndModeRegressionTests`, preference-switch regression |
| GPU Clock | Production writes are enabled when SteamOSManager/QAM is available. Starts one step below observed MHz, stages the frequency before enabling Manual, then verifies gain. External manual settings win. | `SteamOSGpuTests`, `ClockRecoveryTests`, runtime admission, rollback and restart tests |
| Half Rate Shading | Existing per-game opt-in is required. Trials need confirmed stable gameplay and an uninterrupted baseline. Missing Steam VRS interface falls back without claiming an applied action. | `HalfRateTests`, runtime admission and all 15 recorded skip cases |
| Flow | Existing renderer capability and measurement gates remain active. No clock/VRS experiment starts while a Flow trial is busy. | `FlowRuntimeTests`, resource-controller exclusion regression |
| CPU power split | Existing sensor and bottleneck gates apply. Pending CPU restoration excludes a GPU/VRS trial; pending GPU/VRS restoration pauses other resource changes. | `BudgetRuntimeTests`, global restoration barrier regression |
| Scaling | Available only with a scale-ready launch and GPU-bound game. Ignored render extent is not retried as if effective. | `BottleneckAwareLadderTests`, budget/runtime scaling tests |
| Frame OS Observe | Computes decisions and evidence without executing Act cadence changes. | Frame OS runner and integration tests |
| Frame OS Act: Calm | Existing Act unlock, live pacer and settled Governor point are required. Calm uses the confirmed cadence. | Frame OS runner/integration and native mock-driver tests |
| Frame OS Act: Boost | Input/motion and available energy fund a higher real cadence. Failed settled bursts accumulate and back off; the adaptive point yields to Governor. | Frame OS policy/energy tests, `BurstDeliveryTests`, runtime release regression |
| Frame OS Act: Rest | Requires verified inactivity or Steam UI, then wakes on input/focus. Without renderer capacity for lower real cadence it keeps the compatible cadence. | Frame OS idle/focus/capacity tests and runtime menu regressions |
| Battery / Balanced / Quality transitions | Leaving Autopilot restores its GPU/VRS settings. Failed restoration blocks resource writes in every mode until recovered or an external override is recognized. | mode-switch restoration and restore-lock regressions |

## Release verification

The final candidate must pass Linux backend tests, native Vulkan pacer and HUD
integration on the mock driver, current frontend build and 91 smoke screens.
The main-branch release workflow separately verifies the installable ZIP,
versions, paths, renderer payload checksums and native layer payloads before
publishing. These checks exercise software paths, not a physical Steam Deck.

## Physical Deck acceptance

No Deck connection or complete raw game recording was supplied. Hardware
acceptance remains unverified; no universal 90 FPS or battery improvement is
claimed. After installing the new ZIP and restarting the game:

1. Record fresh sessions with Auto, Battery and Smoothness separately; include
   ordinary gameplay, Steam menu, resume, game exit and Stop.
2. In a CPU-bound scene, verify a GPU Clock trial actually changes measured MHz,
   retains output/real cadence, and returns to the saved Auto/manual values after
   rejection, mode change, restart and user QAM override.
3. With per-game shading opt-in, verify 2x2 is actually applied only in confirmed
   gameplay; compare text and fine detail visually, then disable the opt-in and
   verify 1x1 is restored. FPS alone cannot prove acceptable image quality.
4. Test Frame OS Observe, then unlocked Act. Confirm Calm, funded Boost and
   verified Rest from actual delivered cadence/power, including wake-up and
   ineffective-boost backoff. A label change alone is insufficient evidence.
5. Collect the full session recording and renderer telemetry, not only a summary.
   A mode passes device acceptance only when its applied settings, measured
   delivery and restoration are all recorded without unresolved errors.
