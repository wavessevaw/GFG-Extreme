/* GFG Frame OS — layer-side measurements.  See metrics.h. */
#include "metrics.h"

#include <math.h>
#include <string.h>

#define NS_PER_MS 1000000.0

void gfg_ring_push(gfg_ring *r, double v)
{
    if (!isfinite(v))
        return;
    r->v[r->head] = v;
    r->head = (r->head + 1) % GFG_RING_LEN;
    if (r->count < GFG_RING_LEN)
        r->count++;
}

double gfg_ring_quantile(const gfg_ring *r, double q)
{
    double s[GFG_RING_LEN];
    int n = r->count, i, j;
    if (n <= 0)
        return 0.0;
    memcpy(s, r->v, sizeof(double) * (size_t)n);
    for (i = 1; i < n; i++) {   /* insertion sort: n <= 64 */
        double v = s[i];
        for (j = i - 1; j >= 0 && s[j] > v; j--)
            s[j + 1] = s[j];
        s[j + 1] = v;
    }
    q = q < 0 ? 0 : (q > 1 ? 1 : q);
    return s[(int)llround(q * (n - 1))];
}

void gfg_metrics_reset(gfg_metrics *m)
{
    memset(m, 0, sizeof(*m));
}

void gfg_metrics_frame_start(gfg_metrics *m, int64_t start_ns)
{
    m->start_ns = start_ns;
}

void gfg_metrics_ready(gfg_metrics *m, int64_t ready_ns)
{
    if (m->start_ns > 0 && ready_ns >= m->start_ns)
        gfg_ring_push(&m->costs_ms, (double)(ready_ns - m->start_ns) / NS_PER_MS);
}

void gfg_metrics_released(gfg_metrics *m, int64_t release_ns)
{
    if (m->start_ns > 0 && release_ns >= m->start_ns) {
        double age = (double)(release_ns - m->start_ns) / NS_PER_MS;
        m->freshness_ms = m->freshness_ms > 0 ? (1 - GFG_FRESHNESS_ALPHA) * m->freshness_ms + GFG_FRESHNESS_ALPHA * age
                                              : age;
    }
    if (m->last_present_ns > 0 && release_ns >= m->last_present_ns)
        gfg_ring_push(&m->intervals_ms, (double)(release_ns - m->last_present_ns) / NS_PER_MS);
    m->last_present_ns = release_ns;
    m->start_ns = 0;
    m->frames++;
}
