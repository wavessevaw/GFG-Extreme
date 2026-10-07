/* Integration test: a tiny Vulkan "game" (headless surface + swapchain on the mock ICD) that
 * loops acquire/present through the real loader with VK_LAYER_GFG_pacer as an implicit layer.
 *
 *   test_layer env    N   layer enabled from env (GFG_FRAME_OS_ENABLE/REAL_HZ/MODE):
 *                         act: paced + telemetry; observe: measured, not paced;
 *                         shadow: scheduler decisions reported, not paced
 *   test_layer file   N   this process plays Governor: writes the policy file, then flips it
 *                         (60 Hz gen 7 -> disabled -> swapchain recreated -> 30 Hz gen 8)
 *   test_layer off    N   layer not enabled: must not pace, must not create the file
 *   test_layer badver N   version-1 and version-2 policy files (enabled): foreign, must not pace or
 *                         be written
 *   test_layer dxvk   N   DXVK/vkd3d-like: two swapchains, each image presented 6 ms after its own
 *                         acquire, acquires interleaved (env-enabled observe mode)
 *
 * The mock ICD presents instantly, so any pacing measured here comes from the layer. */
#define _GNU_SOURCE
#include "../src/control.h"

#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#include <vulkan/vulkan.h>

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); } \
    else { printf("PASS "); } printf(__VA_ARGS__); printf("\n"); } while (0)
#define VKCHECK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
    printf("FAIL %s:%d: %s -> %d\n", __FILE__, __LINE__, #call, r_); exit(1); } } while (0)

typedef struct app {
    VkInstance inst;
    VkDevice dev;
    VkQueue queue;
    VkSurfaceKHR surface, surface2;
    VkSwapchainKHR swapchain, swapchain2;   /* swapchain2: dxvk mode only */
    VkSwapchainCreateInfoKHR sci;
    VkFence fence;
} app;

static char path[512];
/* file mode: this process plays Governor and keeps the policy heartbeat fresh while it runs */
static gfg_ctl_shm *g_gov;
static gfg_ctl_policy g_gov_policy;
static int g_two_swapchains;

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void sleep_ms(int ms)
{
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000l };
    nanosleep(&ts, NULL);
}

static void governor_write(gfg_ctl_shm *m, const gfg_ctl_policy *p, int64_t age_ns)
{
    g_gov = m;
    g_gov_policy = *p;
    g_gov_policy.written_ns = (int64_t)(now_s() * 1e9) - age_ns;
    gfg_ctl_write_policy(m, &g_gov_policy);
}

static void governor_heartbeat(void)
{
    if (g_gov && (int64_t)(now_s() * 1e9) - g_gov_policy.written_ns > 100000000ll)
        governor_write(g_gov, &g_gov_policy, 0);
}

static int has_instance_ext(const char *name)
{
    uint32_t n = 0;
    vkEnumerateInstanceExtensionProperties(NULL, &n, NULL);
    VkExtensionProperties *p = calloc(n, sizeof(*p));
    vkEnumerateInstanceExtensionProperties(NULL, &n, p);
    int found = 0;
    for (uint32_t i = 0; i < n; i++)
        found |= !strcmp(p[i].extensionName, name);
    free(p);
    return found;
}

static void app_init(app *a)
{
    const char *iext[] = { VK_KHR_SURFACE_EXTENSION_NAME, VK_EXT_HEADLESS_SURFACE_EXTENSION_NAME };
    const char *dext[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
    if (!has_instance_ext(VK_EXT_HEADLESS_SURFACE_EXTENSION_NAME)) {
        printf("FAIL: driver has no VK_EXT_headless_surface\n");
        exit(1);
    }
    VkApplicationInfo ai = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName = "gfg-pacer-test",
                             .pEngineName = "gfg-test-engine-long-name",
                             .apiVersion = VK_API_VERSION_1_3 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &ai,
                                 .enabledExtensionCount = 2, .ppEnabledExtensionNames = iext };
    VKCHECK(vkCreateInstance(&ici, NULL, &a->inst));

    uint32_t n = 1;
    VkPhysicalDevice phys;
    VkResult r = vkEnumeratePhysicalDevices(a->inst, &n, &phys);
    if ((r != VK_SUCCESS && r != VK_INCOMPLETE) || n == 0) {
        printf("FAIL: no physical device\n");
        exit(1);
    }
    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = 0,
                                    .queueCount = 1, .pQueuePriorities = &prio };
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1,
                               .pQueueCreateInfos = &qci, .enabledExtensionCount = 1, .ppEnabledExtensionNames = dext };
    VKCHECK(vkCreateDevice(phys, &dci, NULL, &a->dev));
    vkGetDeviceQueue(a->dev, 0, 0, &a->queue);

    PFN_vkCreateHeadlessSurfaceEXT create_headless =
        (PFN_vkCreateHeadlessSurfaceEXT)vkGetInstanceProcAddr(a->inst, "vkCreateHeadlessSurfaceEXT");
    VkHeadlessSurfaceCreateInfoEXT hci = { .sType = VK_STRUCTURE_TYPE_HEADLESS_SURFACE_CREATE_INFO_EXT };
    VKCHECK(create_headless(a->inst, &hci, NULL, &a->surface));
    VkBool32 supported = VK_FALSE;
    VKCHECK(vkGetPhysicalDeviceSurfaceSupportKHR(phys, 0, a->surface, &supported));

    VkSwapchainCreateInfoKHR sci = {
        .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR, .surface = a->surface, .minImageCount = 3,
        .imageFormat = VK_FORMAT_B8G8R8A8_UNORM, .imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR,
        .imageExtent = { 64, 64 }, .imageArrayLayers = 1, .imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
        .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE, .preTransform = VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR,
        .compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR, .presentMode = VK_PRESENT_MODE_FIFO_KHR,
        .clipped = VK_TRUE,
    };
    a->sci = sci;
    VKCHECK(vkCreateSwapchainKHR(a->dev, &sci, NULL, &a->swapchain));
    VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VKCHECK(vkCreateFence(a->dev, &fci, NULL, &a->fence));
    a->surface2 = VK_NULL_HANDLE;
    a->swapchain2 = VK_NULL_HANDLE;
    if (g_two_swapchains) {
        VKCHECK(create_headless(a->inst, &hci, NULL, &a->surface2));
        sci.surface = a->surface2;
        VKCHECK(vkCreateSwapchainKHR(a->dev, &sci, NULL, &a->swapchain2));
    }
    printf("instance/device/headless swapchain(s) created (supported=%u)\n", supported);
}

/* What a game does on resize / mode switch. */
static void app_recreate_swapchain(app *a)
{
    VkSwapchainKHR old = a->swapchain;
    a->sci.oldSwapchain = old;
    a->sci.imageExtent.width = 128;
    VKCHECK(vkCreateSwapchainKHR(a->dev, &a->sci, NULL, &a->swapchain));
    vkDestroySwapchainKHR(a->dev, old, NULL);
}

static void app_destroy(app *a)
{
    vkDestroyFence(a->dev, a->fence, NULL);
    vkDestroySwapchainKHR(a->dev, a->swapchain, NULL);
    if (a->swapchain2)
        vkDestroySwapchainKHR(a->dev, a->swapchain2, NULL);
    vkDestroyDevice(a->dev, NULL);
    vkDestroySurfaceKHR(a->inst, a->surface, NULL);
    if (a->surface2)
        vkDestroySurfaceKHR(a->inst, a->surface2, NULL);
    vkDestroyInstance(a->inst, NULL);
}

/* n frames of acquire -> (no work) -> present; returns elapsed seconds. */
static double run_frames(app *a, int n)
{
    double t0 = now_s();
    for (int i = 0; i < n; i++) {
        uint32_t idx = 0;
        governor_heartbeat();
        VKCHECK(vkAcquireNextImageKHR(a->dev, a->swapchain, UINT64_MAX, VK_NULL_HANDLE, a->fence, &idx));
        VKCHECK(vkWaitForFences(a->dev, 1, &a->fence, VK_TRUE, UINT64_MAX));
        VKCHECK(vkResetFences(a->dev, 1, &a->fence));
        VkPresentInfoKHR pi = { .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .swapchainCount = 1,
                                .pSwapchains = &a->swapchain, .pImageIndices = &idx };
        VKCHECK(vkQueuePresentKHR(a->queue, &pi));
    }
    return now_s() - t0;
}

static void acquire(app *a, VkSwapchainKHR sc, uint32_t *idx)
{
    VKCHECK(vkAcquireNextImageKHR(a->dev, sc, UINT64_MAX, VK_NULL_HANDLE, a->fence, idx));
    VKCHECK(vkWaitForFences(a->dev, 1, &a->fence, VK_TRUE, UINT64_MAX));
    VKCHECK(vkResetFences(a->dev, 1, &a->fence));
}

static void present(app *a, VkSwapchainKHR sc, uint32_t idx)
{
    VkPresentInfoKHR pi = { .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .swapchainCount = 1, .pSwapchains = &sc,
                            .pImageIndices = &idx };
    VKCHECK(vkQueuePresentKHR(a->queue, &pi));
}

static gfg_ctl_shm *map_file(int create, uint32_t version, size_t file_size)
{
    int fd = open(path, O_RDWR | (create ? O_CREAT | O_TRUNC : 0), 0600);
    if (fd < 0)
        return NULL;
    if (create && ftruncate(fd, (off_t)file_size) != 0) {
        close(fd);
        return NULL;
    }
    gfg_ctl_shm *m = mmap(NULL, sizeof(*m), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (m == MAP_FAILED)
        return NULL;
    if (create) {
        gfg_ctl_init_header(m);
        m->version = version;
        m->size = (uint32_t)file_size;
    }
    return m;
}

static gfg_ctl_telemetry telemetry(const gfg_ctl_shm *m)
{
    gfg_ctl_telemetry t = {0};
    if (m && gfg_ctl_read_telemetry(m, &t) != 0)
        printf("telemetry busy\n");
    printf("telemetry: frames=%llu hits=%llu misses=%llu cost_p50=%.3fms cost_q=%.3fms margin=%.2fms "
           "avg_delay=%.2fms freshness=%.3fms interval_p50=%.3fms interval_p95=%.3fms last_present_ns=%lld "
           "applied_generation=%u swapchain_recreations=%u present_hold=%.4fms acquire_block=%.4fms "
           "last_present_return_ns=%lld passthrough=%u engine=%.16s\n",
           (unsigned long long)t.frames, (unsigned long long)t.hits, (unsigned long long)t.misses, t.cost_p50_ms,
           t.cost_q_ms, t.margin_ms, t.avg_delay_ms, t.freshness_ms, t.present_interval_p50_ms,
           t.present_interval_p95_ms, (long long)t.last_present_ns, t.applied_generation, t.swapchain_recreations,
           t.present_hold_ms, t.acquire_block_ms, (long long)t.last_present_return_ns, t.passthrough, t.engine);
    return t;
}

/* Paced run: first present anchors the grid, the remaining n-1 land one slot apart. */
static void check_paced(double elapsed, int n, double hz)
{
    double expect = (n - 1) / hz;
    CHECK(elapsed > expect * 0.95 && elapsed < expect * 1.10 + 0.03, "paced: %d frames in %.3f s (expected %.3f s at %.0f Hz)",
          n, elapsed, expect, hz);
}

static void check_unpaced(double elapsed, int n)
{
    CHECK(elapsed < 0.1 * n / 60.0, "not paced: %d frames in %.4f s", n, elapsed);
}

static gfg_ctl_policy policy(int enabled, double hz, uint32_t generation)
{
    gfg_ctl_policy p = { .enabled = (uint32_t)enabled, .tick_shaping = 1, .pacing = 1, .mode = GFG_MODE_ACT,
                         .real_target_hz = hz, .generation = generation };
    return p;
}

static int read_file(char *buf, size_t len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0)
        return -1;
    ssize_t r = read(fd, buf, len);
    close(fd);
    return (int)r;
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "env";
    int n = argc > 2 ? atoi(argv[2]) : 120;
    app a;
    gfg_ctl_path(path, sizeof(path));
    printf("mode=%s frames=%d shm=%s\n", mode, n, path);

    if (!strcmp(mode, "env")) {
        const char *hz_s = getenv("GFG_FRAME_OS_REAL_HZ"), *lm = getenv("GFG_FRAME_OS_MODE");
        double hz = hz_s ? atof(hz_s) : 60;
        lm = lm && *lm ? lm : "act";
        printf("layer mode=%s\n", lm);
        app_init(&a);
        double el = run_frames(&a, n);
        gfg_ctl_shm *m = map_file(0, 0, 0);
        CHECK(m != NULL, "layer created %s", path);
        gfg_ctl_telemetry t = telemetry(m);
        CHECK(t.frames == (uint64_t)n, "layer loaded and counted %llu/%d frames", (unsigned long long)t.frames, n);
        CHECK(t.last_present_ns > 0, "last_present_ns set");
        CHECK(t.freshness_ms > 0, "freshness %.3f ms > 0", t.freshness_ms);
        CHECK(t.applied_generation == 0 && t.swapchain_recreations == 0, "env generation 0, no recreations");
        CHECK(t.last_present_return_ns >= t.last_present_ns && t.present_hold_ms >= 0 && t.acquire_block_ms >= 0 &&
              !t.passthrough, "present return / hold / acquire block published");
        CHECK(!strcmp(t.engine, "gfg-test-engine"), "engine name '%s' (truncated to 15 chars)", t.engine);
        if (!strcmp(lm, "act")) {
            double period = 1000.0 / hz;
            CHECK(t.hits + t.misses + 1 == t.frames && t.misses <= (uint64_t)n / 20, "hits %llu misses %llu",
                  (unsigned long long)t.hits, (unsigned long long)t.misses);
            CHECK(t.avg_delay_ms > 1.0, "tick shaping delayed frame starts (avg %.2f ms)", t.avg_delay_ms);
            CHECK(t.freshness_ms < period + 1.0, "freshness %.2f ms within one slot (%.2f ms)", t.freshness_ms, period);
            CHECK(fabs(t.present_interval_p50_ms - period) < 1.0 && t.present_interval_p95_ms < period + 2.0,
                  "present intervals p50 %.3f p95 %.3f ms on the %.2f ms grid", t.present_interval_p50_ms,
                  t.present_interval_p95_ms, period);
            check_paced(el, n, hz);
        } else if (!strcmp(lm, "observe")) {
            CHECK(t.hits == 0 && t.misses == 0 && t.avg_delay_ms == 0 && t.margin_ms == 0, "observe: no scheduler output");
            CHECK(t.present_interval_p50_ms > 0 && t.present_interval_p95_ms >= t.present_interval_p50_ms &&
                  t.present_interval_p95_ms < 5.0, "present intervals p50 %.4f p95 %.4f ms (unpaced)",
                  t.present_interval_p50_ms, t.present_interval_p95_ms);
            CHECK(t.cost_p50_ms > 0 && t.cost_q_ms >= t.cost_p50_ms, "cost p50 %.4f q %.4f ms", t.cost_p50_ms, t.cost_q_ms);
            check_unpaced(el, n);
        } else if (!strcmp(lm, "shadow")) {
            CHECK(t.hits + t.misses + 1 == t.frames, "shadow hits %llu misses %llu", (unsigned long long)t.hits,
                  (unsigned long long)t.misses);
            CHECK(t.avg_delay_ms > 1.0, "shadow reports would-be start delay (avg %.2f ms)", t.avg_delay_ms);
            CHECK(t.present_interval_p95_ms < 5.0, "present intervals p95 %.4f ms (unpaced)", t.present_interval_p95_ms);
            check_unpaced(el, n);
        }
        if (m)
            munmap(m, sizeof(*m));
        app_destroy(&a);
    } else if (!strcmp(mode, "file")) {
        gfg_ctl_shm *m = map_file(1, GFG_CTL_VERSION, sizeof(gfg_ctl_shm));
        if (!m) {
            printf("FAIL: cannot create %s\n", path);
            return 1;
        }
        gfg_ctl_policy p = policy(1, 60, 7);
        governor_write(m, &p, 0);
        app_init(&a);
        double el = run_frames(&a, n);
        gfg_ctl_telemetry t = telemetry(m);
        CHECK(t.frames == (uint64_t)n, "file policy 60 Hz: layer counted %llu/%d frames", (unsigned long long)t.frames, n);
        CHECK(t.applied_generation == 7, "policy generation 7 acknowledged (%u)", t.applied_generation);
        check_paced(el, n, 60);

        p = policy(0, 60, 7);
        governor_write(m, &p, 0);
        sleep_ms(150);   /* > one policy re-read period */
        el = run_frames(&a, n);
        t = telemetry(m);
        CHECK(t.frames == (uint64_t)n, "governor disabled: telemetry frozen at %llu", (unsigned long long)t.frames);
        check_unpaced(el, n);

        app_recreate_swapchain(&a);
        p = policy(1, 30, 8);
        governor_write(m, &p, 0);
        sleep_ms(150);
        el = run_frames(&a, n / 2);
        t = telemetry(m);
        CHECK(t.frames == (uint64_t)(n / 2), "re-enabled at 30 Hz: fresh timeline, %llu frames", (unsigned long long)t.frames);
        CHECK(t.applied_generation == 8, "policy generation 8 acknowledged (%u)", t.applied_generation);
        CHECK(t.swapchain_recreations == 1, "swapchain recreation counted (%u)", t.swapchain_recreations);
        check_paced(el, n / 2, 30);
        CHECK(m->writer_pid == (uint32_t)getpid(), "writer_pid = %u", m->writer_pid);

        governor_write(m, &p, 3000000000ll);   /* the Governor died 3 s ago: heartbeat stale */
        g_gov = NULL;
        sleep_ms(150);
        el = run_frames(&a, n);
        t = telemetry(m);
        CHECK(t.frames == (uint64_t)(n / 2), "stale heartbeat: layer forwards only, telemetry frozen at %llu",
              (unsigned long long)t.frames);
        check_unpaced(el, n);
        app_destroy(&a);
        munmap(m, sizeof(*m));
        unlink(path);
    } else if (!strcmp(mode, "off")) {
        unlink(path);
        app_init(&a);
        check_unpaced(run_frames(&a, n), n);
        CHECK(access(path, F_OK) != 0, "no control file created");
        app_destroy(&a);
    } else if (!strcmp(mode, "badver")) {
        /* version 1 (136 bytes) and version 2 (176 bytes): enabled/hz at the same offsets as today */
        static const struct { uint32_t version; int size; } old[] = { { 1, 136 }, { 2, 176 } };
        app_init(&a);
        for (int v = 0; v < 2; v++) {
            gfg_ctl_shm *m = map_file(1, old[v].version, (size_t)old[v].size);
            if (!m) {
                printf("FAIL: cannot create %s\n", path);
                return 1;
            }
            gfg_ctl_policy p = policy(1, 60, 0);
            governor_write(m, &p, 0);
            g_gov = NULL;
            munmap(m, sizeof(*m));
            char before[256], after[256];
            int nb = read_file(before, sizeof(before));
            sleep_ms(150);   /* the layer re-reads the (recreated) file */
            check_unpaced(run_frames(&a, n), n);
            int na = read_file(after, sizeof(after));
            CHECK(nb == old[v].size && na == old[v].size && !memcmp(before, after, (size_t)na),
                  "version-%u file left untouched (%d bytes)", old[v].version, na);
            unlink(path);
        }
        app_destroy(&a);
    } else if (!strcmp(mode, "dxvk")) {
        g_two_swapchains = 1;
        app_init(&a);
        for (int i = 0; i < n; i++) {
            uint32_t ia, ib;
            acquire(&a, a.swapchain, &ia);
            sleep_ms(6);
            acquire(&a, a.swapchain2, &ib);
            present(&a, a.swapchain, ia);
            sleep_ms(6);
            present(&a, a.swapchain2, ib);
        }
        gfg_ctl_shm *m = map_file(0, 0, 0);
        gfg_ctl_telemetry t = telemetry(m);
        /* the first swapchain owns the telemetry: its last present carries the count */
        CHECK(t.frames >= (uint64_t)(2 * n - 1), "counted %llu/%d presents", (unsigned long long)t.frames, 2 * n);
        /* one start per device would give ~0 ms (the other swapchain's acquire) */
        CHECK(t.cost_p50_ms > 5.0 && t.cost_p50_ms < 12.0, "cost p50 %.3f ms from each image's own acquire",
              t.cost_p50_ms);
        CHECK(t.freshness_ms > 5.0 && t.freshness_ms < 12.0, "freshness %.3f ms", t.freshness_ms);
        if (m)
            munmap(m, sizeof(*m));
        app_destroy(&a);
    } else {
        printf("unknown mode %s\n", mode);
        return 2;
    }
    printf("%s: %s\n", mode, failures ? "FAILED" : "OK");
    return failures ? 1 : 0;
}
