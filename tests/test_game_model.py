import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.game_model import GameModelStore, context_key, MAX_AGE_S  # noqa: E402
from gfg_plugin.governor_core import BudgetController  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_governor_budget import Game, run  # noqa: E402


class StoreTests(unittest.TestCase):
    def test_record_get_confirmations_and_persistence(self):
        with tempfile.TemporaryDirectory() as t:
            now = {"t": 1000.0}
            path = Path(t) / "models.json"
            store = GameModelStore(path, clock=lambda: now["t"])
            key = context_key("Elden Ring", 90, "budget")
            self.assertIsNone(store.get(key))
            self.assertTrue(store.record(key, "45x2", 9.0))
            self.assertFalse(store.record(key, "45x2", 9.0), "rate-limited")
            now["t"] += 61
            self.assertTrue(store.record(key, "45x2", 9.0))
            self.assertEqual(store.get(key)["confirmations"], 2)
            now["t"] += 61
            store.record(key, "36x2.5", 8.0)  # a different state restarts the count
            self.assertEqual(store.get(key)["confirmations"], 1)
            again = GameModelStore(path, clock=lambda: now["t"])
            self.assertEqual(again.get(key)["point"], "36x2.5")

    def test_old_corrupt_and_absurd_entries_are_ignored(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "m.json"
            now = {"t": 1e6}
            store = GameModelStore(path, clock=lambda: now["t"])
            store.record("a|90|budget", "45x2", 9.0)
            now["t"] += MAX_AGE_S + 1
            self.assertIsNone(store.get("a|90|budget"))
            self.assertFalse(store.record("b|90|budget", "45x2", 500.0))
            path.write_text("{not json")
            self.assertIsNone(GameModelStore(path).get("a|90|budget"))


class GameIdentityAndFailureTests(unittest.TestCase):
    def test_key_is_per_game_when_the_steam_app_id_is_known(self):
        self.assertEqual(context_key("mako", 90, "budget", "292030"), "app:292030|90|budget")
        self.assertEqual(context_key("mako", 90, "budget", ""), "mako|90|budget")
        self.assertEqual(context_key("mako", 90, "budget", "0"), "mako|90|budget")

    def test_failures_bridge_a_session_but_expire_and_never_warm_start(self):
        with tempfile.TemporaryDirectory() as t:
            now = {"t": 1000.0}
            store = GameModelStore(Path(t) / "m.json", clock=lambda: now["t"])
            key = context_key("mako", 90, "budget", "292030")
            self.assertTrue(store.record_failure(key, "33x2.75", 10.0))
            store.record_failure(key, "33x2.75", 9.0)            # keeps the highest TDP it failed at
            self.assertEqual(store.failures(key), {"33x2.75": (10.0, 0.0)})
            self.assertIsNone(store.get(key), "a failure alone is nothing to start from")
            now["t"] += 61
            store.record(key, "30x3", 10.0)
            self.assertEqual(store.get(key)["point"], "30x3")
            self.assertEqual(store.failures(key), {"33x2.75": (10.0, 61.0)})  # kept by record(), age kept
            now["t"] += GameModelStore.FAILURE_TTL_S + 1
            self.assertEqual(store.failures(key), {})


class FailureTtlAcrossReloadTests(unittest.TestCase):
    """PR #40 review: a reload must keep the remaining TTL, not start a new 15 minutes."""

    def test_reload_after_7_minutes_leaves_about_3(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 50_000.0}
            path = Path(t) / "m.json"
            key = context_key("mako", 90, "budget", "292030")
            GameModelStore(path, clock=lambda: wall["t"]).record_failure(key, "33x2.75", 10.0)
            wall["t"] += 7 * 60
            failures = GameModelStore(path, clock=lambda: wall["t"]).failures(key)   # plugin reload
            c = BudgetController(target_output_fps=90, now=7.0, min_tdp_w=3, max_tdp_w=20)
            c.load_failures(failures, 7.0)
            c.tdp = 10.0
            up = next(i for i, p in enumerate(c.points) if p.key == "33x2.75")
            self.assertFalse(c._upgrade_allowed(up, 7.0))
            self.assertFalse(c._upgrade_allowed(up, 7.0 + 2 * 60))
            self.assertTrue(c._upgrade_allowed(up, 7.0 + 3 * 60 + 1), "expired at the original 10 min")

    def test_reload_after_expiry_restores_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 50_000.0}
            path = Path(t) / "m.json"
            key = context_key("mako", 90, "budget", "292030")
            GameModelStore(path, clock=lambda: wall["t"]).record_failure(key, "33x2.75", 10.0)
            wall["t"] += GameModelStore.FAILURE_TTL_S + 1
            self.assertEqual(GameModelStore(path, clock=lambda: wall["t"]).failures(key), {})


class WarmStartTests(unittest.TestCase):
    def test_warm_start_locks_on_the_remembered_point_and_clamps_tdp(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=4.0, max_tdp_w=15.0)
        self.assertEqual(c.phase, "settle")
        key = next(p.key for p in c.points[1:] if p.base_target_fps == 36)
        self.assertTrue(c.warm_start(key, 25.0, 1.0))
        self.assertEqual((c.point.key, c.phase, c.tdp), (key, "locked", 15.0))  # never above the normal ceiling
        self.assertTrue(c.status()["warm_started"])

    def test_unknown_or_last_resort_points_do_not_warm_start(self):
        c = BudgetController(target_output_fps=90, now=0.0)
        self.assertFalse(c.warm_start("nope", 9.0, 1.0))
        self.assertFalse(c.warm_start(c.points[0].key, 9.0, 1.0))
        self.assertEqual(c.phase, "settle")

    def test_a_remembered_state_that_no_longer_holds_is_corrected_by_the_guard(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        key = next(p.key for p in c.points[1:] if p.base_target_fps == 30 and p.render_scale_pct == 100)
        self.assertTrue(c.warm_start(key, 6.0, 0.0))     # remembered from a lighter scene / level
        game = Game(4.5)                                   # 6 W gives 27 real: below the 30 real cap
        now, trace = run(c, game, 0.0, 14)
        self.assertGreater(c.tdp, 6.0, trace)
        self.assertEqual(c.phase, "locked")

    def test_a_good_remembered_state_stays_put_without_a_search(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=25)
        key = next(p.key for p in c.points[1:] if p.base_target_fps == 30 and p.render_scale_pct == 100)
        c.warm_start(key, 7.0, 0.0)
        now, trace = run(c, Game(4.5), 0.0, 2)  # before the first lower-power probe (45 s)
        self.assertEqual({t[:2] for t in trace}, {(key, 7.0)}, trace)


if __name__ == "__main__":
    unittest.main()
