## GFG Extreme 1.6.3: power split that always keeps its undo

### Fixed
- **Partial CPU caps restore correctly.** If one CPU policy accepted a lower clock and another failed, the undo previously depended on a cap that had not yet been committed. GFG now detects the actual changed values and restores them.
- **Recovery survives a failed recovery.** Busy or unreadable CPU policies keep their undo entries for retry. A write must read back correctly before recovery is complete; GFG does not learn its own leftover cap as your original clock limit.
- **An outside CPU change does not strand the other policies.** Your new value is preserved, while the remaining GFG-owned caps return to their original values.
- **No CPU write without its undo record.** If the recovery marker cannot be saved, the optimization is skipped. Journals keep both the planned cap and the previous value so a crash halfway through the next cap can recover both.
- **The helper preserves the current owner's clock limit.** A new ownership session rebases the original value after an external change. CPU restore is now a separate helper operation: helper shutdown cannot put a recovered old cap back.
- **SteamOS Manager checks both PPT channels.** A half-applied pair is not accepted. Whole-watt rounding never raises a fractional ceiling; GFG uses the direct pair writer when available, otherwise the lower permitted whole-watt step.
- **Exact restoration is reported honestly.** A manager-only system that cannot represent the original fractional or unequal caps reports the unsupported restore rather than claiming success at different values.

### Status and compatibility
Power Split shows a pending CPU restore and retries it before another optimization. Existing settings and profiles are preserved. Normal successful control keeps the same polling cadence; no new work is added to the frame-presentation path.

### Validation
Regression coverage includes partial writes, crashes between cap changes, failed and unverified recovery, unavailable journal storage, external changes, late helper writes, helper ownership sessions and shutdown, fractional PPT ceilings and both-channel readback. Backend, native Frame OS/HUD, frontend, HUD benchmark and archive checks run in GitHub Actions. Physical Deck validation is not claimed.

### Install
Download GFG-Extreme-v1_6_3.zip and install it through Decky Loader (Install from zip) over your existing installation.

### Verify your download
SHA-256: `<sha256>` (also in SHA256SUMS.txt).
