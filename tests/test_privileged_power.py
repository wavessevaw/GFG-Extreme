import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin import privileged_power  # noqa: E402
from gfg_plugin.governor_power import SteamDeckPowerActuator  # noqa: E402


class PrivilegedPowerTests(unittest.TestCase):
    def test_only_hwmon_power_caps_are_allowed(self):
        ok = "/sys/devices/pci0000:00/0000:00:08.1/0000:04:00.0/hwmon/hwmon5/power1_cap"
        self.assertEqual(privileged_power.allowed_cap_path(ok), ok)
        for bad in ("/etc/shadow", "/sys/devices/x/hwmon/hwmon5/power1_cap_max",
                    "/sys/devices/x/hwmon/hwmon5/../../../../etc/passwd", "/tmp/power1_cap"):
            self.assertIsNone(privileged_power.allowed_cap_path(bad), bad)

    def test_helper_refuses_anything_but_caps(self):
        helper = privileged_power.spawn_helper()
        try:
            with tempfile.TemporaryDirectory() as temp:
                target = Path(temp) / "power1_cap"
                target.write_text("1\n")
                with self.assertRaisesRegex(OSError, "path-not-allowed"):
                    helper.write(target, 5_000_000)
                self.assertEqual(target.read_text(), "1\n")
            with self.assertRaisesRegex(OSError, "value-out-of-range"):
                helper.write(Path("/sys/devices/x/hwmon/hwmon0/power1_cap"), 0)
        finally:
            helper.close()

    def test_silent_helper_times_out_instead_of_blocking(self):
        # review 1.1.x: os.read without a timeout blocked the Governor loop on a stuck helper.
        req_r, req_w = os.pipe()
        rep_r, rep_w = os.pipe()
        pid = os.fork()
        if pid == 0:  # a helper that reads requests and never answers
            try:
                os.close(req_w); os.close(rep_r)
                while os.read(req_r, 4096):
                    pass
            finally:
                os._exit(0)
        os.close(req_r)
        writer = privileged_power.PrivilegedCapWriter(req_w, rep_r, pid)
        writer.REPLY_TIMEOUT_S = 0.2
        import time
        started = time.monotonic()
        with self.assertRaisesRegex(OSError, "did not answer"):
            writer.write(Path("/sys/devices/x/hwmon/hwmon0/power1_cap"), 5_000_000)
        self.assertLess(time.monotonic() - started, 2.0)
        with self.assertRaises(privileged_power.HelperTimeout):  # distinct: the write may still land
            writer.write(Path("/sys/devices/x/hwmon/hwmon0/power1_cap"), 5_000_000)
        os.write(rep_w, b"ok\n")                 # a late reply to the timed-out request ...
        with self.assertRaisesRegex(OSError, "did not answer"):
            writer.write(Path("/sys/devices/x/hwmon/hwmon0/power1_cap"), 5_000_000)  # ... is not taken for this one
        os.close(rep_w)
        writer.close()                           # EOF ends the helper: reaped
        with self.assertRaises(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)

    def test_close_kills_a_helper_that_does_not_exit(self):
        import signal
        import time
        req_r, req_w = os.pipe()
        rep_r, rep_w = os.pipe()
        pid = os.fork()
        if pid == 0:  # stuck: ignores EOF on its pipe
            try:
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                while True:
                    time.sleep(1)
            finally:
                os._exit(0)
        os.close(req_r); os.close(rep_w)
        writer = privileged_power.PrivilegedCapWriter(req_w, rep_r, pid)
        writer.CLOSE_TIMEOUT_S = 0.2
        started = time.monotonic()
        writer.close()
        self.assertLess(time.monotonic() - started, 3.0, "bounded, not a blocking waitpid")
        with self.assertRaises(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)

    def test_not_in_decky_or_not_root_never_drops(self):
        saved = os.environ.pop("DECKY_PLUGIN_DIR", None)
        try:
            self.assertFalse(privileged_power.start_and_drop_privileges("/home/deck"))
        finally:
            if saved is not None:
                os.environ["DECKY_PLUGIN_DIR"] = saved
        self.assertIsNone(privileged_power.writer())

    def test_actuator_writes_through_helper(self):
        writes = []

        class Helper:
            def write(self, path, value):
                writes.append((Path(path).name, value))
                Path(path).write_text(f"{value}\n")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            h = root / "hwmon" / "hwmon0"; h.mkdir(parents=True)
            for name, value in (("power1_label", "fastPPT"), ("power2_label", "slowPPT"),
                                ("power1_cap", 18000000), ("power2_cap", 15000000)):
                (h / name).write_text(f"{value}\n")
            orig = privileged_power.allowed_cap_path
            privileged_power.allowed_cap_path = lambda p: p
            import gfg_plugin.governor_power as gp
            gp_orig = gp.allowed_cap_path
            gp.allowed_cap_path = lambda p: p
            try:
                actuator = SteamDeckPowerActuator(drm_root=root / "drm", hwmon_root=root / "hwmon",
                                                  access=lambda p, m: False, helper=lambda: Helper())
                self.assertTrue(actuator.discover()["available"])
                actuator.claim()
                self.assertTrue(actuator.set_tdp_w(10)["success"])
            finally:
                privileged_power.allowed_cap_path = orig
                gp.allowed_cap_path = gp_orig
            self.assertEqual(writes, [("power2_cap", 10000000), ("power1_cap", 12000000)])

    @unittest.skipUnless(os.geteuid() == 0, "needs root, like Decky's root flag")
    def test_drop_keeps_only_the_helper_as_root(self):
        import subprocess
        import textwrap
        with tempfile.TemporaryDirectory() as temp:
            os.chmod(temp, 0o755)
            home = Path(temp) / "home"; home.mkdir()
            os.chown(home, 65534, 65534)
            code = textwrap.dedent(f"""
                import os, sys
                sys.path.insert(0, {str(ROOT / 'py_modules')!r})
                from gfg_plugin import privileged_power as pp
                assert pp.start_and_drop_privileges({str(home)!r})
                helper = pp.writer()
                uid = [l for l in open(f"/proc/{{helper.pid}}/status") if l.startswith("Uid:")][0].split()[1]
                print(os.getuid(), os.geteuid(), os.environ["HOME"], uid)
                open({str(home / 'made-by-plugin')!r}, "w").close()
            """)
            env = {"PATH": os.environ["PATH"], "DECKY_PLUGIN_DIR": temp}
            out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.split(), ["65534", "65534", str(home), "0"])
            self.assertEqual((home / "made-by-plugin").stat().st_uid, 65534)


if __name__ == "__main__":
    unittest.main()
