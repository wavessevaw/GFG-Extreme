/* SPDX-License-Identifier: GPL-3.0-or-later
 * GSF Frame Output Owner: deterministic offscreen-surface ordering contract.
 *
 * IMPORTANT: This is the scheduling/ownership MODEL, not a replacement for
 * vkCreateSwapchainKHR. The Vulkan adapter MUST copy source pixels into
 * separate owned images and MUST NOT retain/re-present app swapchain images.
 * Synthetic outputs MUST be backed by an actual finished GPU image. Neither
 * success here nor vkQueuePresentKHR success proves physical scanout.
 */
#ifndef GFG_OUTPUT_OWNER_QUEUE_H
#define GFG_OUTPUT_OWNER_QUEUE_H
#include <stdint.h>
#include <string.h>

#define GFG_FOE_CAPACITY 32u
typedef enum { GFG_FOE_REAL = 1, GFG_FOE_SYNTH = 2 } gfg_foe_kind;
typedef enum { GFG_FOE_EMPTY=0, GFG_FOE_OK=1, GFG_FOE_WAIT=2, GFG_FOE_BACKPRESSURE=3 } gfg_foe_result;

typedef struct {
    gfg_foe_kind kind;
    uint64_t epoch, from_seq, to_seq, surface_id, ready_ns, captured_ns;
} gfg_foe_packet;

typedef struct {
    uint64_t seq, surface_id, captured_ns, ready_ns;
} gfg_foe_real;

typedef struct {
    gfg_foe_packet packets[GFG_FOE_CAPACITY];
    unsigned count;
    gfg_foe_real held;
    int have_held;
    uint64_t epoch;
    uint64_t tick_ns, next_tick_ns, max_gap_ns, held_timeout_ns;
    uint64_t forwarded_real, forwarded_synthetic, dropped_synthetic;
    uint64_t discontinuities, backpressure;
} gfg_foe;

static inline void gfg_foe_init(gfg_foe *o, uint64_t refresh_period_ns,
                                uint64_t source_gap_ns, uint64_t source_hold_ns) {
    memset(o,0,sizeof(*o));
    o->epoch=1;
    o->tick_ns=refresh_period_ns;
    o->max_gap_ns=source_gap_ns;
    o->held_timeout_ns=source_hold_ns;
}
static inline int gfg_foe_enqueue(gfg_foe *o, gfg_foe_packet p) {
    if (o->count==GFG_FOE_CAPACITY) { ++o->backpressure; return 0; }
    o->packets[o->count++]=p;
    return 1;
}
static inline gfg_foe_packet gfg_foe_real_packet(const gfg_foe *o, gfg_foe_real r) {
    const gfg_foe_packet p={.kind=GFG_FOE_REAL,.epoch=o->epoch,
        .from_seq=r.seq,.to_seq=r.seq,.surface_id=r.surface_id,
        .ready_ns=r.ready_ns,.captured_ns=r.captured_ns};
    return p;
}
/* All source images in this API are already OWNED COPIES, not the game's
 * VkSwapchainKHR images. A synthetic ID of 0 means no GPU-generated image.
 * If enqueue returns BACKPRESSURE, ownership of the NEW real stays with
 * the caller and it MUST retry; no original frame is silently discarded.
 */
static inline gfg_foe_result gfg_foe_on_real(gfg_foe *o,gfg_foe_real current,
                uint64_t synthetic_surface, uint64_t synthetic_ready_ns) {
    if (!o || !o->tick_ns || !current.seq || !current.surface_id ||
        !current.ready_ns || (o->have_held && current.seq<=o->held.seq))
        return GFG_FOE_WAIT;
    if (!o->have_held) { o->held=current;o->have_held=1;return GFG_FOE_OK; }
    const int gap=current.captured_ns<=o->held.captured_ns ||
        current.captured_ns-o->held.captured_ns>o->max_gap_ns;
    /* Always enqueue the preceding real frame. A cut/long stall forbids
     * an invented interpolation across unrelated scene content. */
    if (o->count==GFG_FOE_CAPACITY) {
        ++o->backpressure;return GFG_FOE_BACKPRESSURE;
    }
    gfg_foe_real previous=o->held;
    if (gap) { ++o->epoch; ++o->discontinuities; }
    gfg_foe_enqueue(o,gfg_foe_real_packet(o,previous));
    if (!gap && synthetic_surface && current.seq==previous.seq+1 &&
        o->count<GFG_FOE_CAPACITY) {
        const gfg_foe_packet mid={.kind=GFG_FOE_SYNTH,.epoch=o->epoch,
            .from_seq=previous.seq,.to_seq=current.seq,
            .surface_id=synthetic_surface,.ready_ns=synthetic_ready_ns,
            .captured_ns=current.captured_ns};
        if(!synthetic_ready_ns || !gfg_foe_enqueue(o,mid))
            ++o->dropped_synthetic;
    } else if (synthetic_surface) ++o->dropped_synthetic;
    o->held=current;
    return GFG_FOE_OK;
}
static inline gfg_foe_result gfg_foe_flush_held(gfg_foe *o) {
    if (!o->have_held) return GFG_FOE_EMPTY;
    if (o->count==GFG_FOE_CAPACITY) {
        ++o->backpressure;return GFG_FOE_BACKPRESSURE;
    }
    gfg_foe_enqueue(o,gfg_foe_real_packet(o,o->held));
    o->have_held=0;return GFG_FOE_OK;
}
static inline void gfg_foe_shift(gfg_foe *o) {
    --o->count;
    if (o->count) memmove(o->packets,o->packets+1,
                          o->count*sizeof(o->packets[0]));
}
/* Call only on the SINGLE output thread. A busy game never manipulates this
 * queue directly. On load/timeout release its most recent real. Real images
 * are never dropped; an unready or expired synthetic is deliberately skipped.
 */
static inline gfg_foe_result gfg_foe_poll(gfg_foe *o,uint64_t now,
                                          gfg_foe_packet *out) {
    if (!o || !out || !o->tick_ns) return GFG_FOE_WAIT;
    if (!o->count && o->have_held &&
        now>=o->held.captured_ns &&
        now-o->held.captured_ns>=o->held_timeout_ns)
        (void)gfg_foe_flush_held(o);
    if (!o->count) return GFG_FOE_EMPTY;
    if (now<o->next_tick_ns) return GFG_FOE_WAIT;
    for (;;) {
        if(!o->count) return GFG_FOE_EMPTY;
        const gfg_foe_packet p=o->packets[0];
        /* A generated image not ready by this output slot is NOT displayed,
         * and no real image is held hostage for it. */
        if (p.kind==GFG_FOE_SYNTH &&
            (now<p.ready_ns ||
             (now>=p.captured_ns && now-p.captured_ns>o->max_gap_ns))) {
            ++o->dropped_synthetic;gfg_foe_shift(o);
            continue;
        }
        if (p.ready_ns>now) return GFG_FOE_WAIT;
        *out=p;gfg_foe_shift(o);
        if(p.kind==GFG_FOE_REAL)++o->forwarded_real;
        else ++o->forwarded_synthetic;
        /* Skip missed *clock slots*, never increase latency indefinitely. */
        o->next_tick_ns=now>o->next_tick_ns?now+o->tick_ns:o->next_tick_ns+o->tick_ns;
        return GFG_FOE_OK;
    }
}
#endif
