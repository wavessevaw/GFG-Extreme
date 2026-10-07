/* Host tests for the control channel (seqlock, file policy, rate limit, version gate, modes,
 * generation, env mode) and the layer-side metrics. */
#define _GNU_SOURCE
#include "../src/control.h"
#include "../src/metrics.h"

#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); } } while (0)

#define MS 1000000ll

static char path[256];

/* The Governor's side: create the file (file_size bytes) and map it. */
static gfg_ctl_shm *governor_create_sized(uint32_t version, size_t file_size)
{
    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fd < 0 || ftruncate(fd, (off_t)file_size) != 0)
        return NULL;
    gfg_ctl_shm *m = mmap(NULL, sizeof(*m), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (m == MAP_FAILED)
        return NULL;
    gfg_ctl_init_header(m);
    m->version = version;
    if (file_size < sizeof(gfg_ctl_shm))
        m->size = (uint32_t)file_size;
    return m;
}

static gfg_ctl_shm *governor_create(uint32_t version)
{
    return governor_create_sized(version, sizeof(gfg_ctl_shm));
}

static gfg_ctl_policy policy(double hz)
{
    gfg_ctl_policy p = { .enabled = 1, .tick_shaping = 1, .pacing = 1, .mode = GFG_MODE_ACT, .real_target_hz = hz,
                         .margin_ms = 3.0 };
    return p;
}

static void test_seqlock(void)
{
    gfg_ctl_shm shm;
    gfg_ctl_init_header(&shm);
    gfg_ctl_policy in = policy(60), out;
    gfg_ctl_write_policy(&shm, &in);
    CHECK(gfg_ctl_read_policy(&shm, &out) == 0 && out.real_target_hz == 60 && out.margin_ms == 3.0, "policy roundtrip");
    CHECK(shm.policy_seq == 2, "seq %u", shm.policy_seq);
    shm.policy_seq = 3;   /* writer mid-update */
    CHECK(gfg_ctl_read_policy(&shm, &out) == -1, "odd seq must read as busy");
    gfg_ctl_write_policy(&shm, &in);   /* a writer that died mid-way is recovered by the next one */
    CHECK(shm.policy_seq == 4 && gfg_ctl_read_policy(&shm, &out) == 0, "seq recovery %u", shm.policy_seq);
    gfg_ctl_telemetry t = { .frames = 7, .hits = 6, .misses = 1, .avg_delay_ms = 4.5 }, r;
    gfg_ctl_write_telemetry(&shm, &t);
    CHECK(gfg_ctl_read_telemetry(&shm, &r) == 0 && r.frames == 7 && r.avg_delay_ms == 4.5, "telemetry roundtrip");
}

static void test_file_policy(void)
{
    gfg_ctl_state st;
    int64_t t = 1000 * MS;
    unlink(path);
    gfg_ctl_shutdown();
    CHECK(gfg_ctl_poll(t, &st) == 0 && !st.enabled, "missing file must be disabled");

    gfg_ctl_shm *m = governor_create(GFG_CTL_VERSION);
    CHECK(m != NULL, "create %s", path);
    if (!m)
        return;
    gfg_ctl_policy p = policy(60);
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    CHECK(gfg_ctl_poll(t, &st) == 0 && st.enabled && st.policy.real_target_hz == 60 && st.policy.margin_ms == 3.0,
          "file policy enabled=%d hz=%.1f", st.enabled, st.policy.real_target_hz);
    uint64_t serial = st.serial;
    CHECK(st.mode == GFG_MODE_ACT && st.generation == 0, "mode act, generation 0");
    CHECK(m->writer_pid == (uint32_t)getpid(), "writer pid %u", m->writer_pid);

    p.real_target_hz = 30;
    gfg_ctl_write_policy(m, &p);
    gfg_ctl_poll(t + 50 * MS, &st);
    CHECK(st.policy.real_target_hz == 60 && st.serial == serial, "re-read before 100 ms");
    gfg_ctl_poll(t + 100 * MS, &st);
    CHECK(st.policy.real_target_hz == 30 && st.serial == serial + 1, "re-read after 100 ms: hz %.1f", st.policy.real_target_hz);
    t += 100 * MS;

    p.generation = 7;   /* same policy, new id: still a change (the ack must follow) */
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(st.generation == 7 && st.serial == serial + 2, "generation %u", st.generation);

    p.mode = GFG_MODE_OBSERVE;
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(st.enabled && st.mode == GFG_MODE_OBSERVE, "mode observe");
    p.mode = GFG_MODE_SHADOW;
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(st.enabled && st.mode == GFG_MODE_SHADOW, "mode shadow");
    p.mode = 3;
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "unknown mode must be disabled");
    p.mode = GFG_MODE_ACT;

    gfg_ctl_telemetry tel = { .frames = 42, .hits = 40, .misses = 2, .cost_p50_ms = 5.0, .freshness_ms = 9.5,
                              .last_present_ns = 123, .applied_generation = 7, .swapchain_recreations = 2 };
    gfg_ctl_publish(&tel);
    gfg_ctl_telemetry r;
    CHECK(gfg_ctl_read_telemetry(m, &r) == 0 && r.frames == 42 && r.cost_p50_ms == 5.0 && r.last_present_ns == 123 &&
          r.freshness_ms == 9.5 && r.applied_generation == 7 && r.swapchain_recreations == 2,
          "telemetry frames %llu", (unsigned long long)r.frames);

    p.real_target_hz = NAN;
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "NaN policy must be disabled");

    p = policy(60);
    p.enabled = 0;
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "enabled=0");

    munmap(m, sizeof(*m));
    m = governor_create(GFG_CTL_VERSION + 1);   /* recreated file, other version */
    p = policy(60);
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "version mismatch must be disabled");


    munmap(m, sizeof(*m));
    m = governor_create(GFG_CTL_VERSION);       /* recreated again (new inode), right version */
    gfg_ctl_write_policy(m, &p);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(st.enabled && st.policy.real_target_hz == 60, "remap after recreate");
    munmap(m, sizeof(*m));
    m = governor_create_sized(1, 136);          /* a version-1 file (136 bytes), policy enabled */
    gfg_ctl_write_policy(m, &p);               /* v1 had enabled/hz at the same offsets */
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "version-1 file must be disabled");
    munmap(m, sizeof(*m));
    unlink(path);
    t += 100 * MS;
    gfg_ctl_poll(t, &st);
    CHECK(!st.enabled, "file removed");
    gfg_ctl_shutdown();
}

static void test_env_mode(void)
{
    gfg_ctl_state st;
    unlink(path);
    setenv("GFG_FRAME_OS_ENABLE", "1", 1);
    setenv("GFG_FRAME_OS_REAL_HZ", "45", 1);
    setenv("GFG_FRAME_OS_PACING", "0", 1);
    setenv("GFG_FRAME_OS_MODE", "bogus", 1);
    gfg_ctl_shutdown();
    CHECK(gfg_ctl_poll(1, &st) == 0 && !st.enabled && access(path, F_OK) != 0, "unknown env mode must be disabled");
    setenv("GFG_FRAME_OS_MODE", "shadow", 1);
    gfg_ctl_shutdown();
    CHECK(gfg_ctl_poll(1, &st) == 0 && st.enabled && st.policy.real_target_hz == 45 && !st.policy.pacing &&
          st.policy.tick_shaping && st.mode == GFG_MODE_SHADOW && st.generation == 0, "env policy");
    CHECK(access(path, F_OK) == 0, "env mode creates the file for telemetry");
    gfg_ctl_telemetry tel = { .frames = 3 };
    gfg_ctl_publish(&tel);
    int fd = open(path, O_RDONLY);
    gfg_ctl_shm shm;
    CHECK(fd >= 0 && read(fd, &shm, sizeof(shm)) == (ssize_t)sizeof(shm) && shm.magic == GFG_CTL_MAGIC &&
          shm.telemetry.frames == 3, "telemetry in created file");
    if (fd >= 0)
        close(fd);
    gfg_ctl_shutdown();
    CHECK(access(path, F_OK) != 0, "created file removed at shutdown");
    unsetenv("GFG_FRAME_OS_ENABLE");
    unsetenv("GFG_FRAME_OS_MODE");
}

static void test_metrics(void)
{
    gfg_ring r = {0};
    CHECK(gfg_ring_quantile(&r, 0.5) == 0, "empty ring");
    for (int i = 1; i <= 100; i++)
        gfg_ring_push(&r, i);                   /* keeps the last 64: 37..100 */
    CHECK(r.count == GFG_RING_LEN && gfg_ring_quantile(&r, 0) == 37 && gfg_ring_quantile(&r, 1) == 100,
          "ring window %.0f..%.0f", gfg_ring_quantile(&r, 0), gfg_ring_quantile(&r, 1));
    CHECK(fabs(gfg_ring_quantile(&r, 0.5) - 68.5) <= 0.5, "p50 %.1f", gfg_ring_quantile(&r, 0.5));

    /* 60 Hz presents; frame starts 10 ms before the release, ready 4 ms after the start */
    gfg_metrics m;
    gfg_metrics_reset(&m);
    int64_t t = 1000 * MS;
    for (int i = 0; i < 100; i++) {
        int64_t release = t + i * 16666667ll;
        gfg_metrics_frame_start(&m, release - 10 * MS);
        gfg_metrics_ready(&m, release - 6 * MS);
        gfg_metrics_released(&m, release);
    }
    CHECK(m.frames == 100, "frames %llu", (unsigned long long)m.frames);
    CHECK(fabs(m.freshness_ms - 10.0) < 1e-6, "freshness %.3f", m.freshness_ms);
    CHECK(fabs(gfg_ring_quantile(&m.costs_ms, 0.5) - 4.0) < 1e-6, "cost p50 %.3f", gfg_ring_quantile(&m.costs_ms, 0.5));
    CHECK(fabs(gfg_ring_quantile(&m.intervals_ms, 0.95) - 16.667) < 0.01, "interval p95 %.3f",
          gfg_ring_quantile(&m.intervals_ms, 0.95));
    /* EWMA: one 30 ms-old frame moves freshness by alpha * 20 ms */
    gfg_metrics_frame_start(&m, t + 100 * 16666667ll - 30 * MS);
    gfg_metrics_released(&m, t + 100 * 16666667ll);
    CHECK(fabs(m.freshness_ms - (10.0 + GFG_FRESHNESS_ALPHA * 20.0)) < 1e-6, "freshness EWMA %.3f", m.freshness_ms);
    /* present without a known start: no freshness/cost sample, still counted */
    gfg_metrics_released(&m, t + 101 * 16666667ll);
    CHECK(m.frames == 102 && fabs(m.freshness_ms - 11.0) < 1e-6, "no-start present");
}

int main(void)
{
    snprintf(path, sizeof(path), "/dev/shm/gfg-frame-os-test-%d", (int)getpid());
    setenv("GFG_FRAME_OS_SHM", path, 1);
    test_seqlock();
    test_file_policy();
    test_env_mode();
    test_metrics();
    unlink(path);
    if (failures) {
        printf("%d control check(s) failed\n", failures);
        return 1;
    }
    printf("control channel + metrics: all checks passed\n");
    return 0;
}
