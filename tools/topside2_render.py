"""Topside orthophoto of the canopy plate from EVERY posed roof-void camera: the 60 registered 4K
stills plus all four walk traverses (w1 532, w2 103, w4 79, w5 88 frames).

Why a new driver rather than trackA_render3.py --walk: that one reads a single COLMAP model
(void4k-register/mapped), which holds the stills and w1 only. w2/w4/w5 live in
rebuild-roofvoid/build/model. The two models turn out to be the SAME reconstruction (the 532 shared
w1 camera centres agree bit for bit, so the void->hall similarity of record applies unchanged to
both; topside2_framecheck.py proves it), so the cameras can simply be pooled: stills from mapped,
every walk frame from the rebuild model.

Second difference: a per-pixel MIN gsd over all visible cameras is carried through the tiles. The
delivered render uses one gsd cap, but coverage at a TIGHTER cap is then exact and free
(min_gsd < cap), so the gsd_max sweep needs one render, not three.

Everything else - surface (lattice relief + dense-cloud residual + slab), the joint-line correction,
the depth-buffer and analytic occluders (ribs, crest kerb, hub posts, catwalk deck), the per-facet
greedy frame choice and the per-frame grey histograms - is trackA_render3.py's, imported.

Output shape is trackA_render3.py's, so trackA_assemble2.py / trackA_jointcheck2.py read it as is.

python topside2_render.py --sim <chain.json> --corr <corr.json> --out <dir> [--gsd-max 20]
       [--traverses w1,w2,w4,w5] [--depth-only] [--only-tiles 0_0,0_1857]
"""
import sys, os, json, argparse, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import depth_buffers, residual_field, parse_exclude, DB_DOWN
from trackA_render3 import make_corr, surface_with_corr, cam_visible

MAPPED = "E:/sitecapture-captures/ngv-video/void4k-register/mapped"
REBUILD = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/build/model"
STILL_IMG = "E:/sitecapture-captures/ngv-video/void4k-register/images/void4k/"
WALK_IMG = "E:/sitecapture-captures/ngv-site/rebuild-roofvoid/images/"
# occluder geometry: trackA_render3's measured set, re-stated here only so render-args records it
from trackA_render3 import RIB_H2, RIB_HALF2, CREST_H2, CREST_HALF2, HUB_R2, HUB_H2, DECK_HALF2
from trackA_ortho import DECK_HV, DECK_H


def load_cameras(sim, traverses):
    """{name: Cam} in the hall frame. Stills 'vNNN' from the mapped model, walk frames
    'w<k>_<frame>' from the rebuild model (the frame the walk images are named for)."""
    from colmap_bin import read_model
    out = {}
    cams, imgs, _ = read_model(MAPPED, with_points2d=False)
    for im in imgs.values():
        if not im.name.startswith("void4k"):
            continue          # the mapped model's own w1 copies are the rebuild model's, taken below
        c = cams[im.camera_id]
        out[os.path.basename(im.name)[:-4]] = G.Cam(c.model, c.width, c.height, c.params, im.R(), im.t).to_frame(sim)
    cams, imgs, _ = read_model(REBUILD, with_points2d=False)
    for im in imgs.values():
        tr = im.name.split("_")[0]
        if tr not in traverses:
            continue
        c = cams[im.camera_id]
        out[im.name[:-4]] = G.Cam(c.model, c.width, c.height, c.params, im.R(), im.t).to_frame(sim)
    return out


def image_path(name):
    if name.startswith("v"):
        return STILL_IMG + name + ".jpg"
    return WALK_IMG + name + ".png"


class ImageCache:
    """LRU of decoded frames. Walk frames are 6 MB each and stills 25 MB, so the cap is what keeps
    a tile's working set in RAM when four tiles render in parallel."""

    def __init__(self, cap=60):
        self.cap, self.d, self.order = cap, {}, []

    def __call__(self, name):
        if name not in self.d:
            im = cv2.imread(image_path(name), cv2.IMREAD_COLOR)
            if im is None:
                raise IOError("missing image " + image_path(name))
            self.d[name] = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            self.order.append(name)
            if len(self.order) > self.cap:
                del self.d[self.order.pop(0)]
        return self.d[name]


def render_tile(px0, py0, tw, th, mm, hu0, hv0, cams, names, factors, dbufs, get_img, Fs, cellF,
                slab, gsd_max, corr):
    """trackA_render3.render_tile plus a min-gsd channel (the best gsd ANY camera offers for the
    pixel, whatever frame is finally drawn there): that is what makes the gsd sweep exact."""
    px = px0 + np.arange(tw)
    py = py0 + np.arange(th)
    PX, PY = np.meshgrid(px, py)
    hu = hu0 + (PX.ravel() + 0.5) * mm / 1000.0
    hv = hv0 + (PY.ravel() + 0.5) * mm / 1000.0
    hu_l, hv_l = hu.copy(), hv.copy()          # lattice (pixel) position, before the joint correction
    if corr is not None:
        hu, hv = corr(hu, hv)
    P, n, cval = surface_with_corr(hu, hv, slab, Fs, cellF)
    npx = len(hu)
    # facet id: which of the 4 planar triangles of its bay the pixel is on (0 east 1 west 2 north 3 south),
    # so a frame seam falls on a rib line instead of on an arbitrary grid
    du = hu_l - (G.HU0 + np.round((hu_l - G.HU0) / G.PU) * G.PU)
    dv = hv_l - (G.HV0 + np.round((hv_l - G.HV0) / G.PV) * G.PV)
    ew = np.abs(du) / (G.PU / 2) >= np.abs(dv) / (G.PV / 2)
    cell_id = np.where(ew, np.where(du >= 0, 0, 1), np.where(dv >= 0, 2, 3))
    ncell = 4
    samp = np.linspace(0, npx - 1, 600).astype(int)
    best_score = np.full(npx, np.inf, np.float32)
    best_cam = np.full(npx, 65535, np.uint16)
    best_gsd = np.zeros(npx, np.float32)
    min_gsd = np.full(npx, np.inf, np.float32)
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
        np.minimum.at(min_gsd, idx, gsd)
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
    # per facet: frames ranked by quality mass (sum of 1/score over the facet pixels they see), greedy fill
    for f in range(ncell):
        if cell_obs[f] == 0 or not cell_sum:
            continue
        ranked = sorted(((cell_mass[ci][f], ci) for ci in cell_sum if cell_cnt[ci][f] > 0), reverse=True)
        fpix = np.nonzero((cell_id == f) & observed)[0]
        left = np.ones(len(fpix), bool)
        for mass, ci in ranked[:16]:
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
        col = cv2.remap(im, mapx.reshape(rows, 4096), mapy.reshape(rows, 4096), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE)
        col = col.reshape(-1, 3)[:nsel]
        rgb[sel] = col
        grey = (0.299 * col[:, 0] + 0.587 * col[:, 1] + 0.114 * col[:, 2]).astype(int)
        hist[int(ci)] = np.bincount(np.clip(grey, 0, 255), minlength=256)
    final_gsd[~observed] = 0
    min_gsd[~observed] = 0
    return (rgb.reshape(th, tw, 3), final_cam.reshape(th, tw), final_gsd.reshape(th, tw),
            observed.reshape(th, tw), cval.reshape(th, tw).astype(np.float32),
            min_gsd.reshape(th, tw), hist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mm", type=float, default=4.0)
    ap.add_argument("--slab", type=float, default=0.02)
    ap.add_argument("--gsd-max", type=float, default=20.0)
    ap.add_argument("--hu1", type=float, default=G.PLATE_HU[1] + G.PU)
    ap.add_argument("--exclude", default="v021,v022,v025-v028",
                    help="stills to drop (trackA's set: blurred / mis-registered)")
    ap.add_argument("--traverses", default="w1,w2,w4,w5")
    ap.add_argument("--walk-factor", type=float, default=2.5,
                    help="score penalty on a 1080p walk frame so a 4K still wins a tie")
    ap.add_argument("--corr", default=None)
    ap.add_argument("--no-corr", action="store_true", help="drop the dense-cloud residual field")
    ap.add_argument("--depth-only", action="store_true",
                    help="build the depth-buffer cache and stop (so parallel tile jobs share it)")
    ap.add_argument("--only-tiles", default=None, help="comma list of py0_px0 tiles to render")
    ap.add_argument("--cache-cap", type=int, default=60)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "tiles"), exist_ok=True)
    sim = G.load_sim(a.sim)
    traverses = set(a.traverses.split(","))
    cams_all = load_cameras(sim, traverses)
    excl = parse_exclude(a.exclude)
    names = [n for n in sorted(cams_all) if n not in excl]
    factors = np.array([1.0 if n.startswith("v") else a.walk_factor for n in names], np.float32)
    cams = {n: cams_all[n] for n in names}
    per = {}
    for n in names:
        per[n.split("_")[0] if "_" in n else "stills"] = per.get(n.split("_")[0] if "_" in n else "stills", 0) + 1
    print("cameras used", len(names), per, "excluded", sorted(excl & set(cams_all)), flush=True)
    t0 = time.time()
    dbufs = depth_buffers(cams, sim, os.path.join(a.out, "depth-buffers.npz"))
    print("depth buffers ready", round(time.time() - t0, 1), "s", flush=True)
    if a.depth_only:
        return
    Fs, cellF = residual_field(sim)
    if a.no_corr:
        Fs = np.full_like(Fs, np.nan)
    print("residual field: covered cells", int(np.isfinite(Fs).sum()), "of", Fs.size,
          "mean corr (m)", round(float(np.nanmean(Fs)), 4), flush=True)
    corr = make_corr(a.corr) if a.corr else None
    get_img = ImageCache(cap=a.cache_cap)
    hu0, hv0 = G.PLATE_HU[0], G.PLATE_HV[0]
    W = int(round((a.hu1 - hu0) * 1000 / a.mm))
    H = int(round((G.PLATE_HV[1] - hv0) * 1000 / a.mm))
    print("ortho size", W, "x", H, "hu", hu0, "..", a.hu1, flush=True)
    # tiles aligned to the bay grid, so a facet never straddles two tiles
    xs = [int(round(i * G.PU * 1000 / a.mm)) for i in range(int(round((a.hu1 - hu0) / G.PU)) + 1)]
    xs[-1] = W
    ys = [0, int(round(G.PV * 1000 / a.mm)), H]
    tiles = []
    for jy in range(len(ys) - 1):
        for ix in range(len(xs) - 1):
            tiles.append((xs[ix], ys[jy], xs[ix + 1] - xs[ix], ys[jy + 1] - ys[jy]))
    args_path = os.path.join(a.out, "render-args.json")
    if not a.only_tiles or not os.path.exists(args_path):
        json.dump({"names": names, "factors": factors.tolist(), "W": W, "H": H, "mm": a.mm,
                   "tile": 0, "slab": a.slab, "hu0": hu0, "hv0": hv0, "hu1": a.hu1,
                   "hv1": G.PLATE_HV[1], "gsd_max": a.gsd_max, "sim": a.sim, "corr": a.corr,
                   "excluded": sorted(excl), "walk": True, "traverses": sorted(traverses),
                   "models": {"stills": MAPPED, "walk": REBUILD},
                   "occluders": {"rib_half_m": RIB_HALF2, "rib_h_m": RIB_H2,
                                 "crest_half_m": CREST_HALF2, "crest_h_m": CREST_H2,
                                 "hub_r_m": HUB_R2, "hub_h_m": HUB_H2, "deck_hv": DECK_HV,
                                 "deck_half_m": DECK_HALF2, "deck_h_m": DECK_H}},
                  open(args_path, "w"), indent=1)
    if a.only_tiles:
        want = set(a.only_tiles.split(","))
        tiles = [t for t in tiles if f"{t[1]}_{t[0]}" in want]
    print("tiles", len(tiles), flush=True)
    for k, (px0, py0, tw, th) in enumerate(tiles):
        path = os.path.join(a.out, "tiles", f"t_{py0}_{px0}.npz")
        if os.path.exists(path):
            continue
        rgb, cam, gsd, obs, cval, mgsd, hist = render_tile(
            px0, py0, tw, th, a.mm, hu0, hv0, cams, names, factors, dbufs, get_img, Fs, cellF,
            a.slab, a.gsd_max, corr)
        hk = np.array(sorted(hist), np.int32)
        hv_ = np.stack([hist[int(c)] for c in hk]) if len(hk) else np.zeros((0, 256), np.int64)
        np.savez_compressed(path, rgb=rgb, cam=cam, gsd=gsd, obs=obs, corr=cval, mingsd=mgsd,
                            hist_cams=hk, hist=hv_)
        print(f"tile {k+1}/{len(tiles)} ({px0},{py0}) observed {obs.mean()*100:.1f}%"
              f"  {round(time.time()-t0)} s", flush=True)
    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
