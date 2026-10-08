/* Host unit tests for the Vulkan-free half of gfg-hud: header parse, row runs, pixel conversion
 * per swapchain format, placement / fit, staging + region build, overlay file polling, extent file. */
#define _GNU_SOURCE
#include "../src/overlay.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;
#define CHECK(cond, ...) do { if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); } \
    else { printf("PASS "); } printf(__VA_ARGS__); printf("\n"); } while (0)

#define S 1000000000ll

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static void header(uint8_t *b, uint32_t magic, uint32_t version, uint32_t w, uint32_t h, uint32_t corner,
                   uint32_t margin, uint32_t seq)
{
    put32(b, magic);
    put32(b + 4, version);
    put32(b + 8, w);
    put32(b + 12, h);
    put32(b + 16, corner);
    put32(b + 20, margin);
    put32(b + 24, seq);
    put32(b + 28, 0);
}

static void test_header(void)
{
    uint8_t b[32];
    gfg_hud_header h;
    header(b, GFG_HUD_MAGIC, 1, 120, 77, 1, 12, 9);
    CHECK(gfg_hud_parse_header(b, 32, &h) == 0 && h.width == 120 && h.height == 77 && h.corner == 1 && h.margin == 12 &&
          h.seq == 9, "valid header parsed");
    CHECK(gfg_hud_pixel_bytes(&h) == 120u * 77 * 4, "pixel bytes");
    CHECK(gfg_hud_parse_header(b, 31, &h) != 0, "short header rejected");
    header(b, 0x48474646, 1, 4, 4, 0, 0, 1);
    CHECK(gfg_hud_parse_header(b, 32, &h) != 0, "bad magic rejected");
    header(b, GFG_HUD_MAGIC, 2, 4, 4, 0, 0, 1);
    CHECK(gfg_hud_parse_header(b, 32, &h) != 0, "version 2 rejected");
    header(b, GFG_HUD_MAGIC, 1, 4, 4, 4, 0, 1);
    CHECK(gfg_hud_parse_header(b, 32, &h) != 0, "corner 4 rejected");
    header(b, GFG_HUD_MAGIC, 1, GFG_HUD_MAX_DIM + 1, 4, 0, 0, 1);
    CHECK(gfg_hud_parse_header(b, 32, &h) != 0, "oversized width rejected");
    header(b, GFG_HUD_MAGIC, 1, 4, 4, 0, GFG_HUD_MAX_MARGIN + 1, 1);
    CHECK(gfg_hud_parse_header(b, 32, &h) != 0, "oversized margin rejected");
    header(b, GFG_HUD_MAGIC, 1, 0, 0, 0, 12, 3);
    CHECK(gfg_hud_parse_header(b, 32, &h) == 0 && !h.width && !h.height && gfg_hud_pixel_bytes(&h) == 0,
          "0x0 header valid (cleared)");
    header(b, GFG_HUD_MAGIC, 1, 50, 0, 0, 12, 3);
    CHECK(gfg_hud_parse_header(b, 32, &h) == 0 && !h.width && !h.height, "50x0 header = cleared");
}

static void test_row_run(void)
{
    uint8_t row[8 * 4] = {0};
    uint32_t x0 = 99, len = 99;
    CHECK(!gfg_hud_row_run(row, 8, &x0, &len), "empty row: no run");
    row[3 * 4 + 3] = 255;
    CHECK(gfg_hud_row_run(row, 8, &x0, &len) && x0 == 3 && len == 1, "single pixel run x0=%u len=%u", x0, len);
    row[2 * 4 + 3] = 1;
    row[5 * 4 + 3] = 7;
    row[4 * 4 + 3] = 9;
    CHECK(gfg_hud_row_run(row, 8, &x0, &len) && x0 == 2 && len == 4, "rounded-corner run x0=%u len=%u", x0, len);
    for (int i = 0; i < 8; i++)
        row[i * 4 + 3] = 255;
    CHECK(gfg_hud_row_run(row, 8, &x0, &len) && x0 == 0 && len == 8, "full row run");
}

static void test_convert(void)
{
    CHECK(gfg_hud_kind_for_format(44) == GFG_HUD_KIND_BGRA8 && gfg_hud_kind_for_format(50) == GFG_HUD_KIND_BGRA8 &&
          gfg_hud_kind_for_format(37) == GFG_HUD_KIND_RGBA8 && gfg_hud_kind_for_format(43) == GFG_HUD_KIND_RGBA8 &&
          gfg_hud_kind_for_format(64) == GFG_HUD_KIND_A2B10G10R10 &&
          gfg_hud_kind_for_format(58) == GFG_HUD_KIND_A2R10G10B10, "supported formats mapped");
    CHECK(gfg_hud_kind_for_format(97) == GFG_HUD_KIND_NONE /* R16G16B16A16_SFLOAT */ &&
          gfg_hud_kind_for_format(0) == GFG_HUD_KIND_NONE && gfg_hud_kind_for_format(23) == GFG_HUD_KIND_NONE,
          "FP16 / undefined / RGB8: no HUD");
    CHECK(gfg_hud_convert_pixel(GFG_HUD_KIND_BGRA8, 0x10, 0x20, 0x30) == 0xff302010u, "BGRA8 keeps bytes, A=255");
    CHECK(gfg_hud_convert_pixel(GFG_HUD_KIND_RGBA8, 0x10, 0x20, 0x30) == 0xff102030u, "RGBA8 swaps R/B, A=255");
    /* 8 -> 10 bits: v << 2 | v >> 6 (0x00 -> 0, 0x80 -> 0x202, 0xff -> 0x3ff) */
    uint32_t t = gfg_hud_convert_pixel(GFG_HUD_KIND_A2B10G10R10, 0x00, 0x80, 0xff);
    CHECK((t & 0x3ff) == 0x3ff && ((t >> 10) & 0x3ff) == 0x202 && ((t >> 20) & 0x3ff) == 0 && t >> 30 == 3,
          "A2B10G10R10: R low, B high, A=3 (0x%08x)", t);
    t = gfg_hud_convert_pixel(GFG_HUD_KIND_A2R10G10B10, 0x00, 0x80, 0xff);
    CHECK((t & 0x3ff) == 0 && ((t >> 10) & 0x3ff) == 0x202 && ((t >> 20) & 0x3ff) == 0x3ff && t >> 30 == 3,
          "A2R10G10B10: B low, R high, A=3 (0x%08x)", t);
    CHECK(gfg_hud_convert_pixel(GFG_HUD_KIND_NONE, 1, 2, 3) == 0, "no kind: 0");
}

static void test_place(void)
{
    uint32_t x, y;
    CHECK(!gfg_hud_place(1280, 800, 120, 77, GFG_HUD_TOP_LEFT, 12, &x, &y) && x == 12 && y == 12, "top-left");
    CHECK(!gfg_hud_place(1280, 800, 120, 77, GFG_HUD_TOP_RIGHT, 12, &x, &y) && x == 1148 && y == 12, "top-right");
    CHECK(!gfg_hud_place(1280, 800, 120, 77, GFG_HUD_BOTTOM_LEFT, 12, &x, &y) && x == 12 && y == 711, "bottom-left");
    CHECK(!gfg_hud_place(1280, 800, 120, 77, GFG_HUD_BOTTOM_RIGHT, 12, &x, &y) && x == 1148 && y == 711,
          "bottom-right");
    CHECK(!gfg_hud_place(132, 89, 120, 77, GFG_HUD_BOTTOM_RIGHT, 12, &x, &y) && x == 0 && y == 0, "exact fit");
    CHECK(gfg_hud_place(131, 89, 120, 77, GFG_HUD_TOP_LEFT, 12, &x, &y) != 0, "one pixel too narrow");
    CHECK(gfg_hud_place(132, 88, 120, 77, GFG_HUD_TOP_LEFT, 12, &x, &y) != 0, "one pixel too short");
    CHECK(gfg_hud_place(64, 64, 0, 0, GFG_HUD_TOP_LEFT, 0, &x, &y) != 0, "empty overlay: nothing");
    CHECK(gfg_hud_place(64, 64, 8, 8, GFG_HUD_TOP_LEFT, 0xffffffffu, &x, &y) != 0, "huge margin: no overflow");
}

/* 4x3: row 0 drawn at x 1..2 (rounded corners), row 1 full, row 2 empty. */
static void make_pixels(uint8_t *px)
{
    memset(px, 0, 4 * 3 * 4);
    for (int y = 0; y < 3; y++)
        for (int x = 0; x < 4; x++) {
            uint8_t *p = px + (y * 4 + x) * 4;
            p[0] = (uint8_t)(0x10 + x);   /* B */
            p[1] = (uint8_t)(0x20 + y);   /* G */
            p[2] = 0x30;                  /* R */
            p[3] = (y == 0 && (x == 1 || x == 2)) || y == 1 ? 255 : 0;
        }
}

static void test_build(void)
{
    uint8_t px[48], st[48];
    gfg_hud_region rg[3];
    gfg_hud_header h = { GFG_HUD_MAGIC, 1, 4, 3, GFG_HUD_BOTTOM_RIGHT, 5, 1, 0 };
    make_pixels(px);
    memset(st, 0xee, sizeof(st));
    uint32_t n = gfg_hud_build(&h, px, GFG_HUD_KIND_RGBA8, 100, 50, st, rg);
    CHECK(n == 2, "two row regions (empty row skipped): %u", n);
    CHECK(rg[0].buf_offset == 4 && rg[0].x == 92 && rg[0].y == 42 && rg[0].len == 2, "row 0 run: off %llu at %u,%u len %u",
          (unsigned long long)rg[0].buf_offset, rg[0].x, rg[0].y, rg[0].len);
    CHECK(rg[1].buf_offset == 16 && rg[1].x == 91 && rg[1].y == 43 && rg[1].len == 4, "row 1 run: off %llu at %u,%u len %u",
          (unsigned long long)rg[1].buf_offset, rg[1].x, rg[1].y, rg[1].len);
    CHECK(st[4] == 0x30 && st[5] == 0x20 && st[6] == 0x11 && st[7] == 0xff, "RGBA staging texel (1,0)");
    CHECK(st[0] == 0xee && st[12] == 0xee && st[32] == 0xee, "undrawn texels not converted");
    CHECK(gfg_hud_build(&h, px, GFG_HUD_KIND_RGBA8, 8, 7, st, rg) == 0, "does not fit: nothing");
    CHECK(gfg_hud_build(&h, px, GFG_HUD_KIND_NONE, 100, 50, st, rg) == 0, "unsupported format: nothing");
    h.width = h.height = 0;
    CHECK(gfg_hud_build(&h, px, GFG_HUD_KIND_BGRA8, 100, 50, st, rg) == 0, "cleared: nothing");
}

static char dir[256], file[300];

/* Publish like the plugin: temp file + rename.  pixels_len < full = truncated file. */
static void publish(uint32_t magic, uint32_t w, uint32_t h, uint32_t seq, size_t pixels_len)
{
    char tmp[320];
    uint8_t hdr[32];
    snprintf(tmp, sizeof(tmp), "%s.tmp", file);
    header(hdr, magic, 1, w, h, 0, 2, seq);
    FILE *f = fopen(tmp, "wb");
    fwrite(hdr, 1, 32, f);
    for (size_t i = 0; i < pixels_len; i++)
        fputc((int)((i % 4) == 3 ? 255 : seq), f);
    fclose(f);
    rename(tmp, file);
}

static void test_source(void)
{
    gfg_hud_source s;
    int64_t t = 10 * S;
    gfg_hud_source_init(&s, file);
    uint64_t g = gfg_hud_source_poll(&s, t);
    CHECK(!s.valid && g == 0, "missing file: no overlay");
    publish(GFG_HUD_MAGIC, 4, 3, 1, 48);
    g = gfg_hud_source_poll(&s, t + S / 10);
    CHECK(!s.valid && g == 0, "not re-read within 500 ms");
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(s.valid && g == 1 && s.hdr.width == 4 && s.pixels && s.pixels[0] == 1 && s.pixels[3] == 255,
          "loaded after the poll period (gen %llu)", (unsigned long long)g);
    publish(GFG_HUD_MAGIC, 4, 3, 1, 48);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(s.valid && g == 1, "same seq republished: no reload");
    publish(GFG_HUD_MAGIC, 4, 3, 2, 48);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(s.valid && g == 2 && s.pixels[0] == 2, "seq 2: reloaded");
    publish(GFG_HUD_MAGIC, 0, 0, 3, 0);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(!s.valid && g == 3, "0x0 overlay: cleared");
    publish(GFG_HUD_MAGIC, 4, 3, 4, 48);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(s.valid && g == 4, "back");
    publish(0x12345678, 4, 3, 5, 48);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(!s.valid && g == 5, "bad magic: nothing drawn");
    publish(GFG_HUD_MAGIC, 4, 3, 6, 47);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(!s.valid && g == 5, "truncated pixels: nothing drawn");
    publish(GFG_HUD_MAGIC, 4, 3, 7, 48);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(s.valid && g == 6, "valid again");
    unlink(file);
    g = gfg_hud_source_poll(&s, t += S / 2);
    CHECK(!s.valid && g == 7, "file removed: nothing drawn");
    gfg_hud_source_free(&s);
}

static void test_extent(void)
{
    char path[320], buf[64] = {0}, tmp[340];
    snprintf(path, sizeof(path), "%s/extent", dir);
    CHECK(gfg_hud_write_extent(path, 1280, 800) == 0, "extent written");
    CHECK(gfg_hud_write_extent(path, 1920, 1080) == 0, "extent rewritten");
    int fd = open(path, O_RDONLY);
    ssize_t n = fd >= 0 ? read(fd, buf, sizeof(buf) - 1) : -1;
    if (fd >= 0)
        close(fd);
    CHECK(n == 10 && !strcmp(buf, "1920 1080\n"), "extent file '%s'", buf);
    snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path, (int)getpid());
    CHECK(access(tmp, F_OK) != 0, "no temp file left");
    CHECK(gfg_hud_write_extent("/nonexistent-dir/x", 1, 1) != 0, "unwritable path: error, no crash");
    unlink(path);
}

int main(void)
{
    const char *base = getenv("TMPDIR");
    snprintf(dir, sizeof(dir), "%s/gfg-hud-test-XXXXXX", base && *base ? base : "/tmp");
    if (!mkdtemp(dir)) {
        printf("FAIL: mkdtemp\n");
        return 1;
    }
    snprintf(file, sizeof(file), "%s/hud.raw", dir);
    test_header();
    test_row_run();
    test_convert();
    test_place();
    test_build();
    test_source();
    test_extent();
    rmdir(dir);
    printf("test_overlay: %s\n", failures ? "FAILED" : "OK");
    return failures ? 1 : 0;
}
