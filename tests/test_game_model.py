import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "py_modules"))
from gfg_plugin.game_model import GameModelStore, context_key, floor_key, game_prefix, MAX_AGE_S  # noqa: E402
from gfg_plugin.governor_core import BudgetController  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_governor_budget import Game, run  # noqa: E402


class StoreTests(unittest.TestCase):
    def test_record_get_confirmations_and_persistence(self):
        with tempfile.TemporaryDirectory() as t:
            now = {"t": 1000.0}
            path = Path(t) / "models.json"
            store = GameModelStore(path, clock=lambda: now["t"])
            key = context_key("Sample Game", 90, "budget")
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


    def test_valid_entries_survive_corrupted_failure_and_floor_records(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "model.json"
            good = context_key("game", 90, "budget")
            floor = floor_key("game", 90)
            data = {
                "version": 1,
                "entries": {
                    good: {
                        "point": "30x3", "tdp_w": 10.0, "updated": 1000.0,
                        "confirmations": 1, "failed": {
                            "broken": ["invalid", 900],
                            "nan": [float("nan"), 900],
                            "33x2.75": [10.0, 950.0],
                        },
                    },
                    "invalid|90|budget": {
                        "point": "30x3", "tdp_w": 10.0,
                        "updated": float("nan"), "confirmations": 1,
                    },
                },
                "floors": {floor: {
                    "30x3": [9.0, 950.0, 2],
                    "bad-timestamp": [9.0, float("nan"), 1],
                    "bad-count": [9.0, 950.0, float("inf")],
                }},
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            store = GameModelStore(path, clock=lambda: 1000.0)
            self.assertEqual(store.get(good)["point"], "30x3")
            self.assertIsNone(store.get("invalid|90|budget"))
            self.assertEqual(store.failures(good), {"33x2.75": (10.0, 50.0)})
            self.assertEqual(store.floor_failures(floor), {"30x3": (9.0, 50.0, 2)})
            # A single malformed cache field cannot break normal writes.
            self.assertTrue(store.record_failure(good, "45x2", 11.0))
            self.assertIn("45x2", GameModelStore(path, clock=lambda: 1000.0).failures(good))

    def test_invalid_utf8_cache_is_not_a_startup_failure(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "models.json"
            path.write_bytes(b"\xff\xfe\x00")
            store = GameModelStore(path)
            self.assertIsNone(store.get("game|90|budget"))
            self.assertEqual(store.failures("game|90|budget"), {})


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


    def test_newly_held_point_supersedes_old_failure_for_same_point(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 2000.0}
            path = Path(t) / "models.json"
            key = context_key("mako", 90, "budget", "292030")
            store = GameModelStore(path, clock=lambda: wall["t"])
            store.record_failure(key, "30x3", 9.0)
            store.record_failure(key, "33x2.75", 10.0)
            self.assertEqual(len(store.failures(key)), 2)
            wall["t"] += 61
            store.record(key, "30x3", 9.0)
            self.assertEqual(store.failures(key), {"33x2.75": (10.0, 61.0)})
            self.assertEqual(GameModelStore(path, clock=lambda: wall["t"]).get(key)["point"], "30x3")


    def test_uncapped_success_cannot_erase_wattage_failures(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 5000.0}
            path = Path(t) / "models.json"
            key = context_key("mako", 90, "budget", "292030")
            store = GameModelStore(path, clock=lambda: wall["t"])
            self.assertTrue(store.record_failure(key, "30x3", 9.0))
            wall["t"] += 61.0
            store.record(key, "30x3", None)  # renderer held, but watts were not controlled
            self.assertEqual(store.failures(key), {"30x3": (9.0, 61.0)})
            self.assertEqual(GameModelStore(path, clock=lambda: wall["t"]).failures(key),
                             {"30x3": (9.0, 61.0)})


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


class FloorMemoryTests(unittest.TestCase):
    """review 1.1.x: a rebuilt controller (mode switch, reload) repeated a just-failed lower level."""

    def test_floor_key_is_shared_by_modes_and_forget_covers_every_target(self):
        self.assertEqual(floor_key("mako", 90, "292030"), "app:292030|90")
        self.assertEqual(floor_key("mako", 60), "mako|60")
        self.assertEqual(game_prefix("mako", "292030"), "app:292030")

    def test_reload_keeps_the_remaining_back_off(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 50_000.0}
            path = Path(t) / "m.json"
            key = floor_key("mako", 90, "292030")
            first = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
            first.tdp = 9.0
            first._note_floor_failure(0.0)
            first._note_floor_failure(1.0)                   # second failure at 9 W: back-off 240 s
            store = GameModelStore(path, clock=lambda: wall["t"])
            for point, tdp, count in first.new_floor_failures:
                store.record_floor_failure(key, point, tdp, count)
            wall["t"] += 100
            failures = GameModelStore(path, clock=lambda: wall["t"]).floor_failures(key)   # plugin reload
            self.assertEqual(failures, {"30x3": (9.0, 100.0, 2)})
            c = BudgetController(target_output_fps=90, now=7.0, min_tdp_w=3, max_tdp_w=20)
            c.load_floor_failures(failures, 7.0)
            self.assertEqual(c.point.key, "30x3")
            self.assertTrue(c._floor_blocked(9.0, 7.0), "not anchored at the reload: 140 s are left")
            self.assertTrue(c._floor_blocked(9.0, 7.0 + 139))
            self.assertFalse(c._floor_blocked(9.0, 7.0 + 141), "expired at the original 240 s")
            c.tdp = 10.0
            self.assertFalse(c._can_lower(), "the 9 W probe is not repeated by the new controller")

    def test_expiry_clear_and_bounds(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 50_000.0}
            path = Path(t) / "m.json"
            store = GameModelStore(path, clock=lambda: wall["t"])
            key = floor_key("mako", 90)
            self.assertTrue(store.record_floor_failure(key, "30x3", 9.0, 5))
            self.assertFalse(store.record_floor_failure(key, "45x2", 50.0, 1), "absurd TDP")
            wall["t"] += GameModelStore.FLOOR_BACKOFF_MAX_S - 1
            self.assertIn("30x3", GameModelStore(path, clock=lambda: wall["t"]).floor_failures(key))
            wall["t"] += 2
            self.assertEqual(store.floor_failures(key), {}, "never longer than FLOOR_BACKOFF_MAX_S")
            store.record_floor_failure(key, "30x3", 8.0, 1)
            self.assertTrue(store.record_floor_failure(key, "30x3", None))   # the level held: cleared
            self.assertEqual(GameModelStore(path, clock=lambda: wall["t"]).floor_failures(key), {})

    def test_a_level_that_holds_queues_a_clear(self):
        c = BudgetController(target_output_fps=90, now=0.0, min_tdp_w=3, max_tdp_w=20)
        c.tdp = 9.0
        c._note_floor_failure(0.0)
        c.phase, c.probe, c.last_good, c.good = "probe", "down", (c.idx, 10.0), 1
        c._healthy(10.0)
        self.assertEqual(c.new_floor_failures[-1], ("30x3", None, 0))

    def test_forget_game_drops_every_mode_and_target_of_that_game_only(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "m.json"
            store = GameModelStore(path)
            for key in (context_key("mako", 90, "budget", "1"), context_key("mako", 60, "balanced", "1"),
                        context_key("mako", 90, "budget", "12"), context_key("mako", 90, "budget")):
                store.record(key, "30x3", 9.0)
            store.record_floor_failure(floor_key("mako", 90, "1"), "30x3", 9.0)
            self.assertEqual(store.forget_game(game_prefix("mako", "1")), 3)
            again = GameModelStore(path)
            self.assertIsNone(again.get(context_key("mako", 90, "budget", "1")))
            self.assertIsNone(again.get(context_key("mako", 60, "balanced", "1")))
            self.assertEqual(again.floor_failures(floor_key("mako", 90, "1")), {})
            self.assertIsNotNone(again.get(context_key("mako", 90, "budget", "12")), "app:12 is another game")
            self.assertIsNotNone(again.get(context_key("mako", 90, "budget")))
            self.assertEqual(again.forget_game(game_prefix("mako", "1")), 0)


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

    def test_recently_failed_remembered_state_is_skipped_without_an_fps_dip(self):
        with tempfile.TemporaryDirectory() as t:
            wall = {"t": 1000.0}
            key = context_key("mako", 90, "budget")
            path = Path(t) / "model.json"
            store = GameModelStore(path, clock=lambda: wall["t"])
            self.assertTrue(store.record(key, "30x3", 8.0))
            wall["t"] += 70.0
            store.record_failure(key, "30x3", 9.0)
            # New controller after reload: recent failure belongs to the
            # same game at the same or higher cap than its stored good point.
            restored = GameModelStore(path, clock=lambda: wall["t"])
            c = BudgetController(target_output_fps=90, now=7.0, min_tdp_w=3, max_tdp_w=20)
            c.load_failures(restored.failures(key), now=7.0)
            self.assertFalse(c.warm_start(restored.get(key)["point"], restored.get(key)["tdp_w"], 7.0))
            self.assertEqual((c.phase, c.tdp, c.point.key), ("settle", 10.0, "30x3"))
            self.assertIn("recent-failure", c.last_reason)
            # At a cap ABOVE the one that failed, stored context is not
            # disproven, and normal warm start is still legal.
            higher = BudgetController(target_output_fps=90, now=7.0)
            higher.load_failures(restored.failures(key), now=7.0)
            self.assertTrue(higher.warm_start("30x3", 10.0, 7.0))
            # After the original TTL, the old point can be tried again.
            wall["t"] += GameModelStore.FAILURE_TTL_S + 1.0
            fresh = BudgetController(target_output_fps=90, now=9.0)
            fresh.load_failures(GameModelStore(path, clock=lambda: wall["t"]).failures(key), 9.0)
            self.assertTrue(fresh.warm_start("30x3", 8.0, 9.0))

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
