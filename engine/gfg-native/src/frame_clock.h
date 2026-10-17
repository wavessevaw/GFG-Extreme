/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef GFG_FRAME_CLOCK_H
#define GFG_FRAME_CLOCK_H
#include <stdint.h>
/* Absolute CLOCK_MONOTONIC host handoff deadlines, never scanout evidence.
 * For pair R0,R1 separated by dt: G(t)=R1+t*dt, R=R1+dt.
 * This delays content by one measured source interval (R1 lookahead required).
 * Source time survives mailbox waits; late workers never move expired slots
 * into the future. Only consecutive display-spaced slots may be admitted. */
typedef struct {
    uint64_t period_ns, real_ns, resyncs;
    uint64_t source_ns, interval_ns, target_ns[3];
    unsigned mask, discontinuity;
} gfg_frame_clock;
static inline void gfg_frame_clock_pair(gfg_frame_clock *c,uint64_t source,unsigned multiplier) {
    if(!c->period_ns)return;
    uint64_t dt=c->source_ns && source>c->source_ns?source-c->source_ns:0;
    uint64_t gap=6*c->period_ns;
    if(gap<250000000ull)gap=250000000ull;
    c->discontinuity=c->source_ns && (!dt || dt>gap);
    if(!dt || dt>gap)dt=c->interval_ns?c->interval_ns:multiplier*c->period_ns;
    if(c->discontinuity)++c->resyncs;
    c->source_ns=source;c->interval_ns=dt;c->mask=0;
    c->target_ns[0]=source+dt/multiplier;
    c->target_ns[1]=source+2*dt/3;
    c->target_ns[2]=source+dt;
    /* A source-rate change may overlap an earlier pair. Keep deadlines
     * bounded by source+2dt; otherwise suppress interpolation and re-anchor.
     * No wall-clock/worker-time resync and no unbounded phase accumulator. */
    uint64_t last=c->discontinuity?0:c->real_ns;
    for(unsigned k=0;k<multiplier-1;++k) {
        uint64_t target=c->target_ns[k];
        if(!last || target+c->period_ns/20>=last+c->period_ns) {
            c->mask|=1u<<k;last=target;
        }
    }
    if(last && c->target_ns[2]<last+c->period_ns)c->target_ns[2]=last+c->period_ns;
    if(c->target_ns[2]>source+2*dt) {
        c->mask=0;c->target_ns[2]=source+dt;++c->resyncs;
    }
    if(c->discontinuity)c->mask=0;
    c->real_ns=c->target_ns[2];
}
static inline uint64_t gfg_frame_clock_target(const gfg_frame_clock *c,unsigned kind) {
    return c->target_ns[kind]; /* 0 G1 (or x2 midpoint), 1 G2, 2 R */
}
static inline int gfg_frame_clock_admit(const gfg_frame_clock *c,unsigned kind,uint64_t now) {
    return (c->mask&(1u<<kind)) && now<c->target_ns[kind];
}
#endif
