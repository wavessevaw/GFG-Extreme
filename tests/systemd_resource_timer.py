"""CI integration with a real user manager and a disposable timer writing one marker."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))
from gfg_plugin.resource_backup import order_before, scheduled_backup


def ctl(*args):
    return subprocess.check_output(["systemctl", "--user", *args], text=True).strip()


def wait(check, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return
        time.sleep(.15)
    raise AssertionError("Timed out waiting for " + str(check))


def main():
    stem = "gfg-ci-scheduled-backup"
    unit, timer = stem + ".service", stem + ".timer"
    units = Path(os.environ["XDG_RUNTIME_DIR"]) / "systemd/user"
    units.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as path:
        marker = Path(path) / "completed"
        guard = None
        files = {unit: f"[Service]\nType=oneshot\nExecStart=/usr/bin/touch {marker}\n",
                 timer: f"[Timer]\nOnActiveSec=8s\nAccuracySec=50ms\nUnit={unit}\n"}
        try:
            for name, config in files.items():
                with (units / name).open("x") as f:
                    f.write(config)
            ctl("daemon-reload")
            ctl("start", timer)
            assert scheduled_backup(["--user"], {stem: ("/usr/bin/touch", "restore")}) is None
            result = scheduled_backup(["--user"], {stem: ("/usr/bin/touch", str(marker))})
            assert result == unit, result
            guard = order_before(["--user"], unit)
            wait(lambda: ctl("show", "gfg-scheduled-backup-window.service", "-P", "ActiveState") == "activating")
            wait(lambda: any(unit in line and "waiting" in line for line in ctl("list-jobs", "--no-legend").splitlines()))
            assert not marker.exists()
            guard.stdin.close()
            assert guard.wait(timeout=8) == 0
            wait(marker.exists)
            print("User manager queued the actual timer activation and completed it on pipe EOF.")
        finally:
            if guard and not guard.stdin.closed:
                guard.stdin.close()
            ctl("stop", timer, unit)
            for name in files:
                (units / name).unlink(missing_ok=True)
            ctl("daemon-reload")


if __name__ == "__main__":
    main()
