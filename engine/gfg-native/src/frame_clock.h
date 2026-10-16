/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef GFG_FRAME_CLOCK_H
#define GFG_FRAME_CLOCK_H
#include <stdint.h>
/* Host handoff deadlines. They do not measure or assert physical scanout.
 * One source interval of lookahead, three ordered slots, no catch-up burst. */
typedef struct { uint64_t period_ns, real_ns, resyncs; } gfg_frame_clock;
static inline void gfg_frame_clock_pair(gfg_frame_clock *c,uint64_t now) {
    if(!c->period_ns)return;
    uint64_t next=c->real_ns+3*c->period_ns;
    if(!c->real_ns || next<now+c->period_ns) {
        if(c->real_ns)++c->resyncs;
        next=now+3*c->period_ns;
    }
    c->real_ns=next;
}
static inline uint64_t gfg_frame_clock_target(const gfg_frame_clock *c,unsigned kind) {
    return c->real_ns-(2-kind)*c->period_ns; /* 0 G1, 1 G2, 2 R */
}
#endif
