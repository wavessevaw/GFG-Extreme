/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/frame_clock.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    const uint64_t p=1000000000ull/90,t=1000000000ull;
    gfg_frame_clock c={.period_ns=p};
    gfg_frame_clock_pair(&c,t,3);
    for(unsigned k=0;k<3;++k)assert(gfg_frame_clock_target(&c,k)==t+(k+1)*p);
    assert(c.mask==3);
    gfg_frame_clock_pair(&c,t+3*p,3);
    assert(c.real_ns==t+6*p && c.resyncs==0);
    /* Source capture time, rather than worker start, defines every deadline.
     * Missing G1 never invalidates a still-future G2. */
    assert(!gfg_frame_clock_admit(&c,0,t+4*p+1));
    assert(gfg_frame_clock_admit(&c,1,t+4*p+1));
    assert(!gfg_frame_clock_admit(&c,1,t+5*p));
    assert(c.real_ns==t+6*p);
    gfg_frame_clock v={.period_ns=p};
    gfg_frame_clock_pair(&v,t,3);
    gfg_frame_clock_pair(&v,t+4*p,3);
    assert(v.interval_ns==4*p && v.target_ns[0]==t+4*p+4*p/3);
    assert(v.target_ns[1]==t+4*p+8*p/3 && v.real_ns==t+8*p);
    /* 60 real on 90Hz cannot admit two extra slots; never claim x3. */
    gfg_frame_clock high={.period_ns=p};
    gfg_frame_clock_pair(&high,t,3);
    gfg_frame_clock_pair(&high,t+3*p/2,3);
    assert(high.mask!=3 && high.real_ns<=t+3*p/2+2*high.interval_ns);
    /* x2 has one true midpoint, not the first x3 position. */
    gfg_frame_clock x2={.period_ns=p};gfg_frame_clock_pair(&x2,t,2);
    assert(x2.mask==1 && x2.target_ns[0]==t+p && x2.real_ns==t+2*p);
    /* Refresh change changes admission, not source-time interpolation. */
    v.period_ns=1000000000ull/60;
    gfg_frame_clock_pair(&v,t+8*p,3);
    assert(v.interval_ns==4*p && v.target_ns[0]==t+8*p+4*p/3);
    gfg_frame_clock_pair(&v,t+100*p,3);
    assert(v.discontinuity && !v.mask && v.resyncs);
    gfg_frame_clock_pair(&v,t+100*p,3);assert(v.discontinuity && !v.mask);
    gfg_frame_clock disabled={0};gfg_frame_clock_pair(&disabled,t,3);
    assert(!disabled.real_ns && !disabled.resyncs);
    puts("frame-clock: source times, variable FPS/refresh, x2/x3, independent expiry, bounded latency and gaps PASS");
}
