/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/frame_clock.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    const uint64_t p=1000000000ull/90,t=1000000000ull;
    gfg_frame_clock c={.period_ns=p};
    gfg_frame_clock_pair(&c,t);
    for(unsigned k=0;k<3;++k)assert(gfg_frame_clock_target(&c,k)==t+(k+1)*p);
    uint64_t first=c.real_ns;
    gfg_frame_clock_pair(&c,t+3*p);
    assert(gfg_frame_clock_target(&c,0)==first+p && c.real_ns==first+3*p);
    /* Missing synthetic slots leave the real-frame deadline on its own slot. */
    assert(gfg_frame_clock_target(&c,2)==t+6*p && c.resyncs==0);
    /* A late source cannot dump three expired outputs into WSI at once. */
    gfg_frame_clock_pair(&c,t+100*p);
    assert(c.resyncs==1 && gfg_frame_clock_target(&c,0)==t+101*p);
    assert(c.real_ns==t+103*p);
    gfg_frame_clock disabled={0};gfg_frame_clock_pair(&disabled,t);
    assert(!disabled.real_ns && !disabled.resyncs);
    puts("frame-clock: lookahead, G1/G2/R deadlines, skip slots and late resync PASS");
}
