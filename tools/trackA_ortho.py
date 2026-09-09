"""Track A step 3: topside orthophoto of the canopy plate in the huv frame from the posed 4K stills
(optionally plus the posed 1080p roof-void walk frames of the same COLMAP model, --walk).

Pixel convention (same as track B's bottom-ortho): col 0 = hu0 (west end), row 0 = hv0 (south edge),
hu grows rightward, hv grows downward, pixel centre hu = hu0 + (px+0.5)*mm/1000.

Per pixel: hall xyz = lattice surface (index.html relief) + dense-cloud residual correction (where the
void dense cloud covers the cell) + slab offset; projected into every camera through the void->hall
similarity (--sim). A camera is rejected for a pixel when
  (1) the void dense cloud's depth buffer says something sits in front of the surface (deck, hoist,
      beams where reconstructed), or
  (2) the analytic occluders block the ray: steel ribs 0.22 m wide x 0.28 m tall along the cross,
      diagonal and crest lines, the hub posts, and the catwalk deck (0.8 m wide, 0.45 m up) along the
      mid crest line hv = 7.544 (heights measured from the dense cloud, see report).
Best camera = smallest ground-sampling distance (distance/f/cos(incidence), x a per-source factor)
with a mild penalty for image-corner pixels; the choice is made per 32x32-px cell (not per pixel) so
neighbouring frames of the sweep do not interleave.

Outputs (in --out): tiles/*.npz (per tile: rgb, cam, gsd, obs, corr) + render-args.json;
assemble with trackA_assemble.py.

python trackA_ortho.py --sim <chain.json> --out <dir> [--mm 4] [--tile 1000] [--bays 0,1]
                       [--exclude v025-v031] [--walk] [--walk-factor 2.5]
"""
import sys, os, json, argparse, time
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ply import read_ply

MAPPED = "E:/sitecapture-captures/ngv-video/void4k-register/mapped"
IMG = "E:/sitecapture-captures/ngv-video/void4k-register/images/void4k/"
WALK_IMG = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/images/"
PLY = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/topside-extended-20260821.ply"
# the session scratchpad the track A intermediates were written to. Set TRACKA_SCR to point at
# another copy of them (agent-ref-ceiling/trackA/ holds the json files) instead of editing this.
SCR = os.environ.get("TRACKA_SCR", "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/")
DB_DOWN = 4      # depth buffer at 1/4 resolution
CELL = 32        # camera choice cell (px)
RIB_HALF, RIB_H = 0.11, 0.28
HUB_R, HUB_H = 0.22, 0.60
DECK_HV, DECK_HALF, DECK_H = 7.544, 0.40, 0.45


def parse_exclude(s):
    out = set()
    if not s:
        return out
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            for k in range(int(a[1:]), int(b[1:]) + 1):
                out.add(f"v{k:03d}")
        else:
            out.add(part)
    return out


def load_cameras(sim, walk=False):
    """{name: Cam} in the hall frame; stills 'vNNN', walk frames 'wNNNNNN'."""
    from colmap_bin import read_model
    cams, imgs, _ = read_model(MAPPED, with_points2d=False)
    out = {}
    for im in imgs.values():
        c = cams[im.camera_id]
        cam = G.Cam(c.model, c.width, c.height, c.params, im.R(), im.t).to_frame(sim)
        if im.name.startswith("void4k"):
            out[os.path.basename(im.name)[:-4]] = cam
        elif walk:
            out["w" + im.name[:-4]] = cam
    return out


def image_path(name):
    if name.startswith("v"):
        return IMG + name + ".jpg"
    return WALK_IMG + "w1_" + name[1:] + ".png"


def depth_buffers(cams, sim, cache):
    """z-min depth buffers of the void dense cloud in each camera (hall-frame cameras)."""
    have = {}
    if os.path.exists(cache):
        z = np.load(cache)
        have = {k: z[k] for k in z.files}
    todo = [n for n in cams if n not in have]
    if not todo:
        return have
    mm, _ = read_ply(PLY)
    P = np.stack([np.asarray(mm["x"], np.float32), np.asarray(mm["y"], np.float32), np.asarray(mm["z"], np.float32)], 1)
    P = G.apply_sim(sim, P.astype(np.float64)).astype(np.float32)
    t0 = time.time()
    for k, name in enumerate(todo):
        cam = cams[name]
        h, w = cam.h // DB_DOWN, cam.w // DB_DOWN
        u, v, z = cam.project(P)
        # drop cloud points within 0.9 m of the camera: the walk cloud holds the still photographer
        # standing at this very spot (points 1.3-1.4 m above the deck) and near-field noise
        dcam = np.linalg.norm(P - cam.center.astype(np.float32), axis=1)
        ok = cam.inside(u, v, z) & (z < 60) & (dcam > 0.9)
        ui = (u[ok] / DB_DOWN).astype(np.int32)
        vi = (v[ok] / DB_DOWN).astype(np.int32)
        zi = z[ok].astype(np.float32)
        buf = np.full(h * w, np.inf, np.float32)
        key = vi * w + ui
        o = np.argsort(-zi)
        buf[key[o]] = zi[o]
        buf = buf.reshape(h, w)
        buf = cv2.erode(buf, np.ones((3, 3), np.uint8))
        have[name] = buf
        if k % 50 == 0:
            print(f"  depth buffers {k+1}/{len(todo)}  {round(time.time()-t0)} s", flush=True)
    np.savez_compressed(cache, **have)
    return have


def residual_field(sim, mm_cell=0.05):
    """Dense-cloud residual above the lattice model, on a huv grid (metres), smoothed. NaN = no data."""
    z = np.load(SCR + "void_dense_heightmap.npz")
    H, N, x0, z0, cell = z["H10"], z["N"], float(z["x0"]), float(z["z0"]), float(z["cell"])
    iz, ix = np.nonzero(N >= 3)
    x = x0 + (ix + 0.5) * cell
    zz = z0 + (iz + 0.5) * cell
    y = H[iz, ix]
    P = G.apply_sim(sim, np.stack([x, y, zz], 1))
    hu, hv = G.xz_to_huv(P[:, 0], P[:, 2])
    ymod = G.surface_y(hu, hv, 0.0)
    d = P[:, 1] - ymod
    ok = (np.abs(d) < 0.12) & (hu >= G.PLATE_HU[0]) & (hu < G.PLATE_HU[1]) & (hv >= G.PLATE_HV[0]) & (hv < G.PLATE_HV[1])
    hu, hv, d = hu[ok], hv[ok], d[ok]
    nu = int(np.ceil((G.PLATE_HU[1] - G.PLATE_HU[0]) / mm_cell))
    nv = int(np.ceil((G.PLATE_HV[1] - G.PLATE_HV[0]) / mm_cell))
    iu = ((hu - G.PLATE_HU[0]) / mm_cell).astype(int)
    iv = ((hv - G.PLATE_HV[0]) / mm_cell).astype(int)
    S = np.bincount(iv * nu + iu, weights=d, minlength=nu * nv)
    C = np.bincount(iv * nu + iu, minlength=nu * nv)
    F = np.where(C > 0, S / np.maximum(C, 1), np.nan).reshape(nv, nu).astype(np.float32)
    W = np.isfinite(F).astype(np.float32)
    Fz = np.where(np.isfinite(F), F, 0).astype(np.float32)
    k = 7
    num = cv2.blur(Fz, (k, k))
    den = cv2.blur(W, (k, k))
    Fs = np.where(den > 0.25, num / np.maximum(den, 1e-6), np.nan).astype(np.float32)
    return Fs, mm_cell


def surface_with_corr(hu, hv, slab, Fs, cellF):
    """hall xyz of the surface at (hu,hv) plus its unit normal and the correction used."""
    y0 = G.surface_y(hu, hv, slab)
    iu = np.clip(((hu - G.PLATE_HU[0]) / cellF).astype(int), 0, Fs.shape[1] - 1)
    iv = np.clip(((hv - G.PLATE_HV[0]) / cellF).astype(int), 0, Fs.shape[0] - 1)
    c = Fs[iv, iu]
    c = np.where(np.isfinite(c), c, 0.0)
    y = y0 + c
    x, zc = G.huv_to_xz(hu, hv)
    P = np.stack([x, y, zc], 1)
    e = 0.01
    dyu = (G.surface_y(hu + e, hv, slab) - G.surface_y(hu - e, hv, slab)) / (2 * e)
    dyv = (G.surface_y(hu, hv + e, slab) - G.surface_y(hu, hv - e, slab)) / (2 * e)
    dydx = dyu * G.CU - dyv * G.SU
    dydz = dyu * G.SU + dyv * G.CU
    n = np.stack([-dydx, np.ones_like(dydx), -dydz], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    return P, n, c


def line_dists(hu, hv):
    """distance (m) to the nearest cross line, diagonal, crest line, and vertex."""
    du = ((hu - G.HU0 + G.PU / 2) % G.PU) - G.PU / 2
    dv = ((hv - G.HV0 + G.PV / 2) % G.PV) - G.PV / 2
    cross = np.minimum(np.abs(du), np.abs(dv))
    diag = np.abs(np.abs(du) - np.abs(dv)) / np.sqrt(2)
    crest = np.minimum(np.abs(((hu - G.HU0) % G.PU) - G.PU / 2), np.abs(((hv - G.HV0) % G.PV) - G.PV / 2))
    vert = np.hypot(du, dv)
    return cross, diag, crest, vert


def analytic_occluded(P, cam, hu, hv):
    """True where the ray from P to the camera passes through a rib, hub post or the catwalk deck."""
    d = cam.center - P
    dist = np.linalg.norm(d, axis=1)
    d = d / dist[:, None]
    dy = np.maximum(d[:, 1], 0.02)
    occ = np.zeros(len(P), bool)
    for t in (0.04, 0.10, 0.16, 0.22, 0.27):
        s = t / dy
        Q = P + d * s[:, None]
        qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
        cross, diag, crest, vert = line_dists(qu, qv)
        occ |= (cross < RIB_HALF) | (diag < RIB_HALF) | (crest < RIB_HALF)
        occ |= (vert < HUB_R)
    for t in (0.35, 0.45, 0.55):
        s = t / dy
        Q = P + d * s[:, None]
        qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
        _, _, _, vert = line_dists(qu, qv)
        occ |= (vert < HUB_R) & (t < HUB_H)
    # deck: a slab at DECK_H above the (crest) surface, |hv - DECK_HV| < DECK_HALF
    s = DECK_H / dy
    Q = P + d * s[:, None]
    qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
    occ |= np.abs(qv - DECK_HV) < DECK_HALF
    # the pixel itself under the deck
    occ |= np.abs(hv - DECK_HV) < DECK_HALF
    return occ


def cam_visible(cam, P, n, hu, hv, db, margin=6):
    """per-pixel: index of visible pixels, u, v, gsd(mm/px), score."""
    u, v, z = cam.project(P)
    ok = cam.inside(u, v, z, margin=margin)
    if not ok.any():
        return None
    Xc = P @ cam.R.T + cam.t
    ok &= Xc[:, 2] > 0.35 * np.linalg.norm(Xc, axis=1)
    idx = np.nonzero(ok)[0]
    if len(idx) == 0:
        return None
    ui = np.clip((u[idx] / DB_DOWN).astype(int), 0, db.shape[1] - 1)
    vi = np.clip((v[idx] / DB_DOWN).astype(int), 0, db.shape[0] - 1)
    dz = z[idx]
    occ = db[vi, ui] < dz - (0.08 + 0.015 * dz)
    idx = idx[~occ]
    if len(idx) == 0:
        return None
    occ2 = analytic_occluded(P[idx], cam, hu[idx], hv[idx])
    idx = idx[~occ2]
    if len(idx) == 0:
        return None
    d = P[idx] - cam.center
    dist = np.linalg.norm(d, axis=1)
    cosi = np.abs(np.einsum("ij,ij->i", d / dist[:, None], n[idx]))
    f = cam.params[0]
    gsd = 1000.0 * dist / f / np.maximum(cosi, 0.05)
    r = np.hypot((u[idx] - cam.w / 2) / (cam.w / 2), (v[idx] - cam.h / 2) / (cam.h / 2))
    return idx, u[idx], v[idx], gsd, gsd * (1 + 0.35 * r * r)


def render_tile(px0, py0, tw, th, mm, cams, names, factors, dbufs, get_img, Fs, cellF, slab):
    px = px0 + np.arange(tw)
    py = py0 + np.arange(th)
    PX, PY = np.meshgrid(px, py)
    hu = G.PLATE_HU[0] + (PX.ravel() + 0.5) * mm / 1000.0
    hv = G.PLATE_HV[0] + (PY.ravel() + 0.5) * mm / 1000.0
    P, n, corr = surface_with_corr(hu, hv, slab, Fs, cellF)
    npx = len(hu)
    ncx, ncy = (tw + CELL - 1) // CELL, (th + CELL - 1) // CELL
    cell_id = ((PY.ravel() - py0) // CELL) * ncx + (PX.ravel() - px0) // CELL
    ncell = ncx * ncy
    samp = np.linspace(0, npx - 1, 400).astype(int)
    best_score = np.full(npx, np.inf, np.float32)
    best_cam = np.full(npx, 65535, np.uint16)
    best_gsd = np.zeros(npx, np.float32)
    observed = np.zeros(npx, bool)
    cell_sum = {}
    cell_cnt = {}
    for ci, name in enumerate(names):
        cam = cams[name]
        u, v, z = cam.project(P[samp])
        if not (cam.inside(u, v, z, margin=-400)).any():
            continue
        res = cam_visible(cam, P, n, hu, hv, dbufs[name])
        if res is None:
            continue
        idx, uu, vv, gsd, score = res
        score = score * factors[ci]
        observed[idx] = True
        better = score < best_score[idx]
        bi = idx[better]
        best_score[bi] = score[better]
        best_cam[bi] = ci
        best_gsd[bi] = gsd[better]
        cell_sum[ci] = np.bincount(cell_id[idx], weights=score, minlength=ncell)
        cell_cnt[ci] = np.bincount(cell_id[idx], minlength=ncell)
    # per-cell choice: lowest mean score among cameras covering >= 90% of the cell's observed pixels
    cell_obs = np.bincount(cell_id[observed], minlength=ncell)
    chosen = np.full(ncell, -1, int)
    if cell_sum:
        cis = np.array(sorted(cell_sum))
        S = np.stack([cell_sum[c] for c in cis])
        Nn = np.stack([cell_cnt[c] for c in cis])
        mean = np.where(Nn > 0, S / np.maximum(Nn, 1), np.inf)
        mean = np.where(Nn >= 0.9 * cell_obs[None, :], mean, np.inf)
        k = np.argmin(mean, axis=0)
        okc = np.isfinite(mean[k, np.arange(ncell)])
        chosen[okc] = cis[k[okc]]
    final_cam = best_cam.copy()
    final_uv = np.zeros((npx, 2), np.float32)
    final_gsd = best_gsd.copy()
    assigned = np.zeros(npx, bool)
    for ci in np.unique(chosen[chosen >= 0]):
        pix = np.nonzero(chosen[cell_id] == ci)[0]
        cam = cams[names[ci]]
        res = cam_visible(cam, P[pix], n[pix], hu[pix], hv[pix], dbufs[names[ci]])
        if res is None:
            continue
        idx, uu, vv, gsd, score = res
        g = pix[idx]
        final_cam[g] = ci
        final_uv[g, 0] = uu
        final_uv[g, 1] = vv
        final_gsd[g] = gsd
        assigned[g] = True
    left = observed & ~assigned
    for ci in np.unique(best_cam[left]):
        pix = np.nonzero(left & (best_cam == ci))[0]
        cam = cams[names[ci]]
        u, v, z = cam.project(P[pix])
        final_cam[pix] = ci
        final_uv[pix, 0] = u
        final_uv[pix, 1] = v
    final_cam[~observed] = 65535
    rgb = np.zeros((npx, 3), np.uint8)
    for ci in np.unique(final_cam[observed]):
        sel = observed & (final_cam == ci)
        im = get_img(names[ci])
        nsel = int(sel.sum())
        rows = (nsel + 4095) // 4096
        mapx = np.zeros(rows * 4096, np.float32); mapx[:nsel] = final_uv[sel, 0]
        mapy = np.zeros(rows * 4096, np.float32); mapy[:nsel] = final_uv[sel, 1]
        col = cv2.remap(im, mapx.reshape(rows, 4096), mapy.reshape(rows, 4096), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        rgb[sel] = col.reshape(-1, 3)[:nsel]
    final_gsd[~observed] = 0
    return (rgb.reshape(th, tw, 3), final_cam.reshape(th, tw), final_gsd.reshape(th, tw),
            observed.reshape(th, tw), corr.reshape(th, tw).astype(np.float32))


class ImageCache:
    def __init__(self, cap=80):
        self.cap, self.d, self.order = cap, {}, []

    def __call__(self, name):
        if name not in self.d:
            im = cv2.imread(image_path(name), cv2.IMREAD_COLOR)
            self.d[name] = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            self.order.append(name)
            if len(self.order) > self.cap:
                old = self.order.pop(0)
                del self.d[old]
        return self.d[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mm", type=float, default=4.0)
    ap.add_argument("--tile", type=int, default=1000)
    ap.add_argument("--slab", type=float, default=0.02)
    ap.add_argument("--bays", default=None, help="comma list of bay i indices to render (default all)")
    ap.add_argument("--exclude", default="v025-v031")
    ap.add_argument("--walk", action="store_true", help="also use the 532 posed 1080p walk frames")
    ap.add_argument("--walk-factor", type=float, default=2.5)
    ap.add_argument("--no-corr", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "tiles"), exist_ok=True)
    sim = G.load_sim(a.sim)
    cams_all = load_cameras(sim, walk=a.walk)
    excl = parse_exclude(a.exclude)
    names = [n for n in sorted(cams_all) if n not in excl]
    factors = np.array([a.walk_factor if n.startswith("w") else 1.0 for n in names], np.float32)
    cams = {n: cams_all[n] for n in names}
    print("cameras used", len(names), "(stills", sum(n.startswith("v") for n in names), ", walk",
          sum(n.startswith("w") for n in names), ") excluded", sorted(excl & set(cams_all)))
    t0 = time.time()
    dbufs = depth_buffers(cams, sim, os.path.join(a.out, "depth-buffers.npz"))
    print("depth buffers ready", round(time.time() - t0, 1), "s")
    Fs, cellF = residual_field(sim)
    if a.no_corr:
        Fs = np.full_like(Fs, np.nan)
    print("residual field: covered cells", int(np.isfinite(Fs).sum()), "of", Fs.size,
          "mean corr (m)", float(np.nanmean(Fs)), "p5/p95", float(np.nanpercentile(Fs, 5)), float(np.nanpercentile(Fs, 95)))
    get_img = ImageCache(cap=90 if a.walk else 70)
    W = int(round((G.PLATE_HU[1] - G.PLATE_HU[0]) * 1000 / a.mm))
    H = int(round((G.PLATE_HV[1] - G.PLATE_HV[0]) * 1000 / a.mm))
    print("ortho size", W, "x", H)
    bays = None if a.bays is None else [int(b) for b in a.bays.split(",")]
    tiles = []
    for py0 in range(0, H, a.tile):
        for px0 in range(0, W, a.tile):
            tw, th = min(a.tile, W - px0), min(a.tile, H - py0)
            if bays is not None:
                hu_lo = G.PLATE_HU[0] + px0 * a.mm / 1000
                hu_hi = G.PLATE_HU[0] + (px0 + tw) * a.mm / 1000
                blo = int(np.floor((hu_lo - G.PLATE_HU[0]) / G.PU))
                bhi = int(np.floor((hu_hi - 1e-6 - G.PLATE_HU[0]) / G.PU))
                if not any(b in bays for b in range(blo, bhi + 1)):
                    continue
            tiles.append((px0, py0, tw, th))
    print("tiles", len(tiles))
    json.dump({"names": names, "factors": factors.tolist(), "W": W, "H": H, "mm": a.mm, "tile": a.tile, "slab": a.slab,
               "sim": a.sim, "excluded": sorted(excl), "walk": a.walk,
               "occluders": {"rib_half_m": RIB_HALF, "rib_h_m": RIB_H, "hub_r_m": HUB_R, "hub_h_m": HUB_H,
                             "deck_hv": DECK_HV, "deck_half_m": DECK_HALF, "deck_h_m": DECK_H}},
              open(os.path.join(a.out, "render-args.json"), "w"), indent=1)
    for k, (px0, py0, tw, th) in enumerate(tiles):
        path = os.path.join(a.out, "tiles", f"t_{py0}_{px0}.npz")
        if os.path.exists(path):
            continue
        rgb, cam, gsd, obs, corr = render_tile(px0, py0, tw, th, a.mm, cams, names, factors, dbufs, get_img, Fs, cellF, a.slab)
        np.savez_compressed(path, rgb=rgb, cam=cam, gsd=gsd, obs=obs, corr=corr)
        print(f"tile {k+1}/{len(tiles)} ({px0},{py0}) observed {obs.mean()*100:.1f}%  {round(time.time()-t0)} s", flush=True)
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
