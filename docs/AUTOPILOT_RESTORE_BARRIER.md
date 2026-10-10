# C2 prerequisite: explicit actuator restore barrier

A failed TDP restore previously could be followed by DISABLED or new profile
planning. CPU restore returns whether anything was written, so False alone is
not an error: check ownership and restore_pending instead.

This scoped change propagates failed/unverified power and CPU restoration into
RESTORE_PENDING, keeps retrying with the existing rollback cooldown, and blocks
new operating-point, TDP, flow and split work during that barrier. Normal
external takeover is complete: restore_if_owned retains its ownership checks
and no external setting is overwritten. Stop/shutdown status retains failures.
The existing successful Battery/Balanced/Quality and Extreme replan paths stay
in place; the Extreme ceiling is retained during a successful normal replan.

No new actuator interface, sysfs writer, mode migration or release is added.
This fixes a lifecycle prerequisite; it does not connect the Autopilot policy or
experiment engine. Renderer restore ACK and durable power crash recovery remain
separate integration gates. Overlay failure retains its existing status, but now blocks profile transitions
and new optimization until the original profile is restored.

Validation: fault-injected real Governor lifecycle tests, temporary CPU sysfs
tree, unchanged full repository CI. The tests are SIMULATED, not DEVICE-VERIFIED.
Check the associated PR for exact CI commit/results. Hardware: NOT_TESTED.
