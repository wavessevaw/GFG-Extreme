/* GFG Frame OS — Presentation Scheduler core.  See scheduler.h. */
#include "scheduler.h"

#include <math.h>
#include <string.h>

#define NS_PER_MS 1000000.0
#define MIN_COST_SAMPLES 8

void gfg_policy_defaults(gfg_policy *p)
{
    memset(p, 0, sizeof(*p));
    p->real_target_hz = 0.0;
    p->tick_shaping = 1;
    p->pacing = 1;
    p->margin_ms = 2.0;
    p->min_margin_ms = 1.0;
    p->max_margin_ms = 8.0;
    p->max_wait_ms = 11.0;   /* one 90 Hz refresh */
    p->cost_quantile = 0.95;
}

static int64_t period_for(const gfg_policy *p)
{
    if (!(p->real_target_hz > 0.0) || !isfinite(p->real_target_hz))
        return 0;
    return (int64_t)llround(1e9 / p->real_target_hz);
}

static double clamp(double v, double lo, double hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

void gfg_sched_init(gfg_sched *s, const gfg_policy *policy)
{
    memset(s, 0, sizeof(*s));
    s->policy = *policy;
    s->period_ns = period_for(policy);
    s->margin_ms = clamp(policy->margin_ms, policy->min_margin_ms, policy->max_margin_ms);
    s->stats.margin_ms = s->margin_ms;
}

void gfg_sched_set_policy(gfg_sched *s, const gfg_policy *policy)
{
    int64_t period = period_for(policy);
    s->policy = *policy;
    if (period != s->period_ns) {
        s->period_ns = period;
        s->next_slot_ns = 0;   /* re-anchor the grid on the next present */
    }
    s->margin_ms = clamp(s->margin_ms, policy->min_margin_ms, policy->max_margin_ms);
}

static int cmp_double(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

double gfg_sched_cost_quantile(const gfg_sched *s, double q)
{
    double sorted[GFG_COST_WINDOW];
    int n = s->cost_count, i, j;
    if (n <= 0)
        return 0.0;
    memcpy(sorted, s->costs_ms, sizeof(double) * (size_t)n);
    /* insertion sort: n <= 64, called once per frame */
    for (i = 1; i < n; i++) {
        double v = sorted[i];
        for (j = i - 1; j >= 0 && cmp_double(&sorted[j], &v) > 0; j--)
            sorted[j + 1] = sorted[j];
        sorted[j + 1] = v;
    }
    q = clamp(q, 0.0, 1.0);
    i = (int)llround(q * (n - 1));
    return sorted[i];
}

static void record_cost(gfg_sched *s, double cost_ms)
{
    if (!(cost_ms >= 0.0) || !isfinite(cost_ms))
        return;
    s->costs_ms[s->cost_head] = cost_ms;
    s->cost_head = (s->cost_head + 1) % GFG_COST_WINDOW;
    if (s->cost_count < GFG_COST_WINDOW)
        s->cost_count++;
}

int64_t gfg_sched_frame_start(gfg_sched *s, int64_t now_ns)
{
    const gfg_policy *p = &s->policy;
    int64_t delay = 0;
    if (s->period_ns > 0 && p->tick_shaping && s->next_slot_ns > 0 && s->cost_count >= MIN_COST_SAMPLES) {
        double cost_q = gfg_sched_cost_quantile(s, p->cost_quantile);
        int64_t cost_ns = (int64_t)llround(cost_q * NS_PER_MS);
        int64_t plan_ns = (int64_t)llround((cost_q + s->margin_ms) * NS_PER_MS);
        int64_t slot = s->next_slot_ns;
        if (plan_ns >= s->period_ns) {
            /* Frames as long as the slot: nothing queues, there is nothing to shape. */
            s->frame_start_ns = now_ns;
            s->stats.last_delay_ms = 0.0;
            return 0;
        }
        /* A slot the frame cannot make even when started now is gone: plan for the next one.
         * Its frame would land there anyway, so starting later only removes queueing. */
        if (slot < now_ns + cost_ns)   /* after a long idle: many slots, no loop */
            slot += (now_ns + cost_ns - slot + s->period_ns - 1) / s->period_ns * s->period_ns;
        s->next_slot_ns = slot;
        if (slot - plan_ns > now_ns)
            delay = slot - plan_ns - now_ns;
        int64_t cap = (int64_t)llround(p->max_wait_ms * NS_PER_MS);
        if (delay > cap)
            delay = cap;
    }
    s->frame_start_ns = now_ns + delay;
    s->stats.last_delay_ms = (double)delay / NS_PER_MS;
    s->stats.avg_delay_ms = s->stats.frames ? 0.95 * s->stats.avg_delay_ms + 0.05 * s->stats.last_delay_ms
                                            : s->stats.last_delay_ms;
    return delay;
}

int64_t gfg_sched_present(gfg_sched *s, int64_t ready_ns)
{
    const gfg_policy *p = &s->policy;
    int64_t release = ready_ns;
    if (s->frame_start_ns > 0 && ready_ns >= s->frame_start_ns)
        record_cost(s, (double)(ready_ns - s->frame_start_ns) / NS_PER_MS);
    s->stats.frames++;

    if (s->period_ns > 0) {
        int64_t slot = s->next_slot_ns;
        if (slot <= 0) {
            slot = ready_ns;   /* anchor the grid on the first present */
        } else if (ready_ns <= slot) {
            s->stats.hits++;
            s->margin_ms = clamp(s->margin_ms * 0.995, p->min_margin_ms, p->max_margin_ms);  /* slow give-back */
        } else {
            int64_t late = ready_ns - slot;
            int64_t k = (late + s->period_ns - 1) / s->period_ns;
            slot += k * s->period_ns;
            s->stats.misses++;
            s->margin_ms = clamp(s->margin_ms * 1.5 + 0.5, p->min_margin_ms, p->max_margin_ms);
        }
        if (p->pacing && slot > ready_ns)
            release = slot;
        s->next_slot_ns = slot + s->period_ns;
    }
    s->frame_start_ns = 0;
    s->stats.margin_ms = s->margin_ms;
    s->stats.cost_p50_ms = gfg_sched_cost_quantile(s, 0.5);
    s->stats.cost_q_ms = gfg_sched_cost_quantile(s, p->cost_quantile);
    return release;
}

const gfg_stats *gfg_sched_stats(const gfg_sched *s)
{
    return &s->stats;
}
