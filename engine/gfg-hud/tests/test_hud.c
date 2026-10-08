/* Integration test: a tiny Vulkan "game" (headless surfaces + swapchains on the mock ICD) that
 * acquires / presents through the real loader with VK_LAYER_GFG_hud as an implicit layer.
 * The mock ICD executes no commands: this checks that every call the layer adds succeeds and
 * that the app never sees an error; tests/run_integration.sh checks the layer's debug log
 * (hud yes/no per swapchain, HUD frames per swapchain, no fallback).
 *
 *   test_hud draw N      writes overlays itself: seq change, corner change, swapchain recreate,
 *                        two swapchains in one present, every supported format + FP16, cleared
 *   test_hud external N  overlay already written by the plugin (GFG_HUD_FILE); just presents
 *   test_hud missing N   no overlay file                         \
 *   test_hud invalid N   bad magic, then truncated pixels          > pass-through (0 HUD frames)
 *   test_hud toobig N    overlay larger than the image            /
 *   test_hud leak N      destroys the device with a live swapchain (layer cleans its part)
 *
 * EXPECT_NO_LAYER=1: the layer is not enabled, so no extent file may appear.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <vulkan/vulkan.h>

#include "../src/overlay.h"

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); } \
    else { printf("PASS "); } printf(__VA_ARGS__); printf("\n"); } while (0)
#define VKCHECK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
    printf("FAIL %s:%d: %s -> %d\n", __FILE__, __LINE__, #call, r_); exit(1); } } while (0)

typedef struct app {
    VkInstance inst;
    VkPhysicalDevice phys;
    VkDevice dev;
    VkQueue queue;
    PFN_vkCreateHeadlessSurfaceEXT create_headless;
    VkSemaphore acquired[2];
} app;

typedef struct chain {
    VkSurfaceKHR surface;
    VkSwapchainKHR swapchain;
    VkSwapchainCreateInfoKHR ci;
} chain;

static const char *hud_file, *extent_file;

static void sleep_ms(int ms)
{
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000l };
    nanosleep(&ts, NULL);
}

static int parse_uint(const char *s)
{
    int v = 0;
    while (s && *s >= '0' && *s <= '9')
        v = v * 10 + (*s++ - '0');
    return v;
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

/* Publish an overlay like the plugin (temp + rename): w x h panel with cut corners. */
static void publish(uint32_t magic, uint32_t w, uint32_t h, uint32_t corner, uint32_t margin, uint32_t seq,
                    int truncate)
{
    char tmp[600];
    size_t n = 32 + (size_t)w * h * 4;
    uint8_t *b = calloc(1, n);
    put32(b, magic);
    put32(b + 4, 1);
    put32(b + 8, w);
    put32(b + 12, h);
    put32(b + 16, corner);
    put32(b + 20, margin);
    put32(b + 24, seq);
    for (uint32_t y = 0; y < h; y++)
        for (uint32_t x = 0; x < w; x++) {
            uint8_t *p = b + 32 + ((size_t)y * w + x) * 4;
            int cut = (y == 0 || y + 1 == h) && (x < 2 || x + 2 >= w);
            p[0] = 0x20, p[1] = (uint8_t)(0x40 + seq), p[2] = 0x60, p[3] = cut ? 0 : 255;
        }
    if (truncate)
        n -= 4;
    snprintf(tmp, sizeof(tmp), "%s.tmp", hud_file);
    FILE *f = fopen(tmp, "wb");
    if (!f || fwrite(b, 1, n, f) != n || fclose(f) != 0 || rename(tmp, hud_file) != 0) {
        printf("FAIL: cannot publish %s\n", hud_file);
        exit(1);
    }
    free(b);
}

static void check_extent(uint32_t w, uint32_t h, int hud)
{
    char buf[64] = {0}, want[64];
    if (getenv("EXPECT_NO_LAYER")) {
        CHECK(access(extent_file, F_OK) != 0, "layer not loaded: no extent file");
        return;
    }
    int fd = open(extent_file, O_RDONLY);
    ssize_t n = fd >= 0 ? read(fd, buf, sizeof(buf) - 1) : -1;
    if (fd >= 0)
        close(fd);
    snprintf(want, sizeof(want), "%u %u %d\n", w, h, hud);
    CHECK(n > 0 && !strcmp(buf, want), "extent file says %ux%u hud %d ('%.*s')", w, h, hud, n > 0 ? (int)n - 1 : 0, buf);
}

static void app_init(app *a, int queue2)
{
    const char *iext[] = { VK_KHR_SURFACE_EXTENSION_NAME, VK_EXT_HEADLESS_SURFACE_EXTENSION_NAME };
    const char *dext[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
    VkApplicationInfo ai = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName = "gfg-hud-test",
                             .apiVersion = VK_API_VERSION_1_3 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &ai,
                                 .enabledExtensionCount = 2, .ppEnabledExtensionNames = iext };
    VKCHECK(vkCreateInstance(&ici, NULL, &a->inst));
    uint32_t n = 1;
    VkResult r = vkEnumeratePhysicalDevices(a->inst, &n, &a->phys);
    if ((r != VK_SUCCESS && r != VK_INCOMPLETE) || n == 0) {
        printf("FAIL: no physical device\n");
        exit(1);
    }
    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = 0,
                                    .queueCount = 1, .pQueuePriorities = &prio };
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1,
                               .pQueueCreateInfos = &qci, .enabledExtensionCount = 1, .ppEnabledExtensionNames = dext };
    VKCHECK(vkCreateDevice(a->phys, &dci, NULL, &a->dev));
    if (queue2) {
        VkDeviceQueueInfo2 qi = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_INFO_2, .queueFamilyIndex = 0 };
        vkGetDeviceQueue2(a->dev, &qi, &a->queue);
    } else {
        vkGetDeviceQueue(a->dev, 0, 0, &a->queue);
    }
    a->create_headless = (PFN_vkCreateHeadlessSurfaceEXT)vkGetInstanceProcAddr(a->inst, "vkCreateHeadlessSurfaceEXT");
    VkSemaphoreCreateInfo sci = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO };
    for (int i = 0; i < 2; i++)
        VKCHECK(vkCreateSemaphore(a->dev, &sci, NULL, &a->acquired[i]));
}

static void chain_create(app *a, chain *c, VkFormat format, uint32_t w, uint32_t h)
{
    VkHeadlessSurfaceCreateInfoEXT hci = { .sType = VK_STRUCTURE_TYPE_HEADLESS_SURFACE_CREATE_INFO_EXT };
    VKCHECK(a->create_headless(a->inst, &hci, NULL, &c->surface));
    VkSwapchainCreateInfoKHR ci = {
        .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR, .surface = c->surface, .minImageCount = 3,
        .imageFormat = format, .imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR, .imageExtent = { w, h },
        .imageArrayLayers = 1, .imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
        .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE, .preTransform = VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR,
        .compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR, .presentMode = VK_PRESENT_MODE_FIFO_KHR,
        .clipped = VK_TRUE,
    };
    c->ci = ci;
    VKCHECK(vkCreateSwapchainKHR(a->dev, &c->ci, NULL, &c->swapchain));
    check_extent(w, h, format != VK_FORMAT_R16G16B16A16_SFLOAT);   /* FP16: passed through */
}

/* What a game does on resize. */
static void chain_recreate(app *a, chain *c, uint32_t w, uint32_t h)
{
    VkSwapchainKHR old = c->swapchain;
    c->ci.oldSwapchain = old;
    c->ci.imageExtent.width = w;
    c->ci.imageExtent.height = h;
    VKCHECK(vkCreateSwapchainKHR(a->dev, &c->ci, NULL, &c->swapchain));
    vkDestroySwapchainKHR(a->dev, old, NULL);
    check_extent(w, h, c->ci.imageFormat != VK_FORMAT_R16G16B16A16_SFLOAT);
}

static void chain_destroy(app *a, chain *c)
{
    vkDestroySwapchainKHR(a->dev, c->swapchain, NULL);
    vkDestroySurfaceKHR(a->inst, c->surface, NULL);
}

/* n frames: acquire (semaphore) -> present waiting on it; chains presented together. */
static void frames(app *a, chain **cs, uint32_t count, int n)
{
    VkSwapchainKHR sc[2];
    uint32_t idx[2];
    VkResult res[2];
    for (int f = 0; f < n; f++) {
        for (uint32_t i = 0; i < count; i++) {
            sc[i] = cs[i]->swapchain;
            VKCHECK(vkAcquireNextImageKHR(a->dev, sc[i], UINT64_MAX, a->acquired[i], VK_NULL_HANDLE, &idx[i]));
            res[i] = VK_SUCCESS;   /* the mock ICD leaves pResults alone */
        }
        VkPresentInfoKHR pi = { .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .waitSemaphoreCount = count,
                                .pWaitSemaphores = a->acquired, .swapchainCount = count, .pSwapchains = sc,
                                .pImageIndices = idx, .pResults = res };
        VKCHECK(vkQueuePresentKHR(a->queue, &pi));
        for (uint32_t i = 0; i < count; i++)
            if (res[i] != VK_SUCCESS) {
                printf("FAIL: present result[%u] = %d\n", i, res[i]);
                exit(1);
            }
    }
}

static void frames1(app *a, chain *c, int n)
{
    frames(a, &c, 1, n);
}

static void app_destroy(app *a)
{
    for (int i = 0; i < 2; i++)
        vkDestroySemaphore(a->dev, a->acquired[i], NULL);
    vkDestroyDevice(a->dev, NULL);
    vkDestroyInstance(a->inst, NULL);
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "draw";
    int n = argc > 2 ? parse_uint(argv[2]) : 30;
    app a;
    chain c, c2;
    hud_file = getenv("GFG_HUD_FILE");
    extent_file = getenv("GFG_HUD_EXTENT_FILE");
    if (!hud_file || !extent_file) {
        printf("FAIL: set GFG_HUD_FILE and GFG_HUD_EXTENT_FILE\n");
        return 2;
    }
    printf("mode=%s frames=%d file=%s\n", mode, n, hud_file);

    if (!strcmp(mode, "draw")) {
        publish(GFG_HUD_MAGIC, 40, 20, GFG_HUD_BOTTOM_RIGHT, 8, 1, 0);
        app_init(&a, 1);
        chain_create(&a, &c, VK_FORMAT_B8G8R8A8_UNORM, 256, 256);
        frames1(&a, &c, n);
        publish(GFG_HUD_MAGIC, 48, 24, GFG_HUD_TOP_LEFT, 4, 2, 0);   /* new seq, size and corner */
        sleep_ms(600);
        frames1(&a, &c, n);
        chain_recreate(&a, &c, 512, 300);
        frames1(&a, &c, n);
        chain_create(&a, &c2, VK_FORMAT_R8G8B8A8_UNORM, 320, 200);
        chain *both[2] = { &c, &c2 };
        frames(&a, both, 2, n);
        chain_destroy(&a, &c2);
        static const VkFormat formats[] = { VK_FORMAT_A2B10G10R10_UNORM_PACK32, VK_FORMAT_A2R10G10B10_UNORM_PACK32,
                                            VK_FORMAT_B8G8R8A8_SRGB, VK_FORMAT_R8G8B8A8_SRGB,
                                            VK_FORMAT_R16G16B16A16_SFLOAT };
        for (unsigned i = 0; i < sizeof(formats) / sizeof(formats[0]); i++) {
            chain_create(&a, &c2, formats[i], 128, 96);
            frames1(&a, &c2, n);
            chain_destroy(&a, &c2);
        }
        publish(GFG_HUD_MAGIC, 0, 0, 0, 0, 3, 0);   /* HUD cleared */
        sleep_ms(600);
        frames1(&a, &c, n);
        chain_destroy(&a, &c);
        app_destroy(&a);
        CHECK(1, "draw: every call succeeded");
    } else if (!strcmp(mode, "external")) {
        app_init(&a, 0);
        chain_create(&a, &c, VK_FORMAT_B8G8R8A8_UNORM, 1280, 800);
        frames1(&a, &c, n);
        chain_destroy(&a, &c);
        app_destroy(&a);
        CHECK(1, "external overlay: every call succeeded");
    } else if (!strcmp(mode, "missing") || !strcmp(mode, "invalid") || !strcmp(mode, "toobig")) {
        unlink(hud_file);
        if (!strcmp(mode, "invalid"))
            publish(0x12345678, 40, 20, 0, 8, 1, 0);
        else if (!strcmp(mode, "toobig"))
            publish(GFG_HUD_MAGIC, 250, 40, GFG_HUD_TOP_LEFT, 8, 1, 0);   /* 250 + 8 > 256 */
        app_init(&a, 0);
        chain_create(&a, &c, VK_FORMAT_B8G8R8A8_UNORM, 256, 256);
        frames1(&a, &c, n);
        if (!strcmp(mode, "invalid")) {
            publish(GFG_HUD_MAGIC, 40, 20, 0, 8, 2, 1);   /* valid header, pixels one texel short */
            sleep_ms(600);
            frames1(&a, &c, n);
        }
        chain_recreate(&a, &c, 200, 100);
        frames1(&a, &c, n);
        chain_destroy(&a, &c);
        app_destroy(&a);
        CHECK(1, "%s: pass-through, every call succeeded", mode);
    } else if (!strcmp(mode, "leak")) {
        publish(GFG_HUD_MAGIC, 40, 20, GFG_HUD_TOP_RIGHT, 8, 1, 0);
        app_init(&a, 0);
        chain_create(&a, &c, VK_FORMAT_B8G8R8A8_UNORM, 256, 256);
        frames1(&a, &c, n);
        app_destroy(&a);   /* swapchain never destroyed */
        CHECK(1, "device destroyed with a live swapchain");
    } else {
        printf("unknown mode %s\n", mode);
        return 2;
    }
    printf("%s: %s\n", mode, failures ? "FAILED" : "OK");
    return failures ? 1 : 0;
}
