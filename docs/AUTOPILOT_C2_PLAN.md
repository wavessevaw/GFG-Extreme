# C2: one tool at a time

The coordinator names at most one of two tools.

Power cap steps one owned watt toward the verified ceiling, requires readback,
then restores. It does not keep the winner. `_autopilot_power_enabled` defaults
off.

Flow scale is not a new writer. The existing flow tuner is the only code that
may change it, and only after its own locked point and ACK gates.
`_autopilot_flow_enabled` defaults off. With no locked point it does not write.

The two flags cannot be on together. While either is on, Battery, Balanced,
Quality and Extreme writers do not run in that iteration. A busy slot rejects
the other tool.

Neither flag is a user-facing mode. Hardware: NOT_TESTED. Checks are SIMULATED.
