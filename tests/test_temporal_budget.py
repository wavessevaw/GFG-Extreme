"""Exercise LMC budget recovery/overload without a Vulkan device."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LmcBudgetTests(unittest.TestCase):
    def test_real_time_deadlines_recovery_and_repeat_length(self):
        source = r'''
#include "lmc_budget.hpp"
#include <cassert>
#include <limits>
using mako::backend::gfg_temporal::LmcBudget;
int main() {
    using A = LmcBudget::Action;
    // CPU/queue wait can miss the interval even with very cheap GPU work.
    for (double interval : {1000.0/15, 1000.0/30, 1000.0/60}) {
        LmcBudget p;
        double elapsed = 0;
        A action = A::keep;
        while (action == A::keep) {
            p.observe(1, interval * 1.2, interval, .25, 0);
            elapsed += interval;
            action = p.plan(0);
        }
        assert(action == A::cheaper);
        assert(elapsed >= 250 && elapsed < 250 + interval + .001);
        assert(p.deadline_misses > 0);
    }
    LmcBudget gpu;
    for (int i = 0; i < 8; ++i) gpu.observe(12, 15, 33.34, .25, 2);
    assert(gpu.plan(2) == A::repeat_one);  // never a 120-pair blackout
    assert(gpu.plan(2) == A::keep);       // must measure afresh after one repeat
    // A single expensive sample must not lower quality; a good one breaks
    // the overload sequence. Invalid timestamps must not invent evidence.
    LmcBudget transient;
    transient.observe(30, 40, 33.34, .25, 0);
    assert(transient.plan(0) == A::keep);
    transient.observe(1, 10, 33.34, .25, 0);
    transient.observe(1, std::numeric_limits<double>::quiet_NaN(), 33.34, .25, 0);
    assert(transient.over_ms == 0 && transient.plan(0) == A::keep);
    // A known costly previous tier is not retried after only ten seconds;
    // a long healthy run eventually retries it instead of being stuck low.
    LmcBudget recovery;
    recovery.observe(20, 40, 33.34, .25, 0);
    recovery.over_ms = 0;
    for (int i = 0; i < 300; ++i) recovery.observe(1, 10, 33.34, .25, 1);
    assert(recovery.plan(1) == A::keep);
    for (int i = 0; i < 1500; ++i) recovery.observe(1, 10, 33.34, .25, 1);
    assert(recovery.plan(1) == A::better);
}
'''
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "budget.cpp"
            exe = Path(td) / "budget"
            src.write_text(source)
            subprocess.run(["c++", "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "engine/gfg-temporal/mako"), str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
