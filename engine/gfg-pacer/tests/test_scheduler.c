/* Host tests for the Presentation Scheduler core: deterministic game simulation. */
#include "../src/scheduler.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); } } while (0)

/* xorshift + Box-Muller: same numbers on every machine */
static uint64_t rng = 88172645463325252ull;
static double urand(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return (rng >> 11) * (1.0 / 9007199254740992.0); }
static double nrand(double mean, double sd) { double u = urand() + 1e-12, v = urand(); return mean + sd * sqrt(-2 * log(u)) * cos(6.283185307179586 * v); }

typedef struct { double latency_ms; double miss_rate; double fps; } sim_result;

/* A game loop: starts a frame when allowed, is ready after `cost`, presents; the next frame can
 * start once the present has been released (one frame in flight).  Latency = input sampled at
 * frame start -> release on the slot grid. */
static sim_result simulate(int shaping, double cost_mean, double cost_sd, double hz, int frames, double spike_rate)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);
    p.real_target_hz = hz;
    p.tick_shaping = shaping;
    gfg_sched_init(&s, &p);
    rng = 88172645463325252ull;
    int64_t now = 1000000000;
    double lat_sum = 0;
    int counted = 0;
    for (int i = 0; i < frames; i++) {
        int64_t wait = gfg_sched_frame_start(&s, now);
        int64_t start = now + wait;
        double cost = nrand(cost_mean, cost_sd);
        if (urand() < spike_rate)
            cost *= 1.8;                         /* occasional heavy frame */
        if (cost < 1) cost = 1;
        int64_t ready = start + (int64_t)(cost * 1e6);
        int64_t release = gfg_sched_present(&s, ready);
        if (i >= 100) { lat_sum += (release - start) / 1e6; counted++; }
        now = release;
    }
    const gfg_stats *st = gfg_sched_stats(&s);
    sim_result r = { lat_sum / counted, (double)st->misses / (double)st->frames, 0 };
    r.fps = frames / ((now - 1000000000) / 1e9);
    return r;
}

static void test_tick_shaping_removes_queueing_latency(void)
{
    sim_result base = simulate(0, 20, 1.5, 30, 2000, 0);
    sim_result jit = simulate(1, 20, 1.5, 30, 2000, 0);
    printf("30 real, 20 ms frames: latency %.1f -> %.1f ms, misses %.1f%% -> %.1f%%, fps %.1f -> %.1f\n",
           base.latency_ms, jit.latency_ms, base.miss_rate * 100, jit.miss_rate * 100, base.fps, jit.fps);
    CHECK(base.latency_ms > 30, "baseline latency %.1f", base.latency_ms);
    CHECK(jit.latency_ms < base.latency_ms - 8, "shaping saved only %.1f ms", base.latency_ms - jit.latency_ms);
    CHECK(jit.miss_rate < 0.05, "miss rate %.3f", jit.miss_rate);
    CHECK(fabs(jit.fps - base.fps) < 0.5, "frame rate changed %.2f -> %.2f", base.fps, jit.fps);
}

static void test_spiky_game_keeps_its_frame_rate(void)
{
    sim_result base = simulate(0, 18, 3, 30, 3000, 0.03);
    sim_result jit = simulate(1, 18, 3, 30, 3000, 0.03);
    printf("spiky 18 ms frames: latency %.1f -> %.1f ms, misses %.1f%% -> %.1f%%, fps %.2f -> %.2f\n",
           base.latency_ms, jit.latency_ms, base.miss_rate * 100, jit.miss_rate * 100, base.fps, jit.fps);
    CHECK(jit.fps > base.fps - 1.0, "fps %.2f vs %.2f", jit.fps, base.fps);
    CHECK(jit.miss_rate < base.miss_rate + 0.05, "misses %.3f vs %.3f", jit.miss_rate, base.miss_rate);
    CHECK(jit.latency_ms < base.latency_ms, "no gain");
}

static void test_heavy_game_is_never_delayed(void)
{
    /* Frames as long as the slot: nothing to shape, the scheduler must not slow the game. */
    sim_result base = simulate(0, 33, 1, 30, 1000, 0);
    sim_result jit = simulate(1, 33, 1, 30, 1000, 0);
    CHECK(jit.fps > base.fps - 0.5, "heavy game slowed %.2f -> %.2f", base.fps, jit.fps);
}

static void test_waits_are_capped(void)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);
    p.real_target_hz = 20;          /* 50 ms slots */
    p.max_wait_ms = 5;
    gfg_sched_init(&s, &p);
    int64_t now = 1000000000;
    for (int i = 0; i < 20; i++) {
        int64_t w = gfg_sched_frame_start(&s, now);
        CHECK(w <= 5000000, "wait %lld ns over the cap", (long long)w);
        now = gfg_sched_present(&s, now + w + 2000000);
    }
}

static void test_no_grid_is_pass_through(void)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);       /* real_target_hz = 0 */
    gfg_sched_init(&s, &p);
    for (int i = 0; i < 20; i++) {
        CHECK(gfg_sched_frame_start(&s, 1000 + i * 100) == 0, "waited without a grid");
        CHECK(gfg_sched_present(&s, 1050 + i * 100) == 1050 + i * 100, "held without a grid");
    }
}

static void test_policy_change_reanchors(void)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);
    p.real_target_hz = 30;
    gfg_sched_init(&s, &p);
    int64_t now = 1000000000;
    for (int i = 0; i < 50; i++)
        now = gfg_sched_present(&s, now + gfg_sched_frame_start(&s, now) + 10000000);
    p.real_target_hz = 45;
    gfg_sched_set_policy(&s, &p);
    CHECK(s.next_slot_ns == 0, "grid not re-anchored");
    CHECK(s.cost_count > 0, "learned cost lost");
}

static void test_long_idle_catch_up(void)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);
    p.real_target_hz = 30;
    p.max_wait_ms = 30;
    gfg_sched_init(&s, &p);
    int64_t now = 1000000000, period = 33333333;
    for (int i = 0; i < 20; i++) {             /* 10 ms frames on the 30 Hz grid */
        now += gfg_sched_frame_start(&s, now);
        now = gfg_sched_present(&s, now + 10000000);
    }
    now += 3600ll * 1000000000ll;              /* an hour paused: one step, not 108000 loop turns */
    int64_t d = gfg_sched_frame_start(&s, now);
    CHECK(s.next_slot_ns >= now + 10000000 && s.next_slot_ns < now + 10000000 + period, "slot %lld after idle",
          (long long)(s.next_slot_ns - now));
    CHECK(d >= 0 && d < period, "delay after idle %lld", (long long)d);
}

/* A scene that keeps changing weight: cost ramps 12 -> 24 ms and back every 240 frames (8 s at
 * 30 real), plus noise.  Predictive planning must miss less while the scene gets heavier and give
 * the reserve back sooner while it gets lighter. */
static sim_result simulate_ramp(int predictive, int frames)
{
    gfg_policy p;
    gfg_sched s;
    gfg_policy_defaults(&p);
    p.real_target_hz = 30;
    p.predictive = predictive;
    gfg_sched_init(&s, &p);
    rng = 88172645463325252ull;
    int64_t now = 1000000000;
    double lat_sum = 0;
    int counted = 0;
    for (int i = 0; i < frames; i++) {
        int64_t wait = gfg_sched_frame_start(&s, now);
        int64_t start = now + wait;
        double phase = (double)(i % 240) / 240.0;
        double mean = 12.0 + 12.0 * (phase < 0.5 ? phase * 2 : (1 - phase) * 2);
        double cost = nrand(mean, 0.8);
        if (cost < 1) cost = 1;
        int64_t ready = start + (int64_t)(cost * 1e6);
        int64_t release = gfg_sched_present(&s, ready);
        if (i >= 100) { lat_sum += (release - start) / 1e6; counted++; }
        now = release;
    }
    const gfg_stats *st = gfg_sched_stats(&s);
    sim_result r = { lat_sum / counted, (double)st->misses / (double)st->frames, 0 };
    r.fps = frames / ((now - 1000000000) / 1e9);
    return r;
}

static void test_predictive_planning_follows_the_scene(void)
{
    sim_result old = simulate_ramp(0, 4800);
    sim_result pred = simulate_ramp(1, 4800);
    printf("changing scene: latency %.1f -> %.1f ms, misses %.1f%% -> %.1f%%, fps %.2f -> %.2f\n",
           old.latency_ms, pred.latency_ms, old.miss_rate * 100, pred.miss_rate * 100, old.fps, pred.fps);
    CHECK(pred.miss_rate <= old.miss_rate, "predictive missed more %.3f vs %.3f", pred.miss_rate, old.miss_rate);
    CHECK(pred.latency_ms < old.latency_ms - 0.3, "predictive gained only %.2f ms", old.latency_ms - pred.latency_ms);
    CHECK(pred.fps > old.fps - 0.3, "fps %.2f vs %.2f", pred.fps, old.fps);
}

int main(void)
{
    test_tick_shaping_removes_queueing_latency();
    test_spiky_game_keeps_its_frame_rate();
    test_heavy_game_is_never_delayed();
    test_waits_are_capped();
    test_no_grid_is_pass_through();
    test_policy_change_reanchors();
    test_long_idle_catch_up();
    test_predictive_planning_follows_the_scene();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("scheduler tests OK\n");
    return 0;
}
