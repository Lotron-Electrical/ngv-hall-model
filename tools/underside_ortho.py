"""Underside orthophoto of the NGV Great Hall canopy, rendered straight from the posed frames.

WHY: trackB/bottom-ortho-v29.png is unwrapped from the BAKED atlas (~6.5 mm/texel, and the bake
itself averages many views), so it is soft everywhere. Every posed underside frame is already in
the certified hall model, so the glass can be resampled once, from the single sharpest camera
that actually sees each patch, with no baking step in between.

Method, per plate pixel at --mm (4 mm default, bottom-meta-v29 origin and convention):
  1. hall xyz on the UNDERSIDE of the glass (underside_geom.Surface: the sim's inverted-pyramid
     lattice, offset PROUD below the plate face),
  2. project into every posed camera of the source class with the COLMAP OPENCV model (the
     distortion is applied on the way OUT, so the raw frame is sampled at the distorted pixel and
     nothing is resampled twice),
  3. reject the pixel where it is outside the frame OR outside the distortion model's valid
     domain (underside_geom.distortion_ok), where incidence exceeds --max-inc, or where
     the analytic occluders hide it FROM BELOW (rib soffits and their 0.3 m depth, the hub nodes,
     the house lighting truss, the twelve columns),
  4. choose ONE camera per 32 px cell by gsd = distance/f/cos(incidence), times a per-source
     factor and a per-frame sharpness factor (Laplacian variance, so a motion-blurred day4k frame
     loses to a sharp one), then resample that camera at full resolution.
No mask pixel is ever painted from anything but a real camera: the visibility test is re-run per
pixel in the resampling pass, and pixels no camera sees stay unobserved.

  python underside_ortho.py --source day4k|night|walk|all --out <dir> [--mm 4] [--workers 12]

Outputs in <out>/<source>/: ortho.png, mask.png, gsd.png (uint16 mm), cam.png (uint16 index),
meta.json (cameras, coverage per bay, gsd distribution), tiles/*.npz.
"""
import os
import sys
import json
import time
import argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import underside_geom as U
import trackA_geom as G

CELL = 32        # camera-choice cell, px
STRIDE = 4       # the choice pass runs on every 4th pixel: 64 samples a cell is plenty and it
                 # keeps the all-cameras pass 16x cheaper than the resampling pass
NOCAM = 65535

_S = {}          # per-worker globals (cameras, surface, image cache)


# ----------------------------------------------------------------------------- sharpness
def _lapvar(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return 0.0
    g = cv2.resize(im, (im.shape[1] // 4, im.shape[0] // 4), interpolation=cv2.INTER_AREA).astype(np.float32)
    m = float(g.mean())
    if m < 1e-3:
        return 0.0
    # normalised by mean^2 so an exposure difference between day and night frames does not
    # masquerade as sharpness
    return float(cv2.Laplacian(g, cv2.CV_32F).var() / (m * m))


def sharpness(cams, cache, workers):
    have = json.load(open(cache)) if os.path.exists(cache) else {}
    todo = [n for n in cams if n not in have]
    if todo:
        from multiprocessing import Pool
        with Pool(workers) as p:
            for n, v in zip(todo, p.map(_lapvar, [cams[n][1] for n in todo], chunksize=4)):
                have[n] = v
        json.dump(have, open(cache, "w"), indent=0)
    return have


# ------------------------------------------------------------------------------ visibility
def visible(cam, P, n, surf, cols, max_inc_cos, steel=None, margin=8):
    """indices of P this camera really sees, with pixel uv and gsd (mm/px)."""
    u, v, z = cam.project(P)
    # the frame test is not enough on its own: see underside_geom.distortion_ok
    ok = cam.inside(u, v, z, margin=margin) & U.distortion_ok(cam, P)
    if not ok.any():
        return None
    idx = np.nonzero(ok)[0]
    d = P[idx] - cam.center
    dist = np.linalg.norm(d, axis=1)
    cosi = np.abs(np.einsum("ij,ij->i", d / dist[:, None], n[idx]))
    keep = cosi > max_inc_cos
    idx, dist, cosi = idx[keep], dist[keep], cosi[keep]
    if not len(idx):
        return None
    occ = U.occluded_from_below(surf, P[idx], cam.center, cols,
                                None if steel is None else steel[idx])
    idx, dist, cosi = idx[~occ], dist[~occ], cosi[~occ]
    if not len(idx):
        return None
    gsd = 1000.0 * dist / cam.params[0] / cosi
    # a mild penalty at the frame corners, where the distortion model is least trustworthy
    r = np.hypot((u[idx] - cam.w / 2) / (cam.w / 2), (v[idx] - cam.h / 2) / (cam.h / 2))
    return idx, u[idx], v[idx], gsd.astype(np.float32), (gsd * (1 + 0.30 * r * r)).astype(np.float32)


# ---------------------------------------------------------------------------------- tiles
def render_tile(args):
    px0, py0, tw, th = args
    S = _S
    surf, cols, mm = S["surf"], S["cols"], S["mm"]
    names, cams, factors = S["names"], S["cams"], S["factors"]
    mic = S["max_inc_cos"]
    PX, PY = np.meshgrid(px0 + np.arange(tw), py0 + np.arange(th))
    hu = U.HU0_RASTER + (PX.ravel() + 0.5) * mm / 1000.0
    hv = U.HV0_RASTER + (PY.ravel() + 0.5) * mm / 1000.0
    inplate = surf.in_plate(hu, hv)
    npx = len(hu)
    rgb = np.zeros((npx, 3), np.uint8)
    camid = np.full(npx, NOCAM, np.uint16)
    gsdm = np.zeros(npx, np.float32)
    if not inplate.any():
        return px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw)
    P, nrm = surf.xyz_n(hu, hv)
    steel = surf.steel_code(hu, hv)

    # --- pass 1: every camera, on a stride grid, to pick one camera per cell
    ncx = (tw + CELL - 1) // CELL
    ncy = (th + CELL - 1) // CELL
    ncell = ncx * ncy
    sy, sx = np.meshgrid(np.arange(0, th, STRIDE), np.arange(0, tw, STRIDE), indexing="ij")
    sub = (sy.ravel() * tw + sx.ravel())
    sub = sub[inplate[sub]]
    if not len(sub):
        return px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw)
    cell_of = ((sub // tw) // CELL) * ncx + ((sub % tw) // CELL)
    Ps, ns, sts = P[sub], nrm[sub], steel[sub]
    probe = np.linspace(0, len(sub) - 1, min(400, len(sub))).astype(int)
    csum, ccnt = {}, {}
    obs_sub = np.zeros(len(sub), bool)
    for ci, name in enumerate(names):
        cam = cams[name]
        u, v, z = cam.project(Ps[probe])
        if not cam.inside(u, v, z, margin=-cam.w // 3).any():
            continue     # nothing of this tile is anywhere near the frame
        res = visible(cam, Ps, ns, surf, cols, mic, sts)
        if res is None:
            continue
        idx, _, _, _, score = res
        score = score * factors[ci]
        obs_sub[idx] = True
        csum[ci] = np.bincount(cell_of[idx], weights=score, minlength=ncell)
        ccnt[ci] = np.bincount(cell_of[idx], minlength=ncell)
    if not csum:
        return px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw)
    cell_obs = np.bincount(cell_of[obs_sub], minlength=ncell)
    cis = np.array(sorted(csum))
    Ssum = np.stack([csum[c] for c in cis])
    Ncnt = np.stack([ccnt[c] for c in cis])
    mean = np.where(Ncnt > 0, Ssum / np.maximum(Ncnt, 1), np.inf)
    # prefer a camera that covers most of the cell, but never leave a cell blank for want of one
    full = np.where(Ncnt >= 0.8 * cell_obs[None, :], mean, np.inf)
    k = np.argmin(full, axis=0)
    bad = ~np.isfinite(full[k, np.arange(ncell)])
    k2 = np.argmin(mean, axis=0)
    k = np.where(bad, k2, k)
    chosen = np.where(cell_obs > 0, cis[k], -1)

    # --- pass 2: the chosen cameras only, at full resolution
    cell_full = ((np.arange(npx) // tw) // CELL) * ncx + ((np.arange(npx) % tw) // CELL)
    for ci in np.unique(chosen[chosen >= 0]):
        pix = np.nonzero((chosen[cell_full] == ci) & inplate)[0]
        if not len(pix):
            continue
        cam = cams[names[ci]]
        res = visible(cam, P[pix], nrm[pix], surf, cols, mic, steel[pix])
        if res is None:
            continue
        idx, uu, vv, gsd, _ = res
        g = pix[idx]
        camid[g] = ci
        gsdm[g] = gsd
        im = S["img"](names[ci])
        nsel = len(g)
        rows = (nsel + 4095) // 4096
        mapx = np.zeros(rows * 4096, np.float32); mapx[:nsel] = uu
        mapy = np.zeros(rows * 4096, np.float32); mapy[:nsel] = vv
        col = cv2.remap(im, mapx.reshape(rows, 4096), mapy.reshape(rows, 4096),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        rgb[g] = col.reshape(-1, 3)[:nsel]
    return px0, py0, rgb.reshape(th, tw, 3), camid.reshape(th, tw), gsdm.reshape(th, tw)


class ImageCache:
    """A small LRU: the 4K day frames are 25 MB each decoded, and twelve workers hold one each."""

    def __init__(self, paths, cap):
        self.paths, self.cap, self.d, self.order = paths, cap, {}, []

    def __call__(self, name):
        if name not in self.d:
            im = cv2.imread(self.paths[name], cv2.IMREAD_COLOR)
            if im is None:
                raise RuntimeError("cannot read " + self.paths[name])
            self.d[name] = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            self.order.append(name)
            if len(self.order) > self.cap:
                del self.d[self.order.pop(0)]
        return self.d[name]


def _init(lat, slab, classes, names, factors, mm, max_inc, cap):
    surf = U.Surface(lat, slab)
    cams, paths = {}, {}
    for c in classes:
        for n, (cam, p) in U.load_class(c).items():
            cams[c + "/" + n] = cam
            paths[c + "/" + n] = p
    _S.update(surf=surf, cams=cams, names=names, factors=np.asarray(factors, np.float32), mm=mm,
              cols=[(np.array(h["box"][0]), np.array(h["box"][1])) for h in lat["heads"]],
              max_inc_cos=float(np.cos(np.radians(max_inc))), img=ImageCache(paths, cap))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="all", help="day4k | night | walk | all | a,b")
    ap.add_argument("--out", default=U.OUT_ROOT)
    ap.add_argument("--mm", type=float, default=U.MM_DEFAULT)
    ap.add_argument("--width", type=int, default=U.W_DEFAULT)
    ap.add_argument("--height", type=int, default=U.H_DEFAULT)
    ap.add_argument("--tile", type=int, default=1024)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--slab", type=float, default=U.PROUD)
    ap.add_argument("--max-inc", type=float, default=75.0)
    ap.add_argument("--cache", type=int, default=14, help="decoded frames held per worker")
    a = ap.parse_args()

    classes = list(U.CLASSES) if a.source == "all" else a.source.split(",")
    for c in classes:
        if c not in U.CLASSES:
            raise SystemExit("unknown source class " + c)
    out = os.path.join(a.out, a.source)
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    lat = U.lattice(os.path.join(a.out, "lattice.json"))
    surf = U.Surface(lat, a.slab)
    print("lattice PU/PV %.3f/%.3f phase %.5f/%.5f plate hu %.3f..%.3f hv %.3f..%.3f bays %s"
          % (lat["PU"], lat["PV"], lat["phase_hu"], lat["phase_hv"], *lat["plate"], lat["bays"]), flush=True)

    allcams, names, factors, sh_all = {}, [], [], {}
    loaded, sharp = {}, {}
    for c in classes:
        loaded[c] = U.load_class(c)
        sharp[c] = sharpness(loaded[c], os.path.join(a.out, "sharpness-%s.json" % c), a.workers)
    # ONE median across every class in the run, not one per class. A per-class median would rate
    # each source against itself, and the whole point of the combined render is to let a genuinely
    # sharper source win: the 20260817 night scans measure ~5x the Laplacian variance of the
    # 20260809 day walks on the same patch of ceiling, and that has to count.
    med = float(np.median([sharp[c][n] for c in classes for n in loaded[c]])) or 1.0
    for c in classes:
        cc, sh = loaded[c], sharp[c]
        for n in sorted(cc):
            key = c + "/" + n
            allcams[key] = cc[n][0]
            # a blurred frame is pushed back in the ranking, not thrown away: sqrt keeps the
            # penalty proportionate so a slightly soft but much closer frame can still win
            f = float(np.clip((med / max(sh[n], 1e-9)) ** 0.5, 0.5, 3.0))
            names.append(key)
            factors.append(U.CLASSES[c]["factor"] * f)
            sh_all[key] = {"lapvar": sh[n], "factor": f}
        print("%s: %d frames, class lapvar median %.3f (run median %.3f)"
              % (c, len(cc), float(np.median([sh[n] for n in cc])), med), flush=True)
    print("cameras", len(names), flush=True)

    W, H = a.width, a.height
    tiles = []
    for py0 in range(0, H, a.tile):
        for px0 in range(0, W, a.tile):
            tw, th = min(a.tile, W - px0), min(a.tile, H - py0)
            hu_lo = U.HU0_RASTER + px0 * a.mm / 1000
            hu_hi = U.HU0_RASTER + (px0 + tw) * a.mm / 1000
            hv_lo = U.HV0_RASTER + py0 * a.mm / 1000
            hv_hi = U.HV0_RASTER + (py0 + th) * a.mm / 1000
            if hu_hi < surf.su0 or hu_lo > surf.su1 or hv_hi < surf.sv0 or hv_lo > surf.sv1:
                continue      # wholly off the plate: nothing to render, no camera to ask
            tiles.append((px0, py0, tw, th))
    print("tiles", len(tiles), "of", ((W + a.tile - 1) // a.tile) * ((H + a.tile - 1) // a.tile), flush=True)

    meta = {"source": a.source, "classes": {c: U.CLASSES[c]["note"] for c in classes},
            "raster": U.raster_meta(a.mm, W, H), "lattice": {k: lat[k] for k in
            ("PU", "PV", "RELIEF", "DIP", "RIBH", "phase_hu", "phase_hv", "plane", "plate", "bays")},
            "slab_below_plate_face_m": a.slab, "max_incidence_deg": a.max_inc, "cell_px": CELL,
            "occluders": {"ridge_half_m": U.RIDGE_HALF, "cross_half_m": U.CROSS_HALF,
                          "hip_half_m": U.HIP_HALF, "diag_half_m": U.DIAG_HALF,
                          "rib_depth_m": U.RIB_DEPTH, "hub_half_m": U.HUB_HALF,
                          "rig_hv": U.RIG_HV, "rig_y": U.RIG_Y, "columns": len(lat["heads"])},
            "cameras": names, "factors": [float(f) for f in factors], "frame_stats": sh_all}
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)

    from multiprocessing import Pool
    t0 = time.time()
    todo = [t for t in tiles if not os.path.exists(os.path.join(out, "tiles", "t_%d_%d.npz" % (t[1], t[0])))]
    print("to render", len(todo), flush=True)
    if todo:
        with Pool(a.workers, initializer=_init,
                  initargs=(lat, a.slab, classes, names, factors, a.mm, a.max_inc, a.cache)) as p:
            for k, (px0, py0, rgb, camid, gsdm) in enumerate(p.imap_unordered(render_tile, todo, chunksize=1)):
                np.savez_compressed(os.path.join(out, "tiles", "t_%d_%d.npz" % (py0, px0)),
                                    rgb=rgb, cam=camid, gsd=gsdm)
                print("tile %d/%d (%d,%d) observed %.1f%%  %ds"
                      % (k + 1, len(todo), px0, py0, 100.0 * (camid != NOCAM).mean(),
                         round(time.time() - t0)), flush=True)

    # ------------------------------------------------------------------- assemble + report
    RGB = np.zeros((H, W, 3), np.uint8)
    CAM = np.full((H, W), NOCAM, np.uint16)
    GSD = np.zeros((H, W), np.uint16)
    for px0, py0, tw, th in tiles:
        z = np.load(os.path.join(out, "tiles", "t_%d_%d.npz" % (py0, px0)))
        RGB[py0:py0 + th, px0:px0 + tw] = z["rgb"]
        CAM[py0:py0 + th, px0:px0 + tw] = z["cam"]
        GSD[py0:py0 + th, px0:px0 + tw] = np.clip(z["gsd"], 0, 65535).astype(np.uint16)
    mask = (CAM != NOCAM)
    cv2.imwrite(os.path.join(out, "ortho.png"), cv2.cvtColor(RGB, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(out, "mask.png"), (mask * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(out, "gsd.png"), GSD)
    cv2.imwrite(os.path.join(out, "cam.png"), CAM)

    # coverage is measured against the GLASS of the plate: the steel soffits are not glass and
    # the raster's east extension is not plate, so counting them would flatter the number
    py, px = np.mgrid[0:H, 0:W]
    hu = U.HU0_RASTER + (px + 0.5) * a.mm / 1000.0
    hv = U.HV0_RASTER + (py + 0.5) * a.mm / 1000.0
    del px, py
    plate = surf.in_plate(hu, hv)
    glass = plate & ~surf.on_steel(hu, hv)
    bi, bj = surf.bay(hu, hv)
    rep = {"plate_px": int(plate.sum()), "glass_px": int(glass.sum()),
           "observed_px": int(mask.sum()),
           "coverage_plate": float(mask[plate].mean()), "coverage_glass": float(mask[glass].mean()),
           "bays": {}, "per_class": {}, "gsd_mm": {}}
    for j in range(lat["bays"][1]):
        for i in range(lat["bays"][0]):
            b = glass & (bi == i) & (bj == j)
            if b.any():
                rep["bays"]["i%d_j%d" % (i, j)] = {"glass_px": int(b.sum()),
                                                   "coverage": float(mask[b].mean()),
                                                   "gsd_median_mm": float(np.median(GSD[b & mask])) if (b & mask).any() else None}
    g = GSD[mask]
    if g.size:
        rep["gsd_mm"] = {p: float(np.percentile(g, p)) for p in (5, 10, 25, 50, 75, 90, 95)}
    idx = CAM[mask].astype(int)
    cls_of = np.array([names[k].split("/")[0] for k in range(len(names))])
    for c in classes:
        sel = np.isin(idx, np.nonzero(cls_of == c)[0])
        rep["per_class"][c] = {"pixels": int(sel.sum()),
                               "share_of_observed": float(sel.mean()) if sel.size else 0.0,
                               "frames_used": int(len(np.unique(idx[sel])))}
    rep["frames_used_total"] = int(len(np.unique(idx)))
    meta["report"] = rep
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print("done", round(time.time() - t0), "s ->", out, flush=True)


if __name__ == "__main__":
    main()
