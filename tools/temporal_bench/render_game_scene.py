#!/usr/bin/env python3
"""Render a deterministic game-like reference sequence at an exact frame rate.

The Temporal Engine bench needs ground-truth intermediate frames.  A real game
capture at 90 FPS would be ideal; when none is available this renderer produces
a rasterised 3D scene with the properties that make frame interpolation hard:
parallax between near and far geometry, disocclusion, a fast character, a
spinning fan (non-linear motion), thin fence wires, a fast camera turn, a
static HUD with changing text and a hard scene cut.

It is a synthetic scene, not a commercial game capture.  Every frame is a real
GPU rasterisation (Mesa llvmpipe through EGL) at its exact timestamp, so
dropping two of every three frames leaves known-correct targets in between.

Output: <out>/frames.npy (N x H x W x 3 uint8 .npy memmap) and <out>/meta.json.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

SEGMENTS = [  # (name, start s, end s)
    ("strafe", 0.0, 1.5),
    ("objects", 1.5, 3.0),
    ("fastturn", 3.0, 4.5),
    ("static_hud", 4.5, 6.0),
    ("scenecut", 6.0, 7.0),
]

VERT = """
#version 330
uniform mat4 u_mvp;
uniform mat4 u_model;
in vec3 in_pos;
in vec3 in_nrm;
out vec3 v_world;
out vec3 v_nrm;
void main() {
    vec4 w = u_model * vec4(in_pos, 1.0);
    v_world = w.xyz;
    v_nrm = mat3(u_model) * in_nrm;
    gl_Position = u_mvp * vec4(in_pos, 1.0);
}
"""

FRAG = """
#version 330
uniform int u_material;
uniform vec3 u_tint;
uniform vec3 u_cam;
uniform float u_world;
in vec3 v_world;
in vec3 v_nrm;
out vec4 f_color;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x),
               mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
    float a = 0.5, s = 0.0;
    for (int i = 0; i < 5; ++i) { s += a * noise(p); p *= 2.03; a *= 0.5; }
    return s;
}
void main() {
    vec3 n = normalize(v_nrm);
    vec3 albedo;
    if (u_material == 0) {          // ground: tiles + grime
        vec2 g = v_world.xz;
        float tile = step(0.04, fract(g.x * 0.5)) * step(0.04, fract(g.y * 0.5));
        albedo = mix(vec3(0.18), vec3(0.55, 0.52, 0.47), tile) * (0.6 + 0.5 * fbm(g * 3.0));
    } else if (u_material == 1) {   // bricks on world-space walls
        vec2 b = vec2(dot(v_world.xz, vec2(0.7071, 0.7071)) * 2.0 + v_world.y * 0.0, v_world.y * 4.0);
        b.x += floor(b.y) * 0.5;
        float mortar = step(0.08, fract(b.x)) * step(0.1, fract(b.y));
        albedo = mix(vec3(0.75), u_tint * (0.7 + 0.6 * noise(floor(b) * 1.7)), mortar);
        albedo *= 0.75 + 0.35 * fbm(v_world.xy * 6.0 + v_world.z);
    } else if (u_material == 2) {   // painted metal / character
        albedo = u_tint * (0.8 + 0.2 * fbm(v_world.xz * 8.0 + v_world.y * 3.0));
    } else {                        // sky dome
        float h = clamp(n.y * -1.0, 0.0, 1.0);
        vec3 dir = normalize(v_world - u_cam);
        float c = fbm(dir.xz / max(dir.y, 0.05) * 1.5 + u_world * 3.0);
        albedo = mix(vec3(0.45, 0.6, 0.85), vec3(0.95), smoothstep(0.45, 0.8, c));
        f_color = vec4(albedo, 1.0);
        return;
    }
    vec3 l = normalize(vec3(0.4, 0.8, 0.3));
    float diff = max(dot(n, l), 0.0) * 0.8 + 0.25;
    vec3 col = albedo * diff;
    float d = length(v_world - u_cam);
    col = mix(col, vec3(0.62, 0.7, 0.82), clamp((d - 25.0) / 60.0, 0.0, 1.0));
    if (u_world > 0.5) col = col * vec3(1.15, 0.92, 0.75);  // second location grading
    f_color = vec4(col, 1.0);
}
"""


def box(cx, cy, cz, sx, sy, sz):
    """Axis-aligned box as (positions, normals) triangle lists."""
    faces = [
        ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
        ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
        ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
        ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
        ((0, 0, 1), [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)]),
        ((0, 0, -1), [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]),
    ]
    pos, nrm = [], []
    for n, q in faces:
        for i in (0, 1, 2, 0, 2, 3):
            x, y, z = q[i]
            pos.append((cx + x * sx * 0.5, cy + y * sy * 0.5, cz + z * sz * 0.5))
            nrm.append(n)
    return pos, nrm


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(fovy / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


def look(eye, yaw, pitch):
    fwd = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), -math.cos(yaw) * math.cos(pitch)])
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    m = np.identity(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = right, up, -fwd
    m[:3, 3] = -m[:3, :3] @ np.asarray(eye, dtype=np.float32)
    return m


def translate_rot_y(x, y, z, angle):
    c, s = math.cos(angle), math.sin(angle)
    m = np.identity(4, dtype=np.float32)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c
    m[:3, 3] = (x, y, z)
    return m


def rot_z_at(x, y, z, angle):
    c, s = math.cos(angle), math.sin(angle)
    m = np.identity(4, dtype=np.float32)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c
    m[:3, 3] = (x, y, z)
    return m


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def camera(t):
    """Camera pose at time t (seconds). Returns eye, yaw, pitch, world id."""
    if t < 1.5:                       # strafe right past pillars at 4 m/s
        return (-3.0 + 4.0 * t, 1.7, 6.0), 0.0, -0.05, 0
    if t < 3.0:                       # slow walk forward
        u = t - 1.5
        return (3.0, 1.7, 6.0 - 1.2 * u), 0.08 * math.sin(u * 2.0), -0.05, 0
    if t < 4.5:                       # fast 180 degree turn within 0.5 s plus aim jitter
        u = t - 3.0
        yaw = math.pi * smoothstep(0.4, 0.9, u) + 0.02 * math.sin(u * 23.0)
        return (3.0, 1.7, 4.2), yaw, -0.05 + 0.01 * math.sin(u * 17.0), 0
    if t < 6.0:                       # nearly static aim
        return (3.0, 1.7, 4.2), math.pi + 0.004 * math.sin((t - 4.5) * 3.0), -0.05, 0
    u = t - 6.0                       # cut to another location, slow pan
    return (-20.0, 2.2, -25.0), 1.1 + 0.25 * u, -0.08, 1


def build_static_scene():
    pos, nrm, mats = [], [], []

    def add(geom, material, tint):
        p, n = geom
        pos.append(np.asarray(p, np.float32)); nrm.append(np.asarray(n, np.float32))
        mats.append((material, tint, len(p)))

    add(box(0, -0.05, 0, 200, 0.1, 200), 0, (1, 1, 1))
    rng = np.random.default_rng(7)
    for i in range(26):                              # pillars at many depths -> parallax
        x = -10 + (i % 13) * 2.0 + rng.uniform(-0.4, 0.4)
        z = (-2.0 if i < 13 else -9.0) + rng.uniform(-1.5, 1.5)
        add(box(x, 1.6, z, 0.7, 3.2, 0.7), 1, tuple(rng.uniform(0.4, 0.9, 3)))
    for i in range(8):                               # far wall segments
        add(box(-14 + i * 4.0, 2.5, -22, 3.6, 5.0, 1.0), 1, (0.6, 0.35, 0.3))
    for i in range(40):                              # thin fence wires: fine detail
        add(box(-8 + i * 0.4, 1.0, 1.0, 0.03, 2.0, 0.03), 2, (0.15, 0.15, 0.17))
    add(box(0, 1.9, 1.0, 16.0, 0.03, 0.03), 2, (0.15, 0.15, 0.17))
    for i in range(12):                              # behind the camera after the turn
        add(box(-6 + i * 1.6, 1.2, 12 + (i % 3) * 2.5, 1.0, 2.4, 1.0), 1, (0.35, 0.5, 0.75))
    for i in range(10):                              # second location
        add(box(-26 + i * 2.5, 1.5 + (i % 3), -34 + (i % 4) * 2, 1.8, 3 + (i % 3) * 2, 1.8), 1, (0.8, 0.7, 0.4))
    return pos, nrm, mats


def draw_hud(img, t, rng_text):
    from PIL import Image, ImageDraw, ImageFont
    h, w = img.shape[:2]
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font = small = ImageFont.load_default()
    d.rectangle([20, h - 70, 300, h - 20], fill=(10, 10, 14))
    ammo = 30 - int(t * 2.0) % 31                     # text changes twice per second
    d.text((32, h - 62), f"AMMO {ammo:02d}/90   HP 100", font=font, fill=(240, 240, 240))
    d.rectangle([w - 170, 20, w - 20, 170], outline=(230, 230, 230), width=2, fill=(20, 30, 25))
    for i in range(6):
        d.line([w - 170 + i * 25, 20, w - 170 + i * 25, 170], fill=(60, 90, 70))
    d.text((w - 165, 175), "SECTOR 7  OBJECTIVE: REACH THE GATE", font=small, fill=(220, 220, 220))
    cx, cy = w // 2, h // 2
    d.line([cx - 12, cy, cx - 4, cy], fill=(255, 255, 255), width=2)
    d.line([cx + 4, cy, cx + 12, cy], fill=(255, 255, 255), width=2)
    d.line([cx, cy - 12, cx, cy - 4], fill=(255, 255, 255), width=2)
    d.line([cx, cy + 4, cx, cy + 12], fill=(255, 255, 255), width=2)
    return np.asarray(im)


def render(out: Path, fps: float, width: int, height: int, duration: float, samples: int):
    import moderngl
    ctx = moderngl.create_standalone_context(backend="egl")
    prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
    pos, nrm, mats = build_static_scene()
    vbo = ctx.buffer(np.concatenate([np.hstack([p, n]) for p, n in zip(pos, nrm)]).astype("f4").tobytes())
    vao = ctx.vertex_array(prog, [(vbo, "3f 3f", "in_pos", "in_nrm")])
    cp, cn = box(0, 0, 0, 1, 1, 1)
    cube = ctx.buffer(np.hstack([np.asarray(cp, "f4"), np.asarray(cn, "f4")]).tobytes())
    cube_vao = ctx.vertex_array(prog, [(cube, "3f 3f", "in_pos", "in_nrm")])
    sky_p, sky_n = box(0, 0, 0, 400, 400, 400)
    sky = ctx.buffer(np.hstack([np.asarray(sky_p, "f4"), -np.asarray(sky_n, "f4")]).tobytes())
    sky_vao = ctx.vertex_array(prog, [(sky, "3f 3f", "in_pos", "in_nrm")])

    msaa = ctx.framebuffer(color_attachments=[ctx.renderbuffer((width, height), 4, samples=samples)],
                           depth_attachment=ctx.depth_renderbuffer((width, height), samples=samples))
    resolve = ctx.framebuffer(color_attachments=[ctx.renderbuffer((width, height), 4)])
    proj = perspective(math.radians(70), width / height, 0.1, 500.0)
    count = int(round(duration * fps))
    frames = np.lib.format.open_memmap(out / "frames.npy", mode="w+", dtype=np.uint8,
                                       shape=(count, height, width, 3))
    ctx.enable(moderngl.DEPTH_TEST)
    for k in range(count):
        t = k / fps
        eye, yaw, pitch, world = camera(t)
        view = look(eye, yaw, pitch)
        vp = proj @ view
        msaa.use(); msaa.clear(0.6, 0.7, 0.85, 1.0)
        prog["u_cam"].value = tuple(eye)
        prog["u_world"].value = float(world)

        def draw(vao_, model, material, tint, first=0, vertices=-1):
            prog["u_mvp"].write((vp @ model).T.astype("f4").tobytes())
            prog["u_model"].write(model.T.astype("f4").tobytes())
            prog["u_material"].value = material
            prog["u_tint"].value = tint
            vao_.render(first=first, vertices=vertices)

        ident = np.identity(4, dtype=np.float32)
        sky_model = ident.copy(); sky_model[:3, 3] = eye
        ctx.disable(moderngl.DEPTH_TEST)
        draw(sky_vao, sky_model, 3, (1, 1, 1))
        ctx.enable(moderngl.DEPTH_TEST)
        first = 0
        for material, tint, n in mats:
            draw(vao, ident, material, tint, first, n)
            first += n
        # fast character crossing in front of the camera (8 m/s), bobbing limbs
        cx = -6.0 + ((t - 1.5) % 3.0) * 8.0 if t >= 1.5 else -20.0
        for part, (oy, sy, ph) in enumerate(((1.0, 0.9, 0.0), (1.75, 0.45, 0.0), (0.4, 0.8, 1.0), (0.4, 0.8, -1.0))):
            swing = 0.25 * math.sin(t * 18.0 + ph * 2.0) if part >= 2 else 0.0
            m = translate_rot_y(cx + swing, oy, 3.0, 0.0)
            m = m @ np.diag([0.5, sy, 0.35, 1.0]).astype(np.float32)
            draw(cube_vao, m, 2, (0.85, 0.2, 0.15) if part == 1 else (0.2, 0.3, 0.75))
        # fan: four blades spinning 3 rev/s (non-linear per-pixel motion)
        for b in range(4):
            a = t * 2 * math.pi * (3.0 if t < 4.5 else 0.6) + b * math.pi / 2
            m = rot_z_at(1.5, 2.4, 9.0 if t < 3.0 else 10.5, a)
            m = m @ translate_rot_y(0.55, 0, 0, 0) @ np.diag([1.1, 0.18, 0.05, 1.0]).astype(np.float32)
            draw(cube_vao, m, 2, (0.9, 0.85, 0.2))
        ctx.copy_framebuffer(resolve, msaa)
        img = np.frombuffer(resolve.read(components=3), dtype=np.uint8).reshape(height, width, 3)[::-1]
        frames[k] = draw_hud(np.ascontiguousarray(img), t, None)
    frames.flush()
    meta = {
        "source": "render_game_scene.py (synthetic rasterised scene, Mesa llvmpipe)",
        "fps": fps, "width": width, "height": height, "frames": count,
        "timestamps_s": [k / fps for k in range(count)],
        "segments": [{"name": n, "start": int(round(a * fps)), "end": int(round(b * fps))} for n, a, b in SEGMENTS],
        "scene_cuts": [int(round(6.0 * fps))],
        "msaa": samples,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=float, default=90.0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--duration", type=float, default=7.0)
    ap.add_argument("--msaa", type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    meta = render(a.out, a.fps, a.width, a.height, a.duration, a.msaa)
    print(f"rendered {meta['frames']} frames {meta['width']}x{meta['height']} at {meta['fps']} FPS -> {a.out}")


if __name__ == "__main__":
    main()
