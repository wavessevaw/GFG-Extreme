/* GFG Frame OS — layer-side measurements (pure C, host-testable).
 *
 * What the layer observes per device, independent of whether the scheduler acts:
 * frame cost (start -> present call), present intervals, freshness (age of the input the
 * game sampled at frame start when the present returns, i.e. after any hold by the layers below)
 * and how long the present / acquire forwards block. */
#ifndef GFG_METRICS_H
#define GFG_METRICS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GFG_RING_LEN 64
#define GFG_FRESHNESS_ALPHA 0.05

typedef struct gfg_ring {
    double v[GFG_RING_LEN];
    int count;
    int head;
} gfg_ring;

typedef struct gfg_metrics {
    uint64_t frames;
    int64_t start_ns;          /* current frame start (after any applied delay); 0 = none */
    int64_t last_present_ns;   /* last forwarded present; 0 = none */
    double freshness_ms;       /* EWMA */
    double present_hold_ms;    /* EWMA of present forward -> return */
    double acquire_block_ms;   /* EWMA of the acquire forward's duration */
    gfg_ring costs_ms;
    gfg_ring intervals_ms;
} gfg_metrics;

void gfg_ring_push(gfg_ring *r, double v);
/* Quantile of the stored values; 0 when empty. */
double gfg_ring_quantile(const gfg_ring *r, double q);

void gfg_metrics_reset(gfg_metrics *m);
void gfg_metrics_frame_start(gfg_metrics *m, int64_t start_ns);
/* Present call at ready_ns: records the cost of the current frame. */
void gfg_metrics_ready(gfg_metrics *m, int64_t ready_ns);
/* Present forwarded at release_ns, returned at return_ns: freshness, hold, interval, frame count;
 * ends the frame. */
void gfg_metrics_released(gfg_metrics *m, int64_t release_ns, int64_t return_ns);
/* An acquire forward blocked for block_ns. */
void gfg_metrics_acquired(gfg_metrics *m, int64_t block_ns);

#ifdef __cplusplus
}
#endif

#endif /* GFG_METRICS_H */
