"""Isolated installer failure experiment using the repository's fake system and temp root."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tests"))
from test_kedavra_install import InstallerTest

test = InstallerTest()
test.setUp()
try:
    test.inst.install()
    old = test.inst.runtime / "bin/gamescope"
    old.write_text("old-runtime")
    (test.inst.bundle / "bin/gamescope").write_text("new-runtime")
    fake = test.sys

    def fail_setcap(argv, **kw):
        if Path(argv[0]).name == "setcap":
            return 1, "injected setcap failure"
        return fake(argv, **kw)

    test.inst.run = fail_setcap
    try:
        test.inst.install()
        error = None
    except RuntimeError as exc:
        error = str(exc)
    print(json.dumps({"error": error, "installed_binary_after_failure": old.read_text(),
                      "old_runtime_preserved": old.read_text() == "old-runtime"}))
finally:
    test.tearDown()
