"""Governor 2.0 shadow lease: one experiment at a time is recorded, overlaps are flagged."""
import unittest
from helpers import Clock
from gfg_plugin.lease import ExperimentLease


class LeaseTest(unittest.TestCase):
    def setUp(self):
        self.clock, self.notes = Clock(), []
        self.lease = ExperimentLease(clock=self.clock, journal=lambda k, **f: self.notes.append((k, f)))

    def run_for(self, seconds, **running):
        for _ in range(seconds):
            self.clock.t += 1
            self.lease.observe(running)

    def kinds(self):
        return [k for k, _ in self.notes]

    def test_one_experiment_is_one_transaction(self):
        self.run_for(5, tdp=True)
        self.run_for(1)
        self.assertEqual(self.kinds(), ["lease-start", "lease-end"])
        self.assertEqual(self.notes[1][1]["axis"], "tdp")

    def test_second_experiment_while_one_runs_is_a_conflict(self):
        self.run_for(3, cpu=True)
        self.run_for(3, cpu=True, gpu=True)
        self.assertIn("lease-conflict", self.kinds())
        self.assertEqual(self.lease.status()["holder"], "cpu")
        self.assertEqual(self.lease.conflicts, 1)   # counted once per overlap, not per second

    def test_overrun_is_flagged_once(self):
        self.run_for(40, tdp=True)
        self.assertEqual(self.kinds().count("lease-overrun"), 1)

    def test_back_to_back_experiments_get_new_ids(self):
        self.run_for(2, cpu=True)
        self.run_for(2, gpu=True)
        starts = [f["id"] for k, f in self.notes if k == "lease-start"]
        self.assertEqual(starts, [1, 2])


if __name__ == "__main__":
    unittest.main()
