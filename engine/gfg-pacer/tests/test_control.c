/* Host tests for the control channel: seqlock, file policy, rate limit, version gate, env mode. */
#define _GNU_SOURCE
#include "../src/control.h"

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

/* The Governor's side: create the file and map it. */
static gfg_ctl_shm *governor_create(uint32_t version)
{
    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fd < 0 || ftruncate(fd, sizeof(gfg_ctl_shm)) != 0)
        return NULL;
    gfg_ctl_shm *m = mmap(NULL, sizeof(*m), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (m == MAP_FAILED)
        return NULL;
    gfg_ctl_init_header(m);
    m->version = version;
    return m;
}

static gfg_ctl_policy policy(double hz)
{
    gfg_ctl_policy p = { .enabled = 1, .tick_shaping = 1, .pacing = 1, .real_target_hz = hz, .margin_ms = 3.0 };
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
    uint64_t gen = st.generation;
    CHECK(m->writer_pid == (uint32_t)getpid(), "writer pid %u", m->writer_pid);

    p.real_target_hz = 30;
    gfg_ctl_write_policy(m, &p);
    gfg_ctl_poll(t + 50 * MS, &st);
    CHECK(st.policy.real_target_hz == 60 && st.generation == gen, "re-read before 100 ms");
    gfg_ctl_poll(t + 100 * MS, &st);
    CHECK(st.policy.real_target_hz == 30 && st.generation == gen + 1, "re-read after 100 ms: hz %.1f", st.policy.real_target_hz);
    t += 100 * MS;

    gfg_stats s = { .frames = 42, .hits = 40, .misses = 2, .cost_p50_ms = 5.0 };
    gfg_ctl_publish(&s, 123);
    gfg_ctl_telemetry r;
    CHECK(gfg_ctl_read_telemetry(m, &r) == 0 && r.frames == 42 && r.cost_p50_ms == 5.0 && r.last_present_ns == 123,
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
    gfg_ctl_shutdown();
    CHECK(gfg_ctl_poll(1, &st) == 0 && st.enabled && st.policy.real_target_hz == 45 && !st.policy.pacing &&
          st.policy.tick_shaping, "env policy");
    CHECK(access(path, F_OK) == 0, "env mode creates the file for telemetry");
    gfg_stats s = { .frames = 3 };
    gfg_ctl_publish(&s, 9);
    int fd = open(path, O_RDONLY);
    gfg_ctl_shm shm;
    CHECK(fd >= 0 && read(fd, &shm, sizeof(shm)) == (ssize_t)sizeof(shm) && shm.magic == GFG_CTL_MAGIC &&
          shm.telemetry.frames == 3, "telemetry in created file");
    if (fd >= 0)
        close(fd);
    gfg_ctl_shutdown();
    CHECK(access(path, F_OK) != 0, "created file removed at shutdown");
    unsetenv("GFG_FRAME_OS_ENABLE");
}

int main(void)
{
    snprintf(path, sizeof(path), "/dev/shm/gfg-frame-os-test-%d", (int)getpid());
    setenv("GFG_FRAME_OS_SHM", path, 1);
    test_seqlock();
    test_file_policy();
    test_env_mode();
    unlink(path);
    if (failures) {
        printf("%d control check(s) failed\n", failures);
        return 1;
    }
    printf("control channel: all checks passed\n");
    return 0;
}
