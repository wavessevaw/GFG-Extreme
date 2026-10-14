/* Frame budget scheduler: see te_scheduler.h. */
#include "te_scheduler.h"

#include <string.h>

#define EMA 0.2
#define SAFETY 0.85          /* use at most 85 % of the free GPU time */
#define CALM_PAIRS 30        /* pairs well under budget before improving quality */
#define CALM_RATIO 0.6
#define MISS_PAIRS 3         /* consecutive misses that force a cheaper level */
#define NOT_WORTH_PAIRS 8
#define PROFILE_EVERY 32
#define WARMUP 4
#define RECHECK_PAIRS 240

static const float k_scale[TE_SCHED_LEVELS] = {1.0f, 1.5f, 2.5f, 4.0f};

void te_scheduler_init(te_scheduler* s) {
    memset(s, 0, sizeof *s);
    s->since_profile = PROFILE_EVERY; /* calibrate on the first pair */
}

float te_scheduler_light_scale(uint32_t level) {
    return k_scale[level < TE_SCHED_LEVELS ? level : TE_SCHED_LEVELS - 1];
}

static double ema(double old, double value, uint32_t n) { return n == 0 ? value : old + (value - old) * EMA; }

/* Light-share response to the threshold scale is unknown in general, so the
 * prediction at another level keeps the measured shares and only the level
 * actually observed is trusted; cheaper levels can only move tiles from FULL
 * to LIGHT, so the current-level prediction is an upper bound for them. */
static double per_output_ms(const te_scheduler* s, int force_full) {
    if (s->calibrated == 0) return s->frame_ms;
    double tiles = s->share[0] + s->share[1] + s->share[2];
    if (tiles <= 0.0) return s->frame_ms;
    double work = force_full ? tiles * s->tile_ms[2]
                             : s->share[0] * s->tile_ms[0] + s->share[1] * s->tile_ms[1] + s->share[2] * s->tile_ms[2];
    return s->lists_ms + work;
}

te_sched_decision te_scheduler_decide(te_scheduler* s, const te_sched_input* in) {
    te_sched_decision d;
    memset(&d, 0, sizeof d);
    d.outputs = in->requested;
    double busy = in->gpu_busy >= 0.0 && in->gpu_busy <= 1.0 ? in->gpu_busy : 0.5;
    d.budget_ms = in->real_interval_ms > 0.0 ? in->real_interval_ms * (1.0 - busy) * SAFETY : 0.0;
    d.profile = s->since_profile >= PROFILE_EVERY;
    if (s->samples < WARMUP) {
        d.level = s->level;
        d.light_scale = te_scheduler_light_scale(d.level);
        d.reason = TE_REASON_WARMUP;
        d.predicted_ms = s->samples ? s->fixed_ms + in->requested * s->frame_ms : 0.0;
        return d;
    }
    d.force_full = s->force_full;
    d.reason = s->force_full ? TE_REASON_ADAPTIVE_NOT_WORTH : (s->last_cut ? TE_REASON_SCENE_CUT : TE_REASON_NONE);
    uint32_t level = s->level;
    double per = per_output_ms(s, d.force_full);
    double predicted = s->fixed_ms + in->requested * per;
    if (d.budget_ms > 0.0 && predicted > d.budget_ms && level + 1 < TE_SCHED_LEVELS) {
        level++;
        s->calm = 0;
        d.reason = TE_REASON_OVER_BUDGET;
    } else if (s->misses >= MISS_PAIRS && level + 1 < TE_SCHED_LEVELS) {
        level++;
        s->misses = 0;
        s->calm = 0;
        d.reason = TE_REASON_MISSES;
    } else if (s->calm >= CALM_PAIRS && level > 0) {
        level--;
        s->calm = 0;
    }
    s->level = level;
    d.level = level;
    d.light_scale = te_scheduler_light_scale(level);
    /* at the cheapest level, shed synthetic frames before giving up */
    uint32_t outs = in->requested;
    if (level + 1 >= TE_SCHED_LEVELS)
        while (outs > 0 && s->fixed_ms + outs * per > d.budget_ms) outs--;
    if (outs == 0 || d.budget_ms <= 0.0) {
        d.action = TE_SCHED_FALLBACK;
        d.reason = TE_REASON_OVER_BUDGET;
        d.outputs = 0;
        d.predicted_ms = predicted;
        s->fallbacks++;
        return d;
    }
    d.outputs = outs;
    d.predicted_ms = s->fixed_ms + outs * per;
    return d;
}

void te_scheduler_observe(te_scheduler* s, const te_sched_observation* o, double budget_ms) {
    s->total_pairs++;
    s->last_cut = o->scene_cut;
    /* uniform FULL hides whether adaptivity would pay now: re-evaluate periodically */
    if (s->force_full && ++s->full_since >= RECHECK_PAIRS) {
        s->force_full = 0;
        s->not_worth = 0;
    }
    if (!o->timed || o->outputs == 0) return;
    double pair_ms = o->fixed_ms;
    double frame_sum = 0.0, lists = 0.0;
    double share[3] = {0, 0, 0};
    for (uint32_t i = 0; i < o->outputs && i < 4; ++i) {
        pair_ms += o->total_ms[i];
        frame_sum += o->total_ms[i];
        lists += o->lists_ms[i];
        for (int c = 0; c < 3; ++c) share[c] += o->tiles[i][c];
    }
    uint32_t n = s->samples;
    s->fixed_ms = ema(s->fixed_ms, o->fixed_ms, n);
    s->frame_ms = ema(s->frame_ms, frame_sum / o->outputs, n);
    s->lists_ms = ema(s->lists_ms, lists / o->outputs, n);
    for (int c = 0; c < 3; ++c) s->share[c] = share[c] / o->outputs;
    if (o->profiled) {
        double t[3] = {0, 0, 0}, k[3] = {0, 0, 0};
        for (uint32_t i = 0; i < o->outputs && i < 4; ++i) {
            t[0] += o->reuse_ms[i];
            t[1] += o->light_ms[i];
            t[2] += o->full_ms[i];
            for (int c = 0; c < 3; ++c) k[c] += o->tiles[i][c];
        }
        for (int c = 0; c < 3; ++c)
            if (k[c] > 0) s->tile_ms[c] = s->calibrated ? s->tile_ms[c] + (t[c] / k[c] - s->tile_ms[c]) * 0.5 : t[c] / k[c];
        s->calibrated++;
        s->since_profile = 0;
        /* adaptivity pays when the work it moves off FULL costs more than classify + lists */
        if (s->tile_ms[2] > 0.0 && !o->scene_cut) {
            double saved = 0.0;
            for (uint32_t i = 0; i < o->outputs && i < 4; ++i)
                saved += o->tiles[i][0] * (s->tile_ms[2] - s->tile_ms[0]) + o->tiles[i][1] * (s->tile_ms[2] - s->tile_ms[1]);
            double overhead = lists + o->classify_ms; /* what classification adds per pair */
            if (!s->force_full) {
                s->not_worth = saved < overhead ? s->not_worth + 1 : 0;
                if (s->not_worth >= NOT_WORTH_PAIRS) {
                    s->force_full = 1;
                    s->full_since = 0;
                }
            }
        }
    } else {
        s->since_profile++;
    }
    s->samples++;
    if (budget_ms > 0.0) {
        if (pair_ms > budget_ms) {
            s->misses++;
            s->total_misses++;
            s->calm = 0;
        } else {
            s->misses = 0;
            s->calm = pair_ms < CALM_RATIO * budget_ms ? s->calm + 1 : 0;
        }
    }
}
