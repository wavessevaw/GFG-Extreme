/* GFG HUD — the Vulkan-free half of VK_LAYER_GFG_hud (unit-tested on the host).
 *
 * Overlay file (written by the plugin with write-temp + rename, little endian):
 *   32-byte header { u32 magic "GFGH", version 1, width, height, corner, margin_px, seq, reserved }
 *   then width*height*4 bytes B,G,R,A, rows top to bottom.  A == 0: not drawn; A != 0: opaque.
 *   Per row the drawn pixels form one contiguous run.  width == 0 or height == 0: HUD cleared.
 *
 * Extent file: "<width> <height>\n" of the last swapchain created, replaced atomically.
 */
#ifndef GFG_HUD_OVERLAY_H
#define GFG_HUD_OVERLAY_H

#include <pthread.h>
#include <stddef.h>
#include <stdint.h>

#define GFG_HUD_MAGIC 0x48474647u   /* "GFGH" */
#define GFG_HUD_VERSION 1u
#define GFG_HUD_HEADER_SIZE 32u
#define GFG_HUD_MAX_DIM 2048u       /* a HUD panel, not a framebuffer */
#define GFG_HUD_MAX_MARGIN 4096u
#define GFG_HUD_POLL_NS 500000000ll
#define GFG_HUD_DEFAULT_FILE "/dev/shm/gfg-hud.raw"
#define GFG_HUD_DEFAULT_EXTENT "/dev/shm/gfg-hud.extent"

enum { GFG_HUD_TOP_LEFT, GFG_HUD_TOP_RIGHT, GFG_HUD_BOTTOM_LEFT, GFG_HUD_BOTTOM_RIGHT };

typedef struct gfg_hud_header {
    uint32_t magic, version, width, height, corner, margin, seq, reserved;
} gfg_hud_header;

/* Pixel layouts a swapchain image can take the overlay in (no HUD for anything else). */
typedef enum gfg_hud_kind {
    GFG_HUD_KIND_NONE = 0,
    GFG_HUD_KIND_BGRA8,          /* B8G8R8A8_UNORM / _SRGB: bytes as in the file */
    GFG_HUD_KIND_RGBA8,          /* R8G8B8A8_UNORM / _SRGB: R and B swapped */
    GFG_HUD_KIND_A2B10G10R10,    /* A2B10G10R10_UNORM_PACK32: R in bits 0..9 */
    GFG_HUD_KIND_A2R10G10B10,    /* A2R10G10B10_UNORM_PACK32: B in bits 0..9 */
} gfg_hud_kind;

/* VkFormat numbers (vulkan_core.h; layer.c static-asserts them) -> kind. */
#define GFG_HUD_VK_R8G8B8A8_UNORM 37u
#define GFG_HUD_VK_R8G8B8A8_SRGB 43u
#define GFG_HUD_VK_B8G8R8A8_UNORM 44u
#define GFG_HUD_VK_B8G8R8A8_SRGB 50u
#define GFG_HUD_VK_A2R10G10B10_UNORM_PACK32 58u
#define GFG_HUD_VK_A2B10G10R10_UNORM_PACK32 64u
gfg_hud_kind gfg_hud_kind_for_format(uint32_t vk_format);

/* Decode and validate a header.  0 = valid (width/height may be 0: cleared), -1 = foreign/broken. */
int gfg_hud_parse_header(const uint8_t *buf, size_t len, gfg_hud_header *out);

/* Pixel bytes that follow a valid header. */
static inline size_t gfg_hud_pixel_bytes(const gfg_hud_header *h)
{
    return (size_t)h->width * h->height * 4u;
}

/* The drawn run of one BGRA row: 1 with [*x0, *x0 + *len) = first..last pixel with A != 0, 0 if none. */
int gfg_hud_row_run(const uint8_t *row, uint32_t width, uint32_t *x0, uint32_t *len);

/* One opaque BGRA pixel as the 32-bit texel of kind (in host = little-endian order). */
uint32_t gfg_hud_convert_pixel(gfg_hud_kind kind, uint8_t b, uint8_t g, uint8_t r);

/* Top-left image position of a w x h overlay at corner with margin inside an ext_w x ext_h image.
 * 0 = fits (w + margin <= ext_w and h + margin <= ext_h), -1 = draw nothing. */
int gfg_hud_place(uint32_t ext_w, uint32_t ext_h, uint32_t w, uint32_t h, uint32_t corner, uint32_t margin,
                  uint32_t *x, uint32_t *y);

/* One copy region: a row run of the overlay. */
typedef struct gfg_hud_region {
    uint64_t buf_offset;   /* bytes into the staging buffer */
    uint32_t x, y;         /* image texel */
    uint32_t len;          /* texels */
} gfg_hud_region;

/* Convert the overlay (header + BGRA pixels) for an ext_w x ext_h image of kind into staging
 * (gfg_hud_pixel_bytes(h) bytes, texel (x, y) at (y * width + x) * 4) and the row regions
 * (room for h->height).  Returns the number of regions; 0 = draw nothing (cleared, empty,
 * does not fit or unsupported kind). */
uint32_t gfg_hud_build(const gfg_hud_header *h, const uint8_t *pixels, gfg_hud_kind kind, uint32_t ext_w,
                       uint32_t ext_h, uint8_t *staging, gfg_hud_region *regions);

/* The current overlay, re-read from the file at most every GFG_HUD_POLL_NS. */
typedef struct gfg_hud_source {
    pthread_mutex_t lock;     /* guards everything below (gfg_hud_source_poll takes it) */
    char path[512];
    int64_t next_poll_ns;
    int polled;               /* at least one poll happened */
    uint64_t gen;             /* bumped whenever the overlay changes (also to / from "none") */
    int valid;                /* a non-empty overlay is loaded */
    gfg_hud_header hdr;       /* last header seen valid (also for a cleared overlay) */
    uint8_t *pixels;
    size_t cap;
} gfg_hud_source;

void gfg_hud_source_init(gfg_hud_source *s, const char *path);
void gfg_hud_source_free(gfg_hud_source *s);
/* Re-read the file when due (open fresh -> header -> pixels -> header again, same seq required;
 * missing / invalid = no overlay; a torn read keeps the previous overlay until the next poll).
 * Returns s->gen.  Takes s->lock. */
uint64_t gfg_hud_source_poll(gfg_hud_source *s, int64_t now_ns);

/* Write "<w> <h> <hud>\n" to path atomically (temp file in the same directory + rename); hud is 1
 * when this swapchain carries the overlay, 0 when it is passed through (the plugin then keeps its
 * text HUD).  0 / -1. */
int gfg_hud_write_extent(const char *path, uint32_t w, uint32_t h, int hud);

#endif
