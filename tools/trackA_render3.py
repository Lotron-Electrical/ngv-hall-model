"""Track A step 3 (resume, v3): as trackA_render2.py but the tiles are aligned to the bay grid (one tile per
bay, so a facet never straddles a tile) and the camera choice is made per FACET (the 4 planar triangles of a
bay) by greedy quality mass (sum of 1/score over the pixels a frame sees), so the seams between frames fall
on the rib lines (which are excluded anyway) or at a frame's natural coverage edge, instead of on a 32-px grid.

v2 docstring follows.
Track A step 3 (resume, v2): topside orthophoto of the canopy plate from the posed 4K stills.

Differences from trackA_ortho.py (kept for the record):
  * the ortho frame can extend east of the model's plate rect (--hu1, default plate east + one bay:
    the cloud and the stills show the real hall running one more bay east of the GLB closure),
  * an early ground-sampling-distance cap (--gsd-max, mm per image pixel) before the occluder tests,
  * an optional 2D similarity correction of the lattice-locked huv (--corr json: s, theta_deg, tu,
    tv, about) applied before the surface lookup, so a measured joint-line residual can be folded in,
  * per-tile per-camera grey histograms of the rendered pixels (for the per-camera white-level gain
    applied at assembly), and the camera list / exclusions are written to render-args.json.
Pixel convention: col 0 = hu0 (west), row 0 = hv0 (south), centre hu = hu0 + (px+0.5)*mm/1000.
Surface: model vertex plane + coffRelief relief + dense-cloud residual (where the cloud exists) + slab.

python trackA_render2.py --sim <chain.json> --out <dir> [--mm 4] [--tile 1000] [--gsd-max 16]
       [--exclude v021,v022,v025-v028] [--corr corr.json] [--hu1 2.792875] [--walk]
"""
import sys, os, json, argparse, time
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import (load_cameras, image_path, depth_buffers, residual_field, line_dists, ImageCache,
                          parse_exclude, DB_DOWN, RIB_HALF, RIB_H, HUB_R, HUB_H, DECK_HV, DECK_H)

CELL = 32
DECK_HALF2 = 0.55   # the grating plus the cable trays either side (measured on v058/v040: ~1.1 m overall)
# occluder geometry measured on the dense cloud (trackA_ribheight.py, Hmax above the modelled surface):
# rib tops p50 0.43 m (mode 0.40-0.45), crest kerb p50 0.47 m, hub nodes 0.8-1.1 m; rib footprint
# half-width ~0.15 m, crest kerb ~0.25 m.
RIB_H2, RIB_HALF2 = 0.50, 0.15
CREST_H2, CREST_HALF2 = 0.50, 0.22
HUB_R2, HUB_H2 = 0.25, 1.0


def make_corr(path):
    j = json.load(open(path))
    s, th, tu, tv = j["s"], np.radians(j["theta_deg"]), j["tu"], j["tv"]
    cu, cv = j["about"]

    def corr(hu, hv):
        du, dv = hu - cu, hv - cv
        c, sn = np.cos(th), np.sin(th)
        return cu + s * (c * du - sn * dv) + tu, cv + s * (sn * du + c * dv) + tv
    return corr


def surface_with_corr(hu, hv, slab, Fs, cellF):
    """hall xyz of the surface at (hu,hv) plus unit normal and the residual correction used."""
    y0 = G.surface_y(hu, hv, slab)
    iu = np.clip(((hu - G.PLATE_HU[0]) / cellF).astype(int), 0, Fs.shape[1] - 1)
    iv = np.clip(((hv - G.PLATE_HV[0]) / cellF).astype(int), 0, Fs.shape[0] - 1)
    inF = (hu >= G.PLATE_HU[0]) & (hu < G.PLATE_HU[0] + Fs.shape[1] * cellF) & (hv >= G.PLATE_HV[0]) & (hv < G.PLATE_HV[0] + Fs.shape[0] * cellF)
    c = Fs[iv, iu]
    c = np.where(np.isfinite(c) & inF, c, 0.0)
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


def analytic_occluded(P, cam, hu, hv):
    """True where the ray from P to the camera passes through a rib (RIB_H2 tall, RIB_HALF2 half-width),
    the crest kerb (CREST_H2 / CREST_HALF2), a hub node (HUB_R2 / HUB_H2) or the catwalk deck band
    (DECK_HALF2 at DECK_H). The ray is sampled every 0.05 m of height up to the tallest occluder."""
    d = cam.center - P
    dist = np.linalg.norm(d, axis=1)
    d = d / dist[:, None]
    dy = np.maximum(d[:, 1], 0.02)
    occ = np.zeros(len(P), bool)
    for t in np.arange(0.03, HUB_H2 + 0.01, 0.05):
        s = t / dy
        Q = P + d * s[:, None]
        qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
        cross, diag, crest, vert = line_dists(qu, qv)
        if t < RIB_H2:
            occ |= (cross < RIB_HALF2) | (diag < RIB_HALF2)
        if t < CREST_H2:
            occ |= crest < CREST_HALF2
        occ |= vert < HUB_R2
    s = DECK_H / dy
    Q = P + d * s[:, None]
    qu, qv = G.xz_to_huv(Q[:, 0], Q[:, 2])
    occ |= np.abs(qv - DECK_HV) < DECK_HALF2
    occ |= np.abs(hv - DECK_HV) < DECK_HALF2
    return occ


def cam_visible(cam, P, n, hu, hv, db, gsd_max, margin=6):
    u, v, z = cam.project(P)
    ok = cam.inside(u, v, z, margin=margin)
    if not ok.any():
        return None
    Xc = P @ cam.R.T + cam.t
    ok &= Xc[:, 2] > 0.35 * np.linalg.norm(Xc, axis=1)
    idx = np.nonzero(ok)[0]
    if len(idx) == 0:
        return None
    d = P[idx] - cam.center
    dist = np.linalg.norm(d, axis=1)
    cosi = np.abs(np.einsum("ij,ij->i", d / dist[:, None], n[idx]))
    f = cam.params[0]
    gsd = 1000.0 * dist / f / np.maximum(cosi, 0.05)
    keep = gsd < gsd_max
    idx, gsd = idx[keep], gsd[keep]
    if len(idx) == 0:
        return None
    ui = np.clip((u[idx] / DB_DOWN).astype(int), 0, db.shape[1] - 1)
    vi = np.clip((v[idx] / DB_DOWN).astype(int), 0, db.shape[0] - 1)
    dz = z[idx]
    occ = db[vi, ui] < dz - (0.08 + 0.015 * dz)
    idx, gsd = idx[~occ], gsd[~occ]
    if len(idx) == 0:
        return None
    occ2 = analytic_occluded(P[idx], cam, hu[idx], hv[idx])
    idx, gsd = idx[~occ2], gsd[~occ2]
    if len(idx) == 0:
        return None
    r = np.hypot((u[idx] - cam.w / 2) / (cam.w / 2), (v[idx] - cam.h / 2) / (cam.h / 2))
    return idx, u[idx], v[idx], gsd, gsd * (1 + 0.35 * r * r)


def render_tile(px0, py0, tw, th, mm, hu0, hv0, cams, names, factors, dbufs, get_img, Fs, cellF, slab, gsd_max, corr):
    px = px0 + np.arange(tw)
    py = py0 + np.arange(th)
    PX, PY = np.meshgrid(px, py)
    hu = hu0 + (PX.ravel() + 0.5) * mm / 1000.0
    hv = hv0 + (PY.ravel() + 0.5) * mm / 1000.0
    if corr is not None:
        hu, hv = corr(hu, hv)
    P, n, cval = surface_with_corr(hu, hv, slab, Fs, cellF)
    npx = len(hu)
    # facet id: which of the 4 planar triangles of its bay the pixel lies in (0 east, 1 west, 2 north, 3 south)
    hu_l = hu0 + (PX.ravel() + 0.5) * mm / 1000.0
    hv_l = hv0 + (PY.ravel() + 0.5) * mm / 1000.0
    du = hu_l - (G.HU0 + np.round((hu_l - G.HU0) / G.PU) * G.PU)
    dv = hv_l - (G.HV0 + np.round((hv_l - G.HV0) / G.PV) * G.PV)
    ew = np.abs(du) / (G.PU / 2) >= np.abs(dv) / (G.PV / 2)
    cell_id = np.where(ew, np.where(du >= 0, 0, 1), np.where(dv >= 0, 2, 3))
    ncell = 4
    samp = np.linspace(0, npx - 1, 600).astype(int)
    best_score = np.full(npx, np.inf, np.float32)
    best_cam = np.full(npx, 65535, np.uint16)
    best_gsd = np.zeros(npx, np.float32)
    observed = np.zeros(npx, bool)
    cell_sum, cell_cnt, cell_mass = {}, {}, {}
    for ci, name in enumerate(names):
        cam = cams[name]
        u, v, z = cam.project(P[samp])
        if not cam.inside(u, v, z, margin=-400).any():
            continue
        res = cam_visible(cam, P, n, hu, hv, dbufs[name], gsd_max)
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
        cell_mass[ci] = np.bincount(cell_id[idx], weights=1.0 / score, minlength=ncell)
    cell_obs = np.bincount(cell_id[observed], minlength=ncell)
    final_cam = best_cam.copy()
    final_uv = np.zeros((npx, 2), np.float32)
    final_gsd = best_gsd.copy()
    assigned = np.zeros(npx, bool)
    # per facet: frames ranked by quality mass (sum of 1/score over the facet pixels they see); greedy fill
    for f in range(ncell):
        if cell_obs[f] == 0 or not cell_sum:
            continue
        ranked = sorted(((cell_mass[ci][f], ci) for ci in cell_sum if cell_cnt[ci][f] > 0), reverse=True)
        fpix = np.nonzero((cell_id == f) & observed)[0]
        left = np.ones(len(fpix), bool)
        for mass, ci in ranked[:12]:
            if left.sum() < 0.02 * len(fpix):
                break
            pix = fpix[left]
            cam = cams[names[ci]]
            res = cam_visible(cam, P[pix], n[pix], hu[pix], hv[pix], dbufs[names[ci]], gsd_max)
            if res is None:
                continue
            idx, uu, vv, gsd, score = res
            if len(idx) < 0.05 * len(fpix):
                continue
            g = pix[idx]
            final_cam[g] = ci
            final_uv[g, 0] = uu
            final_uv[g, 1] = vv
            final_gsd[g] = gsd
            assigned[g] = True
            left[np.nonzero(left)[0][idx]] = False
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
    hist = {}
    for ci in np.unique(final_cam[observed]):
        sel = observed & (final_cam == ci)
        im = get_img(names[ci])
        nsel = int(sel.sum())
        rows = (nsel + 4095) // 4096
        mapx = np.zeros(rows * 4096, np.float32); mapx[:nsel] = final_uv[sel, 0]
        mapy = np.zeros(rows * 4096, np.float32); mapy[:nsel] = final_uv[sel, 1]
        col = cv2.remap(im, mapx.reshape(rows, 4096), mapy.reshape(rows, 4096), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        col = col.reshape(-1, 3)[:nsel]
        rgb[sel] = col
        grey = (0.299 * col[:, 0] + 0.587 * col[:, 1] + 0.114 * col[:, 2]).astype(int)
        hist[int(ci)] = np.bincount(np.clip(grey, 0, 255), minlength=256)
    final_gsd[~observed] = 0
    return (rgb.reshape(th, tw, 3), final_cam.reshape(th, tw), final_gsd.reshape(th, tw),
            observed.reshape(th, tw), cval.reshape(th, tw).astype(np.float32), hist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mm", type=float, default=4.0)
    ap.add_argument("--tile", type=int, default=1000)
    ap.add_argument("--slab", type=float, default=0.02)
    ap.add_argument("--gsd-max", type=float, default=16.0)
    ap.add_argument("--hu1", type=float, default=G.PLATE_HU[1] + G.PU)
    ap.add_argument("--exclude", default="v021,v022,v025-v028")
    ap.add_argument("--walk", action="store_true")
    ap.add_argument("--walk-factor", type=float, default=2.5)
    ap.add_argument("--corr", default=None)
    ap.add_argument("--no-corr", action="store_true", help="drop the dense-cloud residual field")
    ap.add_argument("--only-tiles", default=None, help="comma list of py0_px0 tiles to render")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "tiles"), exist_ok=True)
    sim = G.load_sim(a.sim)
    cams_all = load_cameras(sim, walk=a.walk)
    excl = parse_exclude(a.exclude)
    names = [n for n in sorted(cams_all) if n not in excl]
    factors = np.array([a.walk_factor if n.startswith("w") else 1.0 for n in names], np.float32)
    cams = {n: cams_all[n] for n in names}
    print("cameras used", len(names), "(stills", sum(n.startswith("v") for n in names), ", walk",
          sum(n.startswith("w") for n in names), ") excluded", sorted(excl & set(cams_all)), flush=True)
    t0 = time.time()
    dbufs = depth_buffers(cams, sim, os.path.join(a.out, "depth-buffers.npz"))
    print("depth buffers ready", round(time.time() - t0, 1), "s", flush=True)
    Fs, cellF = residual_field(sim)
    if a.no_corr:
        Fs = np.full_like(Fs, np.nan)
    print("residual field: covered cells", int(np.isfinite(Fs).sum()), "of", Fs.size,
          "mean corr (m)", float(np.nanmean(Fs)), "p5/p95", float(np.nanpercentile(Fs, 5)), float(np.nanpercentile(Fs, 95)), flush=True)
    corr = make_corr(a.corr) if a.corr else None
    get_img = ImageCache(cap=70)
    hu0, hv0 = G.PLATE_HU[0], G.PLATE_HV[0]
    W = int(round((a.hu1 - hu0) * 1000 / a.mm))
    H = int(round((G.PLATE_HV[1] - hv0) * 1000 / a.mm))
    print("ortho size", W, "x", H, "hu", hu0, "..", a.hu1, flush=True)
    tiles = []
    # tiles aligned to the bay grid: bay i spans hu0 + i*PU .. hu0 + (i+1)*PU, bay j spans hv0 + j*PV ..
    xs = [int(round(i * G.PU * 1000 / a.mm)) for i in range(int(round((a.hu1 - hu0) / G.PU)) + 1)]
    xs[-1] = W
    ys = [0, int(round(G.PV * 1000 / a.mm)), H]
    for jy in range(len(ys) - 1):
        for ix in range(len(xs) - 1):
            tiles.append((xs[ix], ys[jy], xs[ix + 1] - xs[ix], ys[jy + 1] - ys[jy]))
    if a.only_tiles:
        want = set(a.only_tiles.split(","))
        tiles = [t for t in tiles if f"{t[1]}_{t[0]}" in want]
    json.dump({"names": names, "factors": factors.tolist(), "W": W, "H": H, "mm": a.mm, "tile": a.tile, "slab": a.slab,
               "hu0": hu0, "hv0": hv0, "hu1": a.hu1, "hv1": G.PLATE_HV[1], "gsd_max": a.gsd_max,
               "sim": a.sim, "corr": a.corr, "excluded": sorted(excl), "walk": a.walk,
               "occluders": {"rib_half_m": RIB_HALF2, "rib_h_m": RIB_H2, "crest_half_m": CREST_HALF2, "crest_h_m": CREST_H2,
                             "hub_r_m": HUB_R2, "hub_h_m": HUB_H2, "deck_hv": DECK_HV, "deck_half_m": DECK_HALF2, "deck_h_m": DECK_H}},
              open(os.path.join(a.out, "render-args.json"), "w"), indent=1)
    print("tiles", len(tiles), flush=True)
    for k, (px0, py0, tw, th) in enumerate(tiles):
        path = os.path.join(a.out, "tiles", f"t_{py0}_{px0}.npz")
        if os.path.exists(path):
            continue
        rgb, cam, gsd, obs, cval, hist = render_tile(px0, py0, tw, th, a.mm, hu0, hv0, cams, names, factors, dbufs, get_img, Fs, cellF, a.slab, a.gsd_max, corr)
        hk = np.array(sorted(hist), np.int32)
        hv_ = np.stack([hist[int(c)] for c in hk]) if len(hk) else np.zeros((0, 256), np.int64)
        np.savez_compressed(path, rgb=rgb, cam=cam, gsd=gsd, obs=obs, corr=cval, hist_cams=hk, hist=hv_)
        print(f"tile {k+1}/{len(tiles)} ({px0},{py0}) observed {obs.mean()*100:.1f}%  {round(time.time()-t0)} s", flush=True)
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
