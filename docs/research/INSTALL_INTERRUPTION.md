# Interrupted install journal — experimental

The reproduction terminated the installer after moving the old runtime to `runtime.rollback`, before moving `runtime.new` into place. A new installer instance then refused to install because the rollback tree existed. No persistent metadata described which service files or watchdog markers belonged to the old installation.

The installer now writes a versioned JSON journal before changing runtime or service state. It stores file snapshots (including mode/owner and existing symlink representation), prior enablement and whether an old runtime existed. File contents use base64; journal data is parsed as JSON, never executed. Recovery uses a fixed list of installer paths rather than arbitrary paths from the journal. The journal is replaced atomically, its file is fsynced, and its containing directory is fsynced on POSIX.

Before the next Install or Remove operation, an uncommitted journal restores the previous runtime, files, watchdog markers and service enablement. A committed journal only finishes cleanup of obsolete runtime trees. Failed recovery retains the journal and recoverable data. A rollback tree without a journal remains protected and is not automatically deleted. POSIX flock serializes Install/Remove across processes and is released by the OS on process exit.

The tests cover the rename gap, first-install enablement, upgrade enablement with a subsequent rejected retry, repeated interruption during recovery, committed cleanup and malformed journal. A child process uses `os._exit(77)` at the rename gap, exercising a real exit without Python cleanup; the subsequent installation succeeds. The concurrency test runs on POSIX and explicitly skips on Windows, where the filesystem/systemd fixture is only a model. Existing recovery/watchdog assertions are retained.

Local initial result: 7 interruption tests passed, 1 POSIX-lock test explicitly skipped. Of 13 existing upgrade tests, 12 passed and the shell-based watchdog test could not run because Windows has no `sh`. Linux must run all tests, including flock and the real generated shell scripts, without these skips before integration.

## Limits that remain blocking

Recovery runs on the next Install/Remove operation, **not automatically in the early-boot service**. This does not prove a safe boot following every interruption, a durable complete runtime after power loss, real systemd behavior or real bind-mount interactions. Runtime/config writes are not all atomic/durably flushed; journal fsync alone is not a power-loss guarantee. The bootstrap and watchdog paths still require independent boot fault injection and hardware verification. A retained or malformed journal can intentionally stop further destructive actions and requires investigation.

Do not classify the complete installer blocker as fixed or issue a device-ready candidate on this evidence alone. This branch remains EXPERIMENTAL and must pass the candidate's full regression, including the unchanged historical guards. Rollback is a revert of this branch; Stable tags and main remain unchanged.
