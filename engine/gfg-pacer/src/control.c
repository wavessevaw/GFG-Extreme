/* GFG Frame OS — control channel.  See control.h. */
#define _GNU_SOURCE
#include "control.h"

#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

_Static_assert(offsetof(gfg_ctl_shm, writer_pid) == 12, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy_seq) == 16, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy) == 24, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy.mode) == 36, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy.real_target_hz) == 40, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy.max_wait_ms) == 56, "abi");
_Static_assert(offsetof(gfg_ctl_shm, policy.generation) == 64, "abi");
_Static_assert(sizeof(gfg_ctl_policy) == 48, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry_seq) == 72, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry) == 80, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry.freshness_ms) == 136, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry.last_present_ns) == 160, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry.applied_generation) == 168, "abi");
_Static_assert(offsetof(gfg_ctl_shm, telemetry.swapchain_recreations) == 172, "abi");
_Static_assert(sizeof(gfg_ctl_telemetry) == 96, "abi");
_Static_assert(sizeof(gfg_ctl_shm) == 176, "abi");

#define SEQ_TRIES 64

/* ---- seqlock ---- */

static void seq_write(uint32_t *seq, void *dst, const void *src, size_t n)
{
    uint32_t s = __atomic_load_n(seq, __ATOMIC_RELAXED);
    __atomic_store_n(seq, s | 1u, __ATOMIC_RELAXED);    /* odd even if a writer died mid-way */
    __atomic_thread_fence(__ATOMIC_RELEASE);
    memcpy(dst, src, n);
    __atomic_store_n(seq, (s | 1u) + 1u, __ATOMIC_RELEASE);
}

static int seq_read(const uint32_t *seq, void *dst, const void *src, size_t n)
{
    for (int i = 0; i < SEQ_TRIES; i++) {
        uint32_t s1 = __atomic_load_n(seq, __ATOMIC_ACQUIRE);
        if (s1 & 1u)
            continue;
        memcpy(dst, src, n);
        __atomic_thread_fence(__ATOMIC_ACQUIRE);
        if (__atomic_load_n(seq, __ATOMIC_RELAXED) == s1)
            return 0;
    }
    return -1;
}

void gfg_ctl_write_policy(gfg_ctl_shm *shm, const gfg_ctl_policy *p)
{
    seq_write(&shm->policy_seq, &shm->policy, p, sizeof(*p));
}

int gfg_ctl_read_policy(const gfg_ctl_shm *shm, gfg_ctl_policy *out)
{
    return seq_read(&shm->policy_seq, out, &shm->policy, sizeof(*out));
}

void gfg_ctl_write_telemetry(gfg_ctl_shm *shm, const gfg_ctl_telemetry *t)
{
    seq_write(&shm->telemetry_seq, &shm->telemetry, t, sizeof(*t));
}

int gfg_ctl_read_telemetry(const gfg_ctl_shm *shm, gfg_ctl_telemetry *out)
{
    return seq_read(&shm->telemetry_seq, out, &shm->telemetry, sizeof(*out));
}

void gfg_ctl_init_header(gfg_ctl_shm *shm)
{
    memset(shm, 0, sizeof(*shm));
    shm->size = sizeof(*shm);
    shm->version = GFG_CTL_VERSION;
    __atomic_store_n(&shm->magic, GFG_CTL_MAGIC, __ATOMIC_RELEASE);   /* magic last: header valid */
}

const char *gfg_ctl_path(char *buf, unsigned long len)
{
    const char *env = getenv("GFG_FRAME_OS_SHM");
    if (env && *env)
        snprintf(buf, len, "%s", env);
    else
        snprintf(buf, len, "/dev/shm/gfg-frame-os-%d", (int)getpid());
    return buf;
}

/* ---- process state ---- */

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static int g_init;
static pid_t g_pid;
static char g_path[512];
static gfg_ctl_shm *g_shm;     /* mapping of g_path, or NULL */
static dev_t g_dev;
static ino_t g_ino;
static int g_created;          /* we created g_path (env test mode): unlink at exit */
static int g_env_enabled;
static uint32_t g_env_mode;
static gfg_policy g_env_policy;
static int64_t g_next_poll;
static gfg_ctl_state g_state;

static int env_int(const char *name, int def)
{
    const char *v = getenv(name);
    return (v && *v) ? atoi(v) : def;
}

/* Control-channel policy -> scheduler policy; 0 when the values are not sane. */
static int to_sched_policy(const gfg_ctl_policy *c, gfg_policy *out)
{
    gfg_policy_defaults(out);
    if (!isfinite(c->real_target_hz) || c->real_target_hz < 0 || c->real_target_hz > 1000 ||
        !isfinite(c->margin_ms) || c->margin_ms > 100 || !isfinite(c->max_wait_ms) || c->max_wait_ms > 100 ||
        c->mode > GFG_MODE_SHADOW)
        return 0;
    out->real_target_hz = c->real_target_hz;
    out->tick_shaping = c->tick_shaping != 0;
    out->pacing = c->pacing != 0;
    if (c->margin_ms > 0)
        out->margin_ms = c->margin_ms;
    if (c->max_wait_ms > 0)
        out->max_wait_ms = c->max_wait_ms;
    return 1;
}

static void unmap(void)
{
    if (g_shm)
        munmap(g_shm, sizeof(*g_shm));
    g_shm = NULL;
    g_created = 0;
}

static int header_ok(const gfg_ctl_shm *shm)
{
    return __atomic_load_n(&shm->magic, __ATOMIC_ACQUIRE) == GFG_CTL_MAGIC &&
           shm->version == GFG_CTL_VERSION && shm->size >= sizeof(gfg_ctl_shm);
}

/* Keep g_shm in sync with the file at g_path (the Governor may recreate it). */
static void sync_mapping(void)
{
    struct stat st;
    if (stat(g_path, &st) != 0) {
        unmap();
        if (!g_env_enabled)
            return;
        /* test mode: create the file to publish telemetry */
        int fd = open(g_path, O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
        if (fd < 0)
            return;
        void *m = MAP_FAILED;
        if (ftruncate(fd, sizeof(gfg_ctl_shm)) == 0 && fstat(fd, &st) == 0)
            m = mmap(NULL, sizeof(gfg_ctl_shm), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        close(fd);
        if (m == MAP_FAILED) {
            unlink(g_path);
            return;
        }
        g_shm = m;
        g_created = 1;
        g_dev = st.st_dev;
        g_ino = st.st_ino;
        gfg_ctl_init_header(g_shm);
        g_shm->writer_pid = (uint32_t)g_pid;
        return;
    }
    if (g_shm && st.st_dev == g_dev && st.st_ino == g_ino)
        return;
    unmap();
    int fd = open(g_path, O_RDWR | O_CLOEXEC);
    if (fd < 0)
        return;
    if (fstat(fd, &st) == 0 && S_ISREG(st.st_mode) && st.st_size >= (off_t)sizeof(gfg_ctl_shm)) {
        void *m = mmap(NULL, sizeof(gfg_ctl_shm), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (m != MAP_FAILED) {
            g_shm = m;
            g_dev = st.st_dev;
            g_ino = st.st_ino;
            if (header_ok(g_shm))
                g_shm->writer_pid = (uint32_t)g_pid;
        }
    }
    close(fd);
}

static void init_locked(void)
{
    g_init = 1;
    g_pid = getpid();
    g_shm = NULL;            /* after fork: the parent's mapping is not ours to use */
    g_created = 0;
    g_next_poll = 0;
    gfg_ctl_path(g_path, sizeof(g_path));
    g_env_enabled = env_int("GFG_FRAME_OS_ENABLE", 0) == 1;
    if (g_env_enabled) {
        gfg_ctl_policy c = {0};
        const char *hz = getenv("GFG_FRAME_OS_REAL_HZ");
        c.enabled = 1;
        c.real_target_hz = hz ? strtod(hz, NULL) : 0.0;
        c.tick_shaping = (uint32_t)env_int("GFG_FRAME_OS_TICK_SHAPING", 1);
        c.pacing = (uint32_t)env_int("GFG_FRAME_OS_PACING", 1);
        const char *mode = getenv("GFG_FRAME_OS_MODE");
        if (!mode || !*mode || !strcmp(mode, "act"))
            c.mode = GFG_MODE_ACT;
        else if (!strcmp(mode, "observe"))
            c.mode = GFG_MODE_OBSERVE;
        else if (!strcmp(mode, "shadow"))
            c.mode = GFG_MODE_SHADOW;
        else
            c.mode = 0xffffffffu;   /* unknown: rejected below => disabled */
        g_env_mode = c.mode;
        if (!to_sched_policy(&c, &g_env_policy))
            g_env_enabled = 0;
    }
}

int gfg_ctl_poll(int64_t now_ns, gfg_ctl_state *out)
{
    if (pthread_mutex_lock(&g_lock) != 0)
        return -1;
    if (!g_init || g_pid != getpid())
        init_locked();
    if (now_ns >= g_next_poll) {
        g_next_poll = now_ns + GFG_CTL_POLL_NS;
        sync_mapping();
        gfg_ctl_state n = { .enabled = 0 };
        gfg_policy_defaults(&n.policy);
        if (g_env_enabled) {
            n.enabled = 1;
            n.mode = g_env_mode;
            n.policy = g_env_policy;
        } else if (g_shm && header_ok(g_shm)) {
            gfg_ctl_policy c;
            if (gfg_ctl_read_policy(g_shm, &c) != 0) {
                n = g_state;                 /* writer busy: keep the last policy */
            } else if (c.enabled == 1 && to_sched_policy(&c, &n.policy)) {
                n.enabled = 1;
                n.mode = c.mode;
                n.generation = c.generation;
            }
        }
        if (!n.enabled) {
            gfg_policy_defaults(&n.policy);
            n.mode = 0;
            n.generation = 0;
        }
        if (n.enabled != g_state.enabled || n.mode != g_state.mode || n.generation != g_state.generation ||
            memcmp(&n.policy, &g_state.policy, sizeof(n.policy)) != 0) {
            n.serial = g_state.serial + 1;
            g_state = n;
        }
    }
    *out = g_state;
    pthread_mutex_unlock(&g_lock);
    return 0;
}

void gfg_ctl_publish(const gfg_ctl_telemetry *t)
{
    if (pthread_mutex_lock(&g_lock) != 0)
        return;
    if (g_shm && g_pid == getpid() && header_ok(g_shm))
        gfg_ctl_write_telemetry(g_shm, t);   /* one writer at a time: under g_lock */
    pthread_mutex_unlock(&g_lock);
}

void gfg_ctl_shutdown(void)
{
    if (pthread_mutex_lock(&g_lock) != 0)
        return;
    if (g_init && g_pid == getpid()) {
        if (g_created)
            unlink(g_path);
        unmap();
    }
    g_init = 0;
    pthread_mutex_unlock(&g_lock);
}

__attribute__((destructor)) static void ctl_fini(void)
{
    gfg_ctl_shutdown();
}
