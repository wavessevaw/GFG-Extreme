/* SPDX-License-Identifier: GPL-3.0-or-later
 * No artificial FPS claims: deterministic ownership/scheduling contract.
 * Synthetic surfaces in this test stand in for ALREADY COMPUTED GPU pixels.
 * Hardware pixel identity/scanout is tested separately.
 */
#include "../src/output_owner_queue.h"
#include <assert.h>
#include <stdio.h>
#include <inttypes.h>
#define MS 1000000ull
static gfg_foe_real input(unsigned seq,uint64_t at) {
    return (gfg_foe_real){.seq=seq,.surface_id=1000u+seq,.captured_ns=at,.ready_ns=at};
}
static gfg_foe_packet emit(gfg_foe *o,uint64_t now,gfg_foe_kind kind,
                           uint64_t from,uint64_t to,uint64_t surface) {
    gfg_foe_packet p={0};
    assert(gfg_foe_poll(o,now,&p)==GFG_FOE_OK);
    assert(p.kind==kind && p.from_seq==from && p.to_seq==to &&
           p.surface_id==surface);
    return p;
}
static void ordered_frames(void) {
    gfg_foe o;gfg_foe_init(&o,10*MS,250*MS,35*MS);
    assert(gfg_foe_on_real(&o,input(1,1000*MS),0,0)==GFG_FOE_OK);
    assert(!o.count && o.have_held);
    assert(gfg_foe_on_real(&o,input(2,1033*MS),2001,1037*MS)==GFG_FOE_OK);
    /* We only own a detached image of A, never borrow the game's swapchain. */
    emit(&o,1033*MS,GFG_FOE_REAL,1,1,1001);
    /* First synthetic is real GPU work and MUST NOT be shown until ready. */
    assert(gfg_foe_poll(&o,1042*MS,&(gfg_foe_packet){0})==GFG_FOE_WAIT);
    emit(&o,1043*MS,GFG_FOE_SYNTH,1,2,2001);
    assert(gfg_foe_on_real(&o,input(3,1066*MS),2002,1070*MS)==GFG_FOE_OK);
    emit(&o,1066*MS,GFG_FOE_REAL,2,2,1002);
    emit(&o,1076*MS,GFG_FOE_SYNTH,2,3,2002);
    /* At the end of a scene we MUST eventually release final B/C. */
    assert(gfg_foe_poll(&o,1110*MS,&(gfg_foe_packet){0})==GFG_FOE_WAIT ||
           !o.count); /* may have just flushed the last held image */
    if(o.have_held) assert(gfg_foe_flush_held(&o)==GFG_FOE_OK);
    if(o.count)emit(&o,1120*MS,GFG_FOE_REAL,3,3,1003);
    assert(o.forwarded_real==3 && o.forwarded_synthetic==2);
}
static void missed_synthetic_does_not_steal_real(void) {
    gfg_foe o;gfg_foe_init(&o,10*MS,250*MS,35*MS);
    assert(gfg_foe_on_real(&o,input(1,1000*MS),0,0)==GFG_FOE_OK);
    assert(gfg_foe_on_real(&o,input(2,1033*MS),2001,2000*MS)==GFG_FOE_OK);
    emit(&o,1033*MS,GFG_FOE_REAL,1,1,1001);
    assert(gfg_foe_on_real(&o,input(3,1066*MS),0,0)==GFG_FOE_OK);
    /* An unready synthetic must be dropped before forwarding REAL B.
       This is deliberate: do not keep drawing slow synthetic A->B when
       B has already arrived. */
    emit(&o,1066*MS,GFG_FOE_REAL,2,2,1002);
    assert(o.dropped_synthetic==1 && o.forwarded_synthetic==0);
    assert(gfg_foe_flush_held(&o)==GFG_FOE_OK);
    emit(&o,1076*MS,GFG_FOE_REAL,3,3,1003);
    assert(o.forwarded_real==3);
}
static void loading_gap_and_cut(void) {
    gfg_foe o;gfg_foe_init(&o,10*MS,250*MS,40*MS);
    assert(gfg_foe_on_real(&o,input(1,1000*MS),0,0)==GFG_FOE_OK);
    assert(gfg_foe_on_real(&o,input(2,1037*MS),2001,1040*MS)==GFG_FOE_OK);
    emit(&o,1037*MS,GFG_FOE_REAL,1,1,1001);
    emit(&o,1047*MS,GFG_FOE_SYNTH,1,2,2001);
    /* 836ms transition: never interpolate across the cut. */
    assert(gfg_foe_on_real(&o,input(3,1873*MS),9999,1875*MS)==GFG_FOE_OK);
    assert(o.discontinuities==1 && o.dropped_synthetic==1);
    emit(&o,1873*MS,GFG_FOE_REAL,2,2,1002);
    assert(gfg_foe_on_real(&o,input(4,1900*MS),2003,1902*MS)==GFG_FOE_OK);
    emit(&o,1900*MS,GFG_FOE_REAL,3,3,1003);
    emit(&o,1910*MS,GFG_FOE_SYNTH,3,4,2003);
    assert(gfg_foe_flush_held(&o)==GFG_FOE_OK);
    emit(&o,1920*MS,GFG_FOE_REAL,4,4,1004);
    assert(o.forwarded_real==4 && o.forwarded_synthetic==2);
}
static void stalled_stream_flushes_real(void) {
    gfg_foe o;gfg_foe_init(&o,10*MS,250*MS,40*MS);
    gfg_foe_packet p;
    assert(gfg_foe_on_real(&o,input(1,1000*MS),0,0)==GFG_FOE_OK);
    assert(gfg_foe_poll(&o,1039*MS,&p)==GFG_FOE_EMPTY);
    emit(&o,1040*MS,GFG_FOE_REAL,1,1,1001);
    assert(!o.have_held && !o.count);
}
static void bounded_backpressure(void) {
    gfg_foe o;gfg_foe_init(&o,10*MS,250*MS,35*MS);
    uint64_t now=1000*MS;
    assert(gfg_foe_on_real(&o,input(1,now),0,0)==GFG_FOE_OK);
    for(unsigned i=2;i<=17;i++) {
        now+=20*MS;
        assert(gfg_foe_on_real(&o,input(i,now),3000u+i,now+1)==GFG_FOE_OK);
    }
    assert(o.count==32);
    now+=20*MS;
    assert(gfg_foe_on_real(&o,input(18,now),3018,now+1)==GFG_FOE_BACKPRESSURE);
    assert(o.held.seq==17 && o.count==32 && o.backpressure==1);
    /* Drain space, retry the exact original real, no silent lost frame. */
    gfg_foe_packet p;
    assert(gfg_foe_poll(&o,now,&p)==GFG_FOE_OK);
    assert(p.kind==GFG_FOE_REAL && p.from_seq==1);
    assert(gfg_foe_on_real(&o,input(18,now),0,0)==GFG_FOE_OK);
    assert(o.held.seq==18);
}
int main(void) {
    ordered_frames();
    missed_synthetic_does_not_steal_real();
    loading_gap_and_cut();
    stalled_stream_flushes_real();
    bounded_backpressure();
    puts("GSF output-owner v0: A->Ahalf->B, GPU readiness, no dropped real, 836ms scene gap, bounded queue PASS");
    puts("NO Vulkan consumer, independent proxy swapchain, hardware scanout or in-game FPS is proven by this test");
    return 0;
}
