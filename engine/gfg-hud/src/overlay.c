/* GFG HUD — overlay file, pixel conversion and placement (see overlay.h). */
#define _GNU_SOURCE
#include "overlay.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define TORN_RETRIES 3
#define TORN_REPOLL_NS 50000000ll

gfg_hud_kind gfg_hud_kind_for_format(uint32_t f)
{
    switch (f) {
    case GFG_HUD_VK_B8G8R8A8_UNORM:
    case GFG_HUD_VK_B8G8R8A8_SRGB:
        return GFG_HUD_KIND_BGRA8;
    case GFG_HUD_VK_R8G8B8A8_UNORM:
    case GFG_HUD_VK_R8G8B8A8_SRGB:
        return GFG_HUD_KIND_RGBA8;
    case GFG_HUD_VK_A2B10G10R10_UNORM_PACK32:
        return GFG_HUD_KIND_A2B10G10R10;
    case GFG_HUD_VK_A2R10G10B10_UNORM_PACK32:
        return GFG_HUD_KIND_A2R10G10B10;
    default:
        return GFG_HUD_KIND_NONE;
    }
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

int gfg_hud_parse_header(const uint8_t *buf, size_t len, gfg_hud_header *out)
{
    gfg_hud_header h;
    if (!buf || len < GFG_HUD_HEADER_SIZE)
        return -1;
    h.magic = le32(buf);
    h.version = le32(buf + 4);
    h.width = le32(buf + 8);
    h.height = le32(buf + 12);
    h.corner = le32(buf + 16);
    h.margin = le32(buf + 20);
    h.seq = le32(buf + 24);
    h.reserved = le32(buf + 28);
    if (h.magic != GFG_HUD_MAGIC || h.version != GFG_HUD_VERSION || h.corner > GFG_HUD_BOTTOM_RIGHT ||
        h.margin > GFG_HUD_MAX_MARGIN)
        return -1;
    if (h.width && h.height && (h.width > GFG_HUD_MAX_DIM || h.height > GFG_HUD_MAX_DIM))
        return -1;
    if (!h.width || !h.height)
        h.width = h.height = 0;   /* cleared */
    if (out)
        *out = h;
    return 0;
}

int gfg_hud_row_run(const uint8_t *row, uint32_t width, uint32_t *x0, uint32_t *len)
{
    uint32_t first = 0, last;
    while (first < width && !row[first * 4 + 3])
        first++;
    if (first == width)
        return 0;
    last = width - 1;
    while (!row[last * 4 + 3])
        last--;
    *x0 = first;
    *len = last - first + 1;
    return 1;
}

static uint32_t expand10(uint8_t v)
{
    return (uint32_t)v << 2 | (uint32_t)v >> 6;
}

uint32_t gfg_hud_convert_pixel(gfg_hud_kind kind, uint8_t b, uint8_t g, uint8_t r)
{
    switch (kind) {
    case GFG_HUD_KIND_BGRA8:   /* memory B,G,R,A */
        return (uint32_t)b | (uint32_t)g << 8 | (uint32_t)r << 16 | 0xffu << 24;
    case GFG_HUD_KIND_RGBA8:   /* memory R,G,B,A */
        return (uint32_t)r | (uint32_t)g << 8 | (uint32_t)b << 16 | 0xffu << 24;
    case GFG_HUD_KIND_A2B10G10R10:
        return expand10(r) | expand10(g) << 10 | expand10(b) << 20 | 3u << 30;
    case GFG_HUD_KIND_A2R10G10B10:
        return expand10(b) | expand10(g) << 10 | expand10(r) << 20 | 3u << 30;
    default:
        return 0;
    }
}

int gfg_hud_place(uint32_t ext_w, uint32_t ext_h, uint32_t w, uint32_t h, uint32_t corner, uint32_t margin,
                  uint32_t *x, uint32_t *y)
{
    if (!w || !h || corner > GFG_HUD_BOTTOM_RIGHT || (uint64_t)w + margin > ext_w || (uint64_t)h + margin > ext_h)
        return -1;
    *x = (corner == GFG_HUD_TOP_RIGHT || corner == GFG_HUD_BOTTOM_RIGHT) ? ext_w - margin - w : margin;
    *y = (corner == GFG_HUD_BOTTOM_LEFT || corner == GFG_HUD_BOTTOM_RIGHT) ? ext_h - margin - h : margin;
    return 0;
}

uint32_t gfg_hud_build(const gfg_hud_header *h, const uint8_t *pixels, gfg_hud_kind kind, uint32_t ext_w,
                       uint32_t ext_h, uint8_t *staging, gfg_hud_region *regions)
{
    uint32_t ox, oy, n = 0;
    if (kind == GFG_HUD_KIND_NONE || !pixels ||
        gfg_hud_place(ext_w, ext_h, h->width, h->height, h->corner, h->margin, &ox, &oy) != 0)
        return 0;
    for (uint32_t y = 0; y < h->height; y++) {
        const uint8_t *row = pixels + (size_t)y * h->width * 4;
        uint32_t x0, len;
        if (!gfg_hud_row_run(row, h->width, &x0, &len))
            continue;
        size_t off = ((size_t)y * h->width + x0) * 4;
        for (uint32_t i = 0; i < len; i++) {
            const uint8_t *p = row + (size_t)(x0 + i) * 4;
            uint32_t t = gfg_hud_convert_pixel(kind, p[0], p[1], p[2]);
            uint8_t *o = staging + off + (size_t)i * 4;
            o[0] = (uint8_t)t;
            o[1] = (uint8_t)(t >> 8);
            o[2] = (uint8_t)(t >> 16);
            o[3] = (uint8_t)(t >> 24);
        }
        regions[n].buf_offset = off;
        regions[n].x = ox + x0;
        regions[n].y = oy + y;
        regions[n].len = len;
        n++;
    }
    return n;
}

/* ---- overlay file ---- */

void gfg_hud_source_init(gfg_hud_source *s, const char *path)
{
    memset(s, 0, sizeof(*s));
    pthread_mutex_init(&s->lock, NULL);
    snprintf(s->path, sizeof(s->path), "%s", path && *path ? path : GFG_HUD_DEFAULT_FILE);
}

void gfg_hud_source_free(gfg_hud_source *s)
{
    free(s->pixels);
    s->pixels = NULL;
    s->cap = 0;
    s->valid = 0;
    pthread_mutex_destroy(&s->lock);
}

/* Read exactly len bytes at off; 0 / -1. */
static int read_at(int fd, void *buf, size_t len, off_t off)
{
    uint8_t *p = buf;
    while (len) {
        ssize_t r = pread(fd, p, len, off);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0)
            return -1;
        p += r;
        len -= (size_t)r;
        off += r;
    }
    return 0;
}

static void set_none(gfg_hud_source *s)
{
    if (s->valid)
        s->gen++;
    s->valid = 0;
}

/* One attempt: 1 = done (state updated), 0 = torn (state untouched). */
static int load(gfg_hud_source *s, int fd)
{
    uint8_t raw[GFG_HUD_HEADER_SIZE], again[GFG_HUD_HEADER_SIZE];
    gfg_hud_header h;
    if (read_at(fd, raw, sizeof(raw), 0) != 0 || gfg_hud_parse_header(raw, sizeof(raw), &h) != 0) {
        set_none(s);
        return 1;
    }
    if (!h.width) {                     /* cleared */
        set_none(s);
        s->hdr = h;
        return 1;
    }
    if (s->valid && h.seq == s->hdr.seq && h.width == s->hdr.width && h.height == s->hdr.height &&
        h.corner == s->hdr.corner && h.margin == s->hdr.margin)
        return 1;                       /* unchanged */
    size_t n = gfg_hud_pixel_bytes(&h);
    uint8_t *px = malloc(n);
    if (!px) {
        set_none(s);
        return 1;
    }
    if (read_at(fd, px, n, GFG_HUD_HEADER_SIZE) != 0) {
        /* short: truncated (invalid) unless the header changed meanwhile (torn) */
        int torn = read_at(fd, again, sizeof(again), 0) != 0 || memcmp(raw, again, sizeof(raw)) != 0;
        free(px);
        if (torn)
            return 0;
        set_none(s);
        return 1;
    }
    if (read_at(fd, again, sizeof(again), 0) != 0 || memcmp(raw, again, sizeof(raw)) != 0) {
        free(px);
        return 0;
    }
    free(s->pixels);
    s->pixels = px;
    s->cap = n;
    s->hdr = h;
    s->valid = 1;
    s->gen++;
    return 1;
}

uint64_t gfg_hud_source_poll(gfg_hud_source *s, int64_t now_ns)
{
    uint64_t gen;
    pthread_mutex_lock(&s->lock);
    if (!s->polled || now_ns >= s->next_poll_ns) {
        int done = 0;
        s->polled = 1;
        s->next_poll_ns = now_ns + GFG_HUD_POLL_NS;
        /* Opened fresh every poll: the plugin replaces the file (new inode) on each update. */
        for (int i = 0; i < TORN_RETRIES && !done; i++) {
            int fd = open(s->path, O_RDONLY | O_CLOEXEC);
            if (fd < 0) {
                set_none(s);
                done = 1;
                break;
            }
            done = load(s, fd);
            close(fd);
        }
        if (!done)
            s->next_poll_ns = now_ns + TORN_REPOLL_NS;   /* keep the previous overlay, look again soon */
    }
    gen = s->gen;
    pthread_mutex_unlock(&s->lock);
    return gen;
}

int gfg_hud_write_extent(const char *path, uint32_t w, uint32_t h, int hud)
{
    static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
    char tmp[600], text[32];
    int len, fd, ok;
    if (!path || !*path)
        return -1;
    len = snprintf(text, sizeof(text), "%u %u %d\n", w, h, hud ? 1 : 0);
    if (snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path, (int)getpid()) >= (int)sizeof(tmp))
        return -1;
    pthread_mutex_lock(&lock);
    fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    ok = fd >= 0;
    if (ok) {
        ok = write(fd, text, (size_t)len) == len;
        ok = close(fd) == 0 && ok;
        ok = ok && rename(tmp, path) == 0;
        if (!ok)
            unlink(tmp);
    }
    pthread_mutex_unlock(&lock);
    return ok ? 0 : -1;
}
