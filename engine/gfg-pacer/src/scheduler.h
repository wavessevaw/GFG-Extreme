/* GFG Frame OS — Presentation Scheduler core.
 *
 * Pure logic: no Vulkan, no clocks, no threads.  The layer feeds it timestamps (ns, monotonic)
 * and asks two questions every frame:
 *
 *   1. "The game wants to start its next frame now — how long should it wait?"
 *      (game-agnostic tick shaping: start just in time for the next real-frame slot, so the
 *      finished frame does not sit in a queue; input is sampled later => lower latency)
 *   2. "The game presented — when should this present be released?"
 *      (pacing on the real-frame slot grid)
 *
 * The scheduler learns the game's frame cost (start -> ready) and adapts its safety margin from
 * hits and misses.  It never changes game speed: it only moves the start of work inside the slot
 * the frame was going to be shown in anyway, and it never waits longer than max_wait_ns.
 */
#ifndef GFG_SCHEDULER_H
#define GFG_SCHEDULER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GFG_COST_WINDOW 64

typedef struct gfg_policy {
    double real_target_hz;   /* real-frame cadence the slots are laid out on; <= 0: no grid */
    int tick_shaping;        /* 1: delay frame starts to just-in-time */
    int pacing;              /* 1: hold early presents until their slot */
    double margin_ms;        /* initial safety margin before the slot */
    double min_margin_ms;
    double max_margin_ms;
    double max_wait_ms;      /* never wait longer than this in one call (<= one refresh) */
    double cost_quantile;    /* frame-cost quantile used for planning, e.g. 0.9 */
} gfg_policy;

typedef struct gfg_stats {
    uint64_t frames;
    uint64_t hits;           /* presented in the planned slot */
    uint64_t misses;         /* presented after the planned slot */
    double cost_p50_ms;
    double cost_q_ms;        /* cost at policy.cost_quantile */
    double margin_ms;
    double last_delay_ms;    /* frame-start delay applied for the current frame */
    double avg_delay_ms;     /* EWMA of applied start delays (= queueing latency removed) */
} gfg_stats;

typedef struct gfg_sched {
    gfg_policy policy;
    int64_t period_ns;
    int64_t next_slot_ns;    /* slot the frame being built is planned for; 0 = unknown */
    int64_t frame_start_ns;  /* when the current frame was allowed to start; 0 = unknown */
    double costs_ms[GFG_COST_WINDOW];
    int cost_count;
    int cost_head;
    double margin_ms;
    gfg_stats stats;
} gfg_sched;

void gfg_policy_defaults(gfg_policy *policy);
void gfg_sched_init(gfg_sched *s, const gfg_policy *policy);
/* A new policy from the control channel; keeps the learned frame cost and margin. */
void gfg_sched_set_policy(gfg_sched *s, const gfg_policy *policy);

/* The game is about to start building a frame (called at acquire / after the previous present).
 * Returns how long to wait first, in ns (0 = start now). Also records the start time. */
int64_t gfg_sched_frame_start(gfg_sched *s, int64_t now_ns);

/* The game presented the frame it started last.  ready_ns is when the frame was ready
 * (CPU submit done, or GPU end if known).  Returns the time the present should be released
 * (>= ready_ns); the caller waits until then.  Updates cost, margin, hit/miss. */
int64_t gfg_sched_present(gfg_sched *s, int64_t ready_ns);

const gfg_stats *gfg_sched_stats(const gfg_sched *s);

/* Quantile of the recorded frame costs (ms); 0 when nothing is known yet. */
double gfg_sched_cost_quantile(const gfg_sched *s, double q);

#ifdef __cplusplus
}
#endif

#endif /* GFG_SCHEDULER_H */
