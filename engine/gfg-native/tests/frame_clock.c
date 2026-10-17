/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../src/frame_clock.h"
#include <assert.h>
#include <stdio.h>
static const uint64_t ns=1000000000ull;
static unsigned replay(unsigned fps,unsigned mul,unsigned n) {
    const uint64_t p=ns/90,origin=1000000000ull;
    gfg_frame_clock c={.period_ns=p};unsigned output=0;
    for(unsigned i=0;i<n;i++) {
        const uint64_t src=origin+(uint64_t)i*ns/fps;
        gfg_frame_clock_pair(&c,src,mul);
        assert(c.real_ns>=src && c.real_ns<=src+2*c.interval_ns);
        if(i && !c.discontinuity) {
            for(unsigned k=0;k<mul-1;k++)if(c.mask&(1u<<k)) {
                assert(c.target_ns[k]>=src && c.target_ns[k]<c.real_ns);
                assert(gfg_frame_clock_admit(&c,k,c.target_ns[k]-1));
                assert(!gfg_frame_clock_admit(&c,k,c.target_ns[k]));
                ++output;
            }
        }
    }
    printf("%u->90Hz x%u: %u admitted / %u real (resync=%llu)\n",
           fps,mul,output,n,(unsigned long long)c.resyncs);
    return output;
}
int main(void) {
    /* 27/42 -> 54/84: enough slots for one generator output per real frame. */
    assert(replay(27,2,600)>=590);
    assert(replay(42,2,600)>=590);
    /* 60 -> 90: every other source pair has an available synthetic slot.
     * Do NOT aim for 120 on a 90 Hz compositor. */
    const unsigned x2_60=replay(60,2,600);
    assert(x2_60>=290 && x2_60<=310);
    /* 30->90 x3: two synthetic slots per real. 60->90 x3 is limited. */
    assert(replay(30,3,600)>=1180);
    const unsigned x3_60=replay(60,3,600);
    assert(x3_60>=290 && x3_60<=310);
    assert(replay(90,2,600)==0);
    assert(replay(120,2,600)==0);
    /* Changing source and display refresh may re-anchor but cannot build
     * unbounded handoff delay or silently claim generated scanout. */
    gfg_frame_clock c={.period_ns=ns/90};uint64_t t=ns;
    for(unsigned i=0;i<400;i++) {
        uint64_t dt=i<100?ns/27:i<200?ns/60:i<300?ns/42:ns/27;
        t+=dt;gfg_frame_clock_pair(&c,t,2);
        assert(c.real_ns>=t && c.real_ns<=t+2*c.interval_ns);
    }
    c.period_ns=ns/60;t+=ns/27;gfg_frame_clock_pair(&c,t,2);
    assert(!c.mask && c.grid_period_ns==ns/60);
    t+=ns;gfg_frame_clock_pair(&c,t,2);
    assert(c.discontinuity && !c.mask);
    t+=ns/27;gfg_frame_clock_pair(&c,t,2);assert(c.real_ns>=t);
    /* New LAB buffered-output experiment: intentionally delay *both* real
     * and synthetic WSI handoffs, not just a generated frame. Ensure the
     * post-loading epoch gets viable slots again instead of starving. */
    const uint64_t display_p=ns/90;
    gfg_frame_clock buffered={.period_ns=display_p,.buffer_ticks=2};
    uint64_t captured=ns;
    gfg_frame_clock_pair(&buffered,captured,2);
    assert(buffered.real_ns==captured+4*display_p);
    unsigned before=0,after=0;
    for(unsigned i=0;i<140;i++) {
        captured+=(ns/27);
        gfg_frame_clock_pair(&buffered,captured,2);
        assert(buffered.real_ns>=captured);
        assert(buffered.real_ns<=captured+2*buffered.interval_ns+2*display_p);
        if(buffered.mask&1u) {
            assert(buffered.target_ns[0]>captured);
            assert(buffered.target_ns[0]<buffered.real_ns);
            ++before;
        }
    }
    assert(before>=130);
    captured+=836000000ull; /* representative loading gap from field trace */
    gfg_frame_clock_pair(&buffered,captured,2);
    assert(buffered.discontinuity && buffered.mask==0);
    unsigned restart_after=0;
    for(unsigned i=0;i<240;i++) {
        captured+=ns/38;
        gfg_frame_clock_pair(&buffered,captured,2);
        assert(buffered.real_ns>=captured);
        assert(buffered.real_ns<=captured+2*buffered.interval_ns+2*display_p);
        if(buffered.mask&1u) {
            if(!restart_after)restart_after=i+1;
            assert(buffered.target_ns[0]>captured);
            ++after;
        }
    }
    assert(restart_after>0 && restart_after<=6);
    assert(after>=195);
    /* 60->90 also needs to remain admissible despite the extra phase.
     * The old bound source+2*dt alone would reject every delayed target. */
    gfg_frame_clock buffered60={.period_ns=display_p,.buffer_ticks=2};
    unsigned mid=0;
    captured=ns;
    for(unsigned i=0;i<300;i++) {
        gfg_frame_clock_pair(&buffered60,captured,2);
        if(buffered60.mask&1u)++mid;
        captured+=ns/60;
    }
    assert(mid>=135 && mid<=160);
    printf("frame-clock: buffered 2 ticks 27->38 fps post-836ms gap=PASS (before=%u after=%u restart=%u, 60fps admitted=%u)\\n",before,after,restart_after,mid);
    gfg_frame_clock none={0};gfg_frame_clock_pair(&none,t,3);assert(!none.real_ns);
    puts("frame-clock: bounded 27/42/60/90Hz slots, x2/x3, rate transitions PASS");
}
