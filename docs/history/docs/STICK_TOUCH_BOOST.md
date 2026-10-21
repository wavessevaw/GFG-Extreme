# Short Boost and right-stick touch — stable 2.1.0

Both controls are available only in Autopilot and default on per profile. Explicit off choices are preserved. Frame OS Act is enabled by default for new Autopilot settings; compatible live layers, confirmed points, power ownership, output health and thermal guards still gate execution. Other Governor modes cancel contact, camera, action and scene contributions and publish the calm cadence.

## Input and lifetime

The existing read-only Deck hidraw relay decodes right-stick contact from byte 14 bit 7 and gyro X/Y/Z from signed offsets 30/32/34 at 2000 degrees/s full scale. See the [SDL driver](https://github.com/libsdl-org/SDL/blob/main/src/joystick/hidapi/SDL_hidapi_steamdeck.c) and [report structure](https://github.com/libsdl-org/SDL/blob/main/src/joystick/hidapi/steam/controller_structs.h). GFG does not grab input, modify Steam mappings or write feature reports. Physical gyro motion does not prove that a game maps the gyro to its camera.

Contact edges are immediate; unchanged contact has a bounded 20 Hz heartbeat. The supervisor runs at 10 Hz. Signal leases expire after 350 ms and clear on source loss. Resumed unchanged contact cannot create a new touch edge. Unsupported controllers report unavailable.

Each fresh contact requests 500 ms before stick motion. Stick deflection above the existing deadzone or gyro above 15 degrees/s can extend this contribution, but the whole burst has a hard 1.5 second limit. Release retains at most 200 ms. A resting or continuously moving held finger cannot renew Boost indefinitely. Camera/action onset has the same maximum. New camera/action input requires a 150 ms quiet rearm; another burst has a 500 ms recovery gap. Menu focus, disabling the feature and leaving Autopilot cancel intent. These are product thresholds, not measured optimal values.

The existing energy bank includes the configured 5% premium and bounds available extra watts within the user's cap. Power offset changes are reconciled at 100 ms checkpoints inside the serialized Governor wait; the power helper's own I/O latency still applies. An expired pulse cannot retain its extra power while the input loop is stale. The ready adaptive executor does not freeze power search during calm play. Resource experiments/probes suppress Boost instead of mixing their evidence with a pulse.

## Delivery evidence

The 64-present median is too slow for a 500 ms pulse. `BurstCadence` instead derives real-present cadence from fresh frame-counter and CLOCK_MONOTONIC timestamp deltas over 150–500 ms, at least four presents, within one writer, policy generation and swapchain epoch. Repeated publications, reset counters, stale telemetry and long gaps cannot qualify. This measures the forwarding cadence of real presents, not physical scanout or GPU completion.

Failure exposure accumulates across separate acknowledged bursts and backs off after three seconds of unsuccessful exposure; a burst need not sustain 45 FPS for a long interval. Long Frame OS A/B frame windows and their historical frame-gain pairs are excluded from short-Boost qualification. Response/energy experiments retain their own existing contracts. Contact, intent, submitted policy and observed cadence remain distinct in logs; no invented gain is shown.

The 2.2.0 field logs have been reviewed, and the user authorized stable publication. Automated qualification covers duration limits, rearm, held contact/motion, decoding/expiry, scopes, feature persistence, fast power rollback, short-window resets and export rotation. Physical touch/gyro mappings, delivered output continuity and comparative energy still need repeatable Deck sessions. The earlier logs proved only that long Boost attempts could be ineffective; the new short implementation does not claim a hardware speedup from those recordings.
