/* GFG Frame OS — control channel (Governor <-> layer).
 *
 * One fixed-layout file under /dev/shm, mmap'ed by both sides:
 *
 *   policy     written by the Governor, read by the layer (seqlock, re-read at most every ~100 ms)
 *   telemetry  written by the layer, read by the Governor (seqlock)
 *
 * Path: $GFG_FRAME_OS_SHM, default /dev/shm/gfg-frame-os-<pid>.  Missing file, short file, bad
 * magic or another version => disabled.  All fields little-endian host order, offsets below are
 * ABI (checked with static asserts); bump GFG_CTL_VERSION on any change.
 *
 * Seqlock protocol (both blocks): the writer stores seq+1 (odd = write in progress), writes the
 * fields, stores seq+2.  A reader copies the fields between two loads of seq and retries when
 * they differ or are odd.
 *
 * Heartbeat: the Governor rewrites policy.written_ns every tick; a policy whose written_ns is more
 * than GFG_CTL_HEARTBEAT_NS old counts as disabled (a dead Governor never leaves a policy acting).
 * The Governor also recreates the file when Frame OS is (re-)enabled and on its first open in a
 * process, so telemetry and policy from an earlier session are never read as current.
 *
 * Test mode without the file: GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=<hz>
 * [GFG_FRAME_OS_MODE=act|observe|shadow] [GFG_FRAME_OS_TICK_SHAPING=0|1] [GFG_FRAME_OS_PACING=0|1]
 * (generation 0, no heartbeat).  The policy then comes from the
 * environment; the layer creates the file itself (if absent) to publish telemetry and removes it
 * at exit.
 */
#ifndef GFG_CONTROL_H
#define GFG_CONTROL_H

#include <stdint.h>

#include "scheduler.h"

#ifdef __cplusplus
extern "C" {
#endif

#define GFG_CTL_MAGIC 0x43474647u   /* "GFGC" */
#define GFG_CTL_VERSION 3u
#define GFG_CTL_POLL_NS 100000000ll /* policy re-read period */
#define GFG_CTL_HEARTBEAT_NS 2000000000ll /* policy older than this (written_ns) => disabled */
#define GFG_CTL_TAKEOVER_NS 500000000ll   /* telemetry older than this may be taken over */
#define GFG_CTL_ENGINE_LEN 16

/* policy.mode */
/* Optional extension bits in policy.reserved / telemetry.reserved; layout stays v3.
 * A legacy layer ignores requests and advertises no support. Never infer support from config. */
#define GFG_POLICY_STALL_SHIELD 1u
#define GFG_SUPPORT_TICK_SHAPING 1u
#define GFG_SUPPORT_STALL_SHIELD 2u
#define GFG_ACTIVE_TICK_SHAPING (1u << 16)
#define GFG_ACTIVE_STALL_SHIELD (1u << 17)

#define GFG_MODE_ACT 0u       /* scheduler decides and the layer sleeps */
#define GFG_MODE_OBSERVE 1u   /* measure and publish only: no scheduler, no sleeps */
#define GFG_MODE_SHADOW 2u    /* scheduler decides, the layer never sleeps (what act would do) */

typedef struct gfg_ctl_policy {
    uint32_t enabled;          /* 0: layer is pass-through, nothing written */
    uint32_t tick_shaping;
    uint32_t pacing;
    uint32_t mode;             /* GFG_MODE_*; anything else => disabled */
    double real_target_hz;     /* <= 0: no grid */
    double margin_ms;          /* <= 0: scheduler default */
    double max_wait_ms;        /* <= 0: scheduler default */
    uint32_t generation;       /* Governor's policy id, echoed as telemetry.applied_generation */
    uint32_t reserved;
    int64_t written_ns;        /* CLOCK_MONOTONIC heartbeat, rewritten every Governor tick (10 Hz) */
} gfg_ctl_policy;              /* 56 bytes */

typedef struct gfg_ctl_telemetry {
    uint64_t frames;           /* presents since the layer was (re-)enabled */
    uint64_t hits;             /* act/shadow: scheduler slot hits (shadow: would-be) */
    uint64_t misses;
    double cost_p50_ms;        /* acquire return of the presented image -> present call */
    double cost_q_ms;          /* same, at the scheduler's cost quantile */
    double margin_ms;          /* act/shadow */
    double avg_delay_ms;       /* act/shadow: EWMA of frame-start delays (shadow: not applied) */
    double freshness_ms;       /* EWMA(0.05) of present return - frame start: age of the input */
    double present_interval_p50_ms; /* over the last 64 presents */
    double present_interval_p95_ms;
    int64_t last_present_ns;   /* CLOCK_MONOTONIC, when the present was forwarded */
    uint32_t applied_generation; /* policy.generation in effect (ack) */
    uint32_t swapchain_recreations; /* vkCreateSwapchainKHR calls after the first, per device */
    double present_hold_ms;    /* EWMA(0.05) of the present forward's duration (layers below: FG hold) */
    double acquire_block_ms;   /* EWMA(0.05) of the acquire forward's duration */
    int64_t last_present_return_ns; /* CLOCK_MONOTONIC, when the forwarded present returned */
    uint32_t passthrough;      /* 1: an internal error turned the layer into a pure forward */
    uint32_t reserved;
    char engine[GFG_CTL_ENGINE_LEN]; /* VkApplicationInfo.pEngineName (DXVK, vkd3d, ...), NUL-padded */
} gfg_ctl_telemetry;           /* 144 bytes */

typedef struct gfg_ctl_shm {
    uint32_t magic;            /* @0  */
    uint32_t version;          /* @4  */
    uint32_t size;             /* @8  sizeof(gfg_ctl_shm) = 232 */
    uint32_t writer_pid;       /* @12 pid of the layer process publishing telemetry (set on publish) */
    uint32_t policy_seq;       /* @16 */
    uint32_t reserved0;
    gfg_ctl_policy policy;     /* @24 */
    uint32_t telemetry_seq;    /* @80 */
    uint32_t reserved1;
    gfg_ctl_telemetry telemetry; /* @88 */
} gfg_ctl_shm;                 /* 232 bytes */

/* Policy resolved for the layer; serial changes whenever anything in it changes. */
typedef struct gfg_ctl_state {
    int enabled;
    uint32_t mode;
    uint32_t generation;       /* Governor's policy.generation (0 in env test mode) */
    uint64_t serial;
    gfg_policy policy;
} gfg_ctl_state;

/* Current policy; re-reads env/file at most every GFG_CTL_POLL_NS.  Thread-safe.
 * Returns 0, or -1 on an internal error (caller goes pass-through). */
int gfg_ctl_poll(int64_t now_ns, gfg_ctl_state *out);

/* Publish telemetry (thread-safe; no-op when no file is mapped).  Several processes may share the
 * file: only the writer_pid process writes, unless the telemetry there is GFG_CTL_TAKEOVER_NS
 * older than t->last_present_ns.  Returns 1 when written. */
int gfg_ctl_publish(const gfg_ctl_telemetry *t);

/* Flag telemetry.passthrough (same ownership rule as publish). */
void gfg_ctl_mark_passthrough(int64_t now_ns);

/* Unmap; unlinks the file if this process created it.  Also runs at process exit. */
void gfg_ctl_shutdown(void);

/* Seqlock helpers, also used by tests and by the Governor-side test tool. */
void gfg_ctl_write_policy(gfg_ctl_shm *shm, const gfg_ctl_policy *policy);
int gfg_ctl_read_policy(const gfg_ctl_shm *shm, gfg_ctl_policy *out);       /* 0 ok, -1 busy */
void gfg_ctl_write_telemetry(gfg_ctl_shm *shm, const gfg_ctl_telemetry *t);
int gfg_ctl_read_telemetry(const gfg_ctl_shm *shm, gfg_ctl_telemetry *out); /* 0 ok, -1 busy */
void gfg_ctl_init_header(gfg_ctl_shm *shm);
/* Resolves the path into buf; returns buf. */
const char *gfg_ctl_path(char *buf, unsigned long len);

#ifdef __cplusplus
}
#endif

#endif /* GFG_CONTROL_H */
