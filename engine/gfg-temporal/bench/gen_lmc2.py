"""LMC2: the layered motion candidate in the shape it will have on the GPU.

Same layers as gen_lmc.py (HUD, camera homography, predictive block search,
orphan object search, per-pixel vectors, trajectory test), restructured so
every stage maps to a compute pass with a known cost on the Deck:

  per pair (shared by the generated frames)
    luma pyramid + HUD still counter          full res, one read of each frame
    block search, B grid and A grid           1/2 res, 8x8 full-res blocks;
                                              camera candidate = previous pair's
                                              homography (one pass, no re-run)
    camera fit                                one workgroup, IRLS on 16k vectors
    orphan search                             unexplained blocks only
    per-pixel vectors, both grids             1/2 res, 3x3 patch, block-constant
                                              candidates (LDS tiles on the GPU)
  per generated frame
    trajectory selection                      1/2 res, 1x1 colour error
    compose                                   full res: each pixel picks among
                                              the 4 nearest 1/2-res choices by
                                              its own two-sided error, then one
                                              two-sided (or one-sided) fetch
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

import gen_lmc as L
from methods import register

MAX_LAYERS = 3     # motion planes: camera/far scene, ground, a wall
MIN_LAYER_SHARE = 0.10
PALETTE = 4
RANSAC_ITERS = 128
MARGIN = 0.06      # half-res 3x3 RGB SAD (mean per pixel x 9) other candidates must beat
TOL_PX = 0.75      # trajectory consistency, half-res pixels (+10 % of |v|)


def half(rgb):
    h, w = rgb.shape[0] // 2 * 2, rgb.shape[1] // 2 * 2
    r = rgb[:h, :w]
    return 0.25 * (r[0::2, 0::2] + r[1::2, 0::2] + r[0::2, 1::2] + r[1::2, 1::2])


def grid_coords(h, w):
    py, px = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    return py, px


def block_cands(blocks, bi, bj, extra=None, base=None):
    bh, bw = blocks.shape[:2]
    out = []
    for dy in (0, -1, 1):
        for dx in (0, -1, 1):
            out.append(blocks[np.clip(bi + dy, 0, bh - 1), np.clip(bj + dx, 0, bw - 1)])
    if extra is not None and extra[1].any():
        ev, eok = extra
        for dy in (0, -1, 1):
            for dx in (0, -1, 1):
                yy, xx = np.clip(bi + dy, 0, bh - 1), np.clip(bj + dx, 0, bw - 1)
                out.append(np.where(eok[yy, xx][..., None], ev[yy, xx], out[0]))
    return out


def camera_vec(H, px, py, grid, scale):
    """Camera motion (A -> B) in this grid's pixels at grid points (px, py)."""
    fx, fy = (px + 0.5) * scale - 0.5, (py + 0.5) * scale - 0.5
    if grid == "a":
        qx, qy = L.apply_h(H, fx, fy)
        return np.stack([(qx - fx) / scale, (qy - fy) / scale], -1).astype(np.float32)
    qx, qy = L.apply_h(np.linalg.inv(H), fx, fy)
    return np.stack([(fx - qx) / scale, (fy - qy) / scale], -1).astype(np.float32)


def half_field(ah, bh_, blocks, orph, H, grid, hudh, palette=()):
    """Per-pixel vectors at 1/2 res (half-res pixel units)."""
    h, w = ah.shape[:2]
    py, px = grid_coords(h, w)
    bi = np.clip((py // 4).astype(int), 0, blocks.shape[0] - 1)
    bj = np.clip((px // 4).astype(int), 0, blocks.shape[1] - 1)
    cands = [c * 0.5 for c in block_cands(blocks, bi, bj, orph)]
    for Hk in (H or []):
        cands.append(camera_vec(Hk, px, py, grid, 2.0))
    for pv in palette:
        cands.append(np.broadcast_to(pv * 0.5, (h, w, 2)).astype(np.float32))
    cands.append(np.zeros((h, w, 2), np.float32))
    own, oth = (bh_, ah) if grid == "b" else (ah, bh_)
    sign = -1.0 if grid == "b" else 1.0
    best_c = np.full((h, w), np.inf, np.float32)
    best_v = np.zeros((h, w, 2), np.float32)
    for k, v in enumerate(cands):
        ox, oy = px + sign * v[..., 0], py + sign * v[..., 1]
        d = np.abs(own - L.bilinear(oth, ox, oy)).sum(-1)
        c = uniform_filter(d, 3, mode="nearest") + (0.0 if k == 0 else MARGIN)
        c = np.where(L.inside(ox, oy, w, h), c, np.inf)
        better = c < best_c
        best_c = np.where(better, c, best_c)
        best_v = np.where(better[..., None], v, best_v)
    best_v[hudh] = 0.0
    return best_v, best_c


def motion_palette(vb, w0, k=PALETTE):
    """The k most frequent block vectors (1 px bins, near-duplicates merged).
    Background motion is always among them, so a pixel next to an object
    still has the right candidate when all of its neighbouring blocks took
    the object's motion (the halo around a still object on a moving scene)."""
    q = np.round(vb.reshape(-1, 2)).astype(np.int32)
    q = q[w0.ravel() > 0]
    if q.size == 0:
        return []
    keys, counts = np.unique(q[:, 0] * 4096 + q[:, 1], return_counts=True)
    order = np.argsort(-counts)
    out = []
    for i in order:
        v = np.array([(keys[i] + 2048) // 4096, (keys[i] + 2048) % 4096 - 2048], np.float32)
        if counts[i] < 0.01 * q.shape[0]:
            break
        if all(np.abs(v - o).max() > 1.5 for o in out):
            out.append(v)
        if len(out) == k:
            break
    return out


def ransac_plane(xs, ys, vx, vy, w0, rng, iters=RANSAC_ITERS):
    """Best homography by inlier count from 4-block samples, then a weighted
    refit on its inliers.  Multi-plane scenes need this: an IRLS fit over all
    blocks settles on a compromise that fits no plane."""
    idx = np.nonzero(w0 > 0)[0]
    if idx.size < 12:
        return None, None
    dx, dy = xs + vx, ys + vy
    tol = 1.5 + 0.03 * np.hypot(vx, vy)
    best_n, best_in = 0, None
    for _ in range(iters):
        s = rng.choice(idx, 4, replace=False)
        try:
            H = L.fit_homography(np.stack([xs[s], ys[s]], 1), np.stack([dx[s], dy[s]], 1), np.ones(4))
        except np.linalg.LinAlgError:
            continue
        if not np.all(np.isfinite(H)):
            continue
        px, py = L.apply_h(H, xs[idx], ys[idx])
        inl = np.hypot(px - dx[idx], py - dy[idx]) < tol[idx]
        n = int(inl.sum())
        if n > best_n:
            best_n, best_in = n, idx[inl]
    if best_in is None or best_in.size < 8:
        return None, None
    H = L.fit_homography(np.stack([xs[best_in], ys[best_in]], 1), np.stack([dx[best_in], dy[best_in]], 1),
                         np.ones(best_in.size))
    px, py = L.apply_h(H, xs, ys)
    explained = (np.hypot(px - dx, py - dy) < tol) & (w0 > 0)
    return H, explained


def fit_layers(vb, cb, hud, yb, rng):
    """Sequential planes: the largest first (camera rotation / far scene or the
    ground), then the next largest among the remaining blocks.  A homography
    is exact for a planar surface whatever the camera does."""
    bh, bw = vb.shape[:2]
    cy, cx = np.meshgrid((np.arange(bh) + 0.5) * 8 - 0.5, (np.arange(bw) + 0.5) * 8 - 0.5, indexing="ij")
    g = np.abs(np.diff(yb, axis=1, prepend=yb[:, :1])) + np.abs(np.diff(yb, axis=0, prepend=yb[:1]))
    tex = g[: bh * 8, : bw * 8].reshape(bh, 8, bw, 8).mean(axis=(1, 3))
    hudb = hud[: bh * 8, : bw * 8].reshape(bh, 8, bw, 8).mean(axis=(1, 3)) > 0.2
    w0 = ((tex > 0.01) & ~hudb & (cb < 0.05)).astype(np.float64).ravel()
    xs, ys = (cx - vb[..., 0]).ravel(), (cy - vb[..., 1]).ravel()
    vx, vy = vb[..., 0].ravel(), vb[..., 1].ravel()
    total = max(w0.sum(), 1.0)
    layers, shares = [], []
    for _ in range(MAX_LAYERS):
        H, explained = ransac_plane(xs, ys, vx, vy, w0, rng)
        if H is None:
            break
        share = float(explained.sum() / total)
        if share < MIN_LAYER_SHARE:
            break
        layers.append(H)
        shares.append(round(share, 3))
        w0 = w0 * ~explained
    return layers, shares


@register("lmc2")
class LMC2:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.prev = None
        self.still = np.zeros((h, w), np.int32)
        self.temporal = None
        self.H = None
        self.layers = []
        self.rng = np.random.default_rng(1)
        self.palette = []
        self.debug = {}

    def push(self, frame, ts):
        b = frame.astype(np.float32) / 255.0
        yb = L.luma(b)
        pyr_b = [yb]
        for _ in range(L.LEVELS):
            pyr_b.append(L.down(pyr_b[-1]))
        bh_ = half(b)
        prev, self.prev = self.prev, (b, pyr_b, bh_)
        if prev is None:
            return []
        a, pyr_a, ah = prev
        still_now = np.abs(b - a).max(-1) < L.STILL
        moving = self.H is not None and np.hypot(*(np.array(L.apply_h(self.H, self.w / 2, self.h / 2))
                                                   - np.array([self.w / 2, self.h / 2]))) > 1.0
        self.still = np.where(still_now, self.still + (1 if moving else 0), 0)
        hud = self.still >= L.HUD_PAIRS
        hudh = half(hud.astype(np.float32)) > 0.5
        # one search per grid; the camera candidate is the previous pair's fit
        vb, cb = L.estimate(pyr_a, pyr_b, "b", self.layers or None, self.temporal)
        va, ca = L.estimate(pyr_a, pyr_b, "a", self.layers or None, vb)
        layers, shares = fit_layers(vb, cb, hud, yb, self.rng)
        bhb, bwb = vb.shape[:2]
        hudb = hud[: bhb * 8, : bwb * 8].reshape(bhb, 8, bwb, 8).mean(axis=(1, 3)) > 0.2
        pal = motion_palette(vb, (~hudb).astype(np.float32))
        self.palette = pal
        self.layers = layers
        H = layers if layers else None
        inl = shares
        self.temporal, self.H = vb, (layers[0] if layers else None)
        # orphans need per-pixel residuals: a first per-pixel pass without them
        pvb, pcb = half_field(ah, bh_, vb, None, H, "b", hudh, pal)
        pva, pca = half_field(ah, bh_, va, None, H, "a", hudh, pal)
        rb = np.repeat(np.repeat(pcb > L.RESID * 0.5, 2, 0), 2, 1)[: self.h, : self.w] & ~hud
        ra = np.repeat(np.repeat(pca > L.RESID * 0.5, 2, 0), 2, 1)[: self.h, : self.w] & ~hud
        ob = L.orphan_search(pyr_b[0], rb.astype(np.float32), pyr_a[0], ra.astype(np.float32), -1.0, vb)
        oa = L.orphan_search(pyr_a[0], ra.astype(np.float32), pyr_b[0], rb.astype(np.float32), 1.0, va)
        if ob[1].any():
            pvb, pcb = half_field(ah, bh_, vb, ob, H, "b", hudh, pal)
        if oa[1].any():
            pva, pca = half_field(ah, bh_, va, oa, H, "a", hudh, pal)
        self.debug = {"inliers": inl, "hud": float(hud.mean()), "orphans": (int(ob[1].sum()), int(oa[1].sum()))}
        return [self._synth(a, b, ah, bh_, vb, pva, pvb, (ob, oa), H, hud, t) for t in ts]

    def _select_half(self, ah, bh_, vb, pva, pvb, orphans, H, t):
        """Trajectory test at 1/2 res: vector (half-res px) and mode per cell.
        mode 3 = both sides valid, 1 = previous only (covered), 2 = newest only
        (uncovered), 0 = none (orphan blend)."""
        h, w = ah.shape[:2]
        py, px = grid_coords(h, w)
        bi = np.clip((py // 4).astype(int), 0, vb.shape[0] - 1)
        bj = np.clip((px // 4).astype(int), 0, vb.shape[1] - 1)
        cands = [pvb, pva]
        for o in orphans:
            if o[1].any():
                ev, eok = o
                for dy in (0, -1, 1):
                    for dx in (0, -1, 1):
                        yy, xx = np.clip(bi + dy, 0, vb.shape[0] - 1), np.clip(bj + dx, 0, vb.shape[1] - 1)
                        cands.append(np.where(eok[yy, xx][..., None], ev[yy, xx] * 0.5, pvb))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cands.append(vb[np.clip(bi + dy, 0, vb.shape[0] - 1), np.clip(bj + dx, 0, vb.shape[1] - 1)] * 0.5)
        for Hk in (H or []):
            cands.append(camera_vec(Hk, px, py, "b", 2.0))
        for pv in self.palette:
            cands.append(np.broadcast_to(pv * 0.5, (h, w, 2)).astype(np.float32))
        cands.append(np.zeros((h, w, 2), np.float32))
        best_s = np.full((h, w), -np.inf, np.float32)
        best_v = np.zeros((h, w, 2), np.float32)
        best_m = np.zeros((h, w), np.int8)
        for k, v in enumerate(cands):
            ax, ay = px - t * v[..., 0], py - t * v[..., 1]
            bx, by = px + (1 - t) * v[..., 0], py + (1 - t) * v[..., 1]
            tol = TOL_PX + 0.1 * np.hypot(v[..., 0], v[..., 1])
            ok_a = L.inside(ax, ay, w, h) & (np.hypot(*(L.bilinear(pva, ax, ay) - v).transpose(2, 0, 1)) < tol)
            ok_b = L.inside(bx, by, w, h) & (np.hypot(*(L.bilinear(pvb, bx, by) - v).transpose(2, 0, 1)) < tol)
            err = np.abs(L.bilinear(ah, ax, ay) - L.bilinear(bh_, bx, by)).sum(-1) / 3.0
            both = ok_a & ok_b
            pen = 0.0 if k < 2 else 0.01
            score = np.where(both, 2.0 - err, np.where(ok_a | ok_b, 1.0, -err)) - pen
            better = score > best_s
            mode = np.where(both, 3, np.where(ok_a, 1, np.where(ok_b, 2, 0))).astype(np.int8)
            best_s = np.where(better, score, best_s)
            best_v = np.where(better[..., None], v, best_v)
            best_m = np.where(better, mode, best_m)
        best_m[best_s < 0.5] = 0
        return best_v, best_m

    def _synth(self, a, b, ah, bh_, vb, pva, pvb, orphans, H, hud, t):
        h, w = self.h, self.w
        hv, hm = self._select_half(ah, bh_, vb, pva, pvb, orphans, H, t)
        hh, hw = hv.shape[:2]
        py, px = grid_coords(h, w)
        # 4 nearest half-res cells; each full-res pixel keeps the one whose
        # trajectory matches best at full resolution (crisp object edges)
        cy, cx = (py + 0.5) / 2 - 0.5, (px + 0.5) / 2 - 0.5
        y0, x0 = np.floor(cy).astype(int), np.floor(cx).astype(int)
        best_e = np.full((h, w), np.inf, np.float32)
        out = a * (1 - t) + b * t
        for oy in (0, 1):
            for ox in (0, 1):
                yy, xx = np.clip(y0 + oy, 0, hh - 1), np.clip(x0 + ox, 0, hw - 1)
                v = hv[yy, xx] * 2.0
                m = hm[yy, xx]
                ax, ay = px - t * v[..., 0], py - t * v[..., 1]
                bx, by = px + (1 - t) * v[..., 0], py + (1 - t) * v[..., 1]
                ca, cbb = L.bilinear(a, ax, ay), L.bilinear(b, bx, by)
                e = np.abs(ca - cbb).sum(-1)
                # one-sided cells are judged by mode, not by a two-sided error
                e = np.where(m == 3, e, np.where(m == 0, 9.0, 1.5))
                col = np.where((m == 3)[..., None], ca * (1 - t) + cbb * t,
                               np.where((m == 1)[..., None], ca,
                                        np.where((m == 2)[..., None], cbb, a * (1 - t) + b * t)))
                better = e < best_e
                best_e = np.where(better, e, best_e)
                out = np.where(better[..., None], col, out)
        out[hud] = (b if t >= 0.5 else a)[hud]
        return out
