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
 * Test mode without the file: GFG_FRAME_OS_ENABLE=1 GFG_FRAME_OS_REAL_HZ=<hz>
 * [GFG_FRAME_OS_TICK_SHAPING=0|1] [GFG_FRAME_OS_PACING=0|1].  The policy then comes from the
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
#define GFG_CTL_VERSION 1u
#define GFG_CTL_POLL_NS 100000000ll /* policy re-read period */

typedef struct gfg_ctl_policy {
    uint32_t enabled;          /* 0: layer is pass-through */
    uint32_t tick_shaping;
    uint32_t pacing;
    uint32_t reserved;
    double real_target_hz;     /* <= 0: no grid */
    double margin_ms;          /* <= 0: scheduler default */
    double max_wait_ms;        /* <= 0: scheduler default */
} gfg_ctl_policy;

typedef struct gfg_ctl_telemetry {
    uint64_t frames;
    uint64_t hits;
    uint64_t misses;
    double cost_p50_ms;
    double cost_q_ms;
    double margin_ms;
    double avg_delay_ms;
    int64_t last_present_ns;   /* CLOCK_MONOTONIC */
} gfg_ctl_telemetry;

typedef struct gfg_ctl_shm {
    uint32_t magic;            /* @0  */
    uint32_t version;          /* @4  */
    uint32_t size;             /* @8  sizeof(gfg_ctl_shm) */
    uint32_t writer_pid;       /* @12 pid of the layer process publishing telemetry */
    uint32_t policy_seq;       /* @16 */
    uint32_t reserved0;
    gfg_ctl_policy policy;     /* @24 */
    uint32_t telemetry_seq;    /* @64 */
    uint32_t reserved1;
    gfg_ctl_telemetry telemetry; /* @72 */
} gfg_ctl_shm;                 /* 136 bytes */

/* Policy resolved for the scheduler; generation changes whenever the policy changes. */
typedef struct gfg_ctl_state {
    int enabled;
    uint64_t generation;
    gfg_policy policy;
} gfg_ctl_state;

/* Current policy; re-reads env/file at most every GFG_CTL_POLL_NS.  Thread-safe.
 * Returns 0, or -1 on an internal error (caller goes pass-through). */
int gfg_ctl_poll(int64_t now_ns, gfg_ctl_state *out);

/* Publish scheduler stats (thread-safe; no-op when no file is mapped). */
void gfg_ctl_publish(const gfg_stats *stats, int64_t last_present_ns);

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
