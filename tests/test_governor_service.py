import asyncio
import json
import logging
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "py_modules"))

from gfg_plugin.governor_service import GovernorService


class FakeConfig:
    def __init__(self, root: Path, backend="gfg"):
        self.config_dir = root
        self.runtime_state_dir = root / "runtime-state"
        self.backend = backend
    def get_current_profile_snapshot(self):
        return "Game", {"success": True, "config": {"fg_backend": self.backend}}


class FakeDisplay:
    def __init__(self, external=False): self.external = external
    def get_active_display_info(self):
        return {"success": True, "internal": not self.external, "external": self.external, "valid_rates": [60] if self.external else [90]}


class FakePower:
    def __init__(self):
        self.state = type("S", (), {"available": True, "owned": False})()
        self.values = {"available": True, "owned": False, "observed_tdp_w": 15.0, "current_tdp_w": 15.0, "ceiling_tdp_w": 15.0, "minimum_tdp_w": 3.0}
    def status(self): return dict(self.values)
    def discover(self): return self.status()
    def claim(self):
        self.state.owned = True; self.values["owned"] = True; return self.status()
    def set_tdp_w(self, value):
        self.values["observed_tdp_w"] = value; self.values["current_tdp_w"] = value
        return {"success": True, "state": self.status()}
    def verify_ownership(self): return self.status()
    def restore_if_owned(self):
        was = self.state.owned; self.state.owned = False; self.values["owned"] = False
        return {"success": True, "restored": was, "state": self.status()}


def diag(base, output):
    """Real renderer ``fixed-plan`` line (no base-FPS field; real = output / (generated_per_real + 1))."""
    ratio = max(1, round(output / base)) - 1
    return (
        "I MAKO Renderer: present diagnostics: operation=fixed-plan "
        f"generated_per_real={ratio} observed_output_fps={output} generated_presented=100 "
        "generated_skipped=0 configured_adaptive_target_fps=90 target_applies=0 display_budget_hz=90"
    )


class GovernorServiceTests(unittest.TestCase):
    def make_service(self, root, external=False, backend="gfg"):
        svc = GovernorService(FakeConfig(root, backend), FakeDisplay(external), logging.getLogger("gov-test"))
        svc.power = FakePower()
        svc._status["power"] = svc.power.status()
        return svc

    def seed(self, svc, base, output):
        for i in range(20):
            svc.observer.consume_line(diag(base, output), now=i * 0.6)
        # Service uses monotonic now; use observer's time function compatible with the synthetic timeline.
        svc.observer.time_fn = lambda: 11.5

    def test_stable_native_target_is_not_nightmare_when_ladder_exhausted(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            svc._status["target_output_fps"] = 90
            tel = {"real": {"median": 90}, "output": {"median": 90, "p5": 88}}
            self.assertEqual(svc._delivering_target(tel), "easy")
            tel = {"real": {"median": 14}, "output": {"median": 40, "p5": 30}}
            self.assertIsNone(svc._delivering_target(tel))

    def test_hud_and_effort_read_service_telemetry_shape(self):
        from gfg_plugin.governor_hud import status_line
        summary = {"real": {"median": 45}, "output": {"median": 90}, "latest": {"effective_multiplier": 2.0}}
        line = status_line({"enabled": True, "telemetry": {"snapshot": {}, "summary": summary}}, "minimal")
        self.assertEqual(line, "x2  45>90")

    def test_hud_status_file_shows_live_tdp(self):
        from gfg_plugin.governor_hud import status_path
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            svc._status["power"] = {}  # snapshot taken before discovery, as on a real start
            svc.set_enabled("Game", True)
            svc.set_hud("Game", enabled=True)
            self.seed(svc, 48, 96)
            asyncio.run(svc._iteration())
            line = status_path(Path(temp)).read_text(encoding="utf-8")
            self.assertNotIn("TDPn/a", line)
            self.assertRegex(line, r"\b\d+W\b")

    def test_hud_falls_back_to_current_tdp(self):
        from gfg_plugin.governor_hud import status_line
        line = status_line({"enabled": True, "power": {"current_tdp_w": 9.0}})
        self.assertIn("9W", line)

    def test_disabled_by_default_never_claims_power(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            self.seed(svc, 48, 96)
            asyncio.run(svc._iteration())
            self.assertEqual(svc.get_status()["state"], "DISABLED")
            self.assertFalse(svc.power.state.owned)

    def test_enabled_proven_45x2_begins_power_search_without_profile_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            svc.set_enabled("Game", True)
            self.seed(svc, 48, 96)
            asyncio.run(svc._iteration())
            status = svc.get_status()
            self.assertEqual(status["recommended_point"]["key"], "45x2")
            self.assertEqual(status["state"], "OPTIMIZE_POWER")
            self.assertTrue(svc.power.state.owned)

    def test_external_backend_is_observe_only_and_does_not_claim_tdp(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp), backend="optiscaler")
            svc.set_enabled("Game", True)
            self.seed(svc, 48, 96)
            asyncio.run(svc._iteration())
            self.assertEqual(svc.get_status()["state"], "OBSERVE_ONLY")
            self.assertFalse(svc.power.state.owned)

    def test_dock_target_is_60(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp), external=True)
            svc.set_enabled("Game", True)
            self.seed(svc, 33, 66)
            asyncio.run(svc._iteration())
            status = svc.get_status()
            self.assertEqual(status["target_output_fps"], 60)
            self.assertEqual(status["recommended_point"]["key"], "30x2")

    def test_enabling_governor_creates_diagnostics_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            marker = svc.diagnostics_marker_path
            self.assertFalse(marker.exists())
            svc.set_enabled("Game", True)
            self.assertTrue(marker.exists())
            svc.set_enabled("Game", False)
            self.assertFalse(marker.exists())

    def test_unwritable_tdp_is_reported_not_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            svc.power.state.available = False
            svc.power.state.fast_cap_path = "/sys/class/hwmon/hwmon5/power1_cap"
            svc.set_enabled("Game", True)
            self.seed(svc, 48, 96)
            asyncio.run(svc._iteration())
            self.assertEqual(svc.get_status()["state"], "OBSERVE_ONLY")
            self.assertEqual(svc.get_status()["reason"], "tdp-control-not-writable")

    def test_unavailable_telemetry_reports_specific_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            svc = self.make_service(Path(temp))
            svc.set_enabled("Game", True)
            asyncio.run(svc._iteration())
            self.assertEqual(svc.get_status()["state"], "PAUSED")
            self.assertEqual(svc.get_status()["reason"], "diagnostics-log-unavailable")
