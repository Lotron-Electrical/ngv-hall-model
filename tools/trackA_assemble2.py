"""Track A (resume, v2): assemble the rendered tiles of trackA_render2.py into the deliverables.

Writes in <render dir>:
  topside-ortho.png     RGB ortho, per-camera white-level gain applied (matrix white -> common level)
  topside-observed.png  255 where any accepted frame saw the surface
  topside-mask.png      255 = dark glass slab on the white matrix (ribs, clutter, unobserved = 0)
  topside-gsd.png/.npy  ground sampling distance of the chosen frame (png: x8, mm per image px)
  topside-cam.png       uint16 index into meta.frames_used (65535 = unobserved)
  topside-meta.json     frame, thresholds, gains, coverage per bay, piece statistics
  preview/*.jpg         downsized whole ortho, the mask, and 1:1 crops with and without the lattice

python trackA_assemble2.py <render dir> [--thresh auto|N] [--open 5] [--min-area-mm2 900]
                          [--crop hu,hv,name ...]
"""
import sys, os, json, glob, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G


def load_all(d):
    args = json.load(open(os.path.join(d, "render-args.json")))
    W, H = args["W"], args["H"]
    rgb = np.zeros((H, W, 3), np.uint8)
    cam = np.full((H, W), 65535, np.uint16)
    gsd = np.zeros((H, W), np.float32)
    obs = np.zeros((H, W), bool)
    hist = {}
    for p in glob.glob(os.path.join(d, "tiles", "t_*.npz")):
        _, py0, px0 = os.path.basename(p)[:-4].split("_")
        py0, px0 = int(py0), int(px0)
        z = np.load(p)
        th, tw = z["rgb"].shape[:2]
        rgb[py0:py0 + th, px0:px0 + tw] = z["rgb"]
        cam[py0:py0 + th, px0:px0 + tw] = z["cam"]
        gsd[py0:py0 + th, px0:px0 + tw] = z["gsd"]
        obs[py0:py0 + th, px0:px0 + tw] = z["obs"]
        if "hist_cams" in z.files:
            for c, h in zip(z["hist_cams"], z["hist"]):
                hist[int(c)] = hist.get(int(c), np.zeros(256, np.int64)) + h
    return args, rgb, cam, gsd, obs, hist


def camera_gains(hist, q=0.80, lo=0.7, hi=1.45):
    """per-camera gain so that the q-quantile grey (the white matrix) of every camera lands on the
    pixel-weighted median of those quantiles."""
    p = {}
    for c, h in hist.items():
        n = h.sum()
        if n < 2000:
            continue
        cdf = np.cumsum(h) / n
        p[c] = int(np.searchsorted(cdf, q))
    if not p:
        return {}, 0
    w = np.array([hist[c].sum() for c in p], float)
    v = np.array([p[c] for c in p], float)
    o = np.argsort(v)
    cw = np.cumsum(w[o]) / w.sum()
    target = float(v[o][np.searchsorted(cw, 0.5)])
    gains = {c: float(np.clip(target / max(p[c], 1), lo, hi)) for c in p}
    return gains, target


def bay_of(hu, hv):
    bi = np.floor((hu - (G.HU0 - G.PU / 2)) / G.PU).astype(int) + 1
    bj = np.floor((hv - (G.HV0 - G.PV / 2)) / G.PV).astype(int) + 1
    return bi, bj


def lattice_overlay(img, px0, py0, mm, hu0, hv0, hu1, hv1, thick=2):
    """edges red, cross cyan, diagonals yellow, anti-diagonals green, vertices magenta."""
    h, w = img.shape[:2]

    def to_px(hu, hv):
        return (hu - hu0) * 1000 / mm - px0, (hv - hv0) * 1000 / mm - py0

    def line(a, b, c, d, col):
        x1, y1 = to_px(a, b)
        x2, y2 = to_px(c, d)
        if max(x1, x2) < 0 or min(x1, x2) > w or max(y1, y2) < 0 or min(y1, y2) > h:
            return
        cv2.line(img, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), col, thick, cv2.LINE_AA)
    ni0 = int(np.floor((hu0 - G.HU0) / G.PU)) - 1
    ni1 = int(np.ceil((hu1 - G.HU0) / G.PU)) + 1
    for i in range(ni0, ni1 + 1):
        hu = G.HU0 + (i + 0.5) * G.PU
        line(hu, hv0, hu, hv1, (255, 0, 0))
        line(G.HU0 + i * G.PU, hv0, G.HU0 + i * G.PU, hv1, (0, 200, 255))
    for j in range(-2, 2):
        line(hu0, G.HV0 + (j + 0.5) * G.PV, hu1, G.HV0 + (j + 0.5) * G.PV, (255, 0, 0))
        line(hu0, G.HV0 + j * G.PV, hu1, G.HV0 + j * G.PV, (0, 200, 255))
    a, b = G.PU / 2, G.PV / 2
    for i in range(ni0, ni1 + 1):
        for j in range(-1, 1):
            cu, cv_ = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            line(cu - a, cv_ - b, cu + a, cv_ + b, (255, 220, 0))
            line(cu - a, cv_ + b, cu + a, cv_ - b, (255, 220, 0))
            line(cu + a, cv_, cu, cv_ + b, (0, 255, 80))
            line(cu, cv_ + b, cu - a, cv_, (0, 255, 80))
            line(cu - a, cv_, cu, cv_ - b, (0, 255, 80))
            line(cu, cv_ - b, cu + a, cv_, (0, 255, 80))
            x, y = to_px(cu, cv_)
            if 0 <= x < w and 0 <= y < h:
                cv2.circle(img, (int(x), int(y)), 12, (255, 0, 255), 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--thresh", default="auto")
    ap.add_argument("--open", type=int, default=9, help="opening kernel (px) to drop cables, joint lines, speckle")
    ap.add_argument("--delta", type=float, default=30.0, help="glass = grey below the local matrix white by this")
    ap.add_argument("--sat", type=float, default=20.0, help="or HSV saturation above this (coloured slabs)")
    ap.add_argument("--min-area-mm2", type=float, default=900.0)
    ap.add_argument("--gsd-good", type=float, default=10.0, help="gsd (mm/px) limit for the piece statistics")
    ap.add_argument("--crop", action="append", default=[])
    ap.add_argument("--no-gain", action="store_true")
    a = ap.parse_args()
    d = a.dir
    args, rgb, cam, gsd, obs, hist = load_all(d)
    W, H, mm = args["W"], args["H"], args["mm"]
    hu0, hv0, hu1, hv1 = args["hu0"], args["hv0"], args["hu1"], args["hv1"]
    names = args["names"]
    print("ortho", W, "x", H, "observed px", int(obs.sum()), f"({obs.mean()*100:.2f}%)")
    # ---- per-camera gain
    gains, target = ({}, 0) if a.no_gain else camera_gains(hist)
    if gains:
        g = np.ones(len(names) + 1, np.float32)
        for c, v in gains.items():
            g[c] = v
        gpix = g[np.minimum(cam, len(names))]
        rgb = np.clip(rgb.astype(np.float32) * gpix[..., None], 0, 255).astype(np.uint8)
        del gpix
        print("gains: target white", target, "range", min(gains.values()), max(gains.values()), "cams", len(gains))
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    sat = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1]
    # ---- glass = darker than the LOCAL matrix white by --delta, or clearly coloured (saturation > --sat)
    # local white = 85th percentile of the observed grey per 128-px block (0.5 m), gaps filled from neighbours
    B = 128
    hb, wb = (H + B - 1) // B, (W + B - 1) // B
    white = np.full((hb, wb), np.nan, np.float32)
    for by in range(hb):
        for bx in range(wb):
            o = obs[by * B:(by + 1) * B, bx * B:(bx + 1) * B]
            if o.sum() > 500:
                white[by, bx] = np.percentile(grey[by * B:(by + 1) * B, bx * B:(bx + 1) * B][o], 85)
    wz = np.where(np.isfinite(white), white, 0).astype(np.float32)
    wm = np.isfinite(white).astype(np.float32)
    for _ in range(8):
        num = cv2.blur(wz, (3, 3))
        den = cv2.blur(wm, (3, 3))
        fill = np.where((wm == 0) & (den > 0), num / np.maximum(den, 1e-6), wz)
        wm = np.where((wm == 0) & (den > 0), 1, wm)
        wz = fill
    white_full = cv2.resize(wz, (W, H), interpolation=cv2.INTER_LINEAR)
    if a.thresh == "auto":
        thresh = None
        dark = ((grey < white_full - a.delta) | (sat > a.sat)) & obs & (grey < 200)
        print("glass rule: grey < local white - %g (local white p10/50/90 %s) or saturation > %g" % (a.delta, np.percentile(white_full[obs], [10, 50, 90]).round(0), a.sat))
    else:
        thresh = float(a.thresh)
        dark = (grey < thresh) & obs
        print("glass threshold (grey <)", thresh)
    del sat, white_full
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.open, a.open))
    m = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # drop specks
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
    area_px = st[:, cv2.CC_STAT_AREA]
    min_px = a.min_area_mm2 / (mm * mm)
    keep = area_px >= min_px
    keep[0] = False
    mask = keep[lab]
    mask &= obs
    print("components", n - 1, "kept", int(keep.sum()))
    # ---- write full-size outputs
    cv2.imwrite(os.path.join(d, "topside-ortho.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(d, "topside-observed.png"), (obs * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(d, "topside-mask.png"), (mask * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(d, "topside-gsd.png"), np.clip(gsd * 8, 0, 255).astype(np.uint8))
    np.save(os.path.join(d, "topside-gsd.npy"), gsd)
    cv2.imwrite(os.path.join(d, "topside-cam.png"), cam.astype(np.uint16))
    # ---- coverage per bay and piece statistics
    px = np.arange(W)
    py = np.arange(H)
    hu = hu0 + (px + 0.5) * mm / 1000
    hv = hv0 + (py + 0.5) * mm / 1000
    bi_col = np.floor((hu - (G.HU0 - G.PU / 2)) / G.PU).astype(int) + 1
    bj_row = np.floor((hv - (G.HV0 - G.PV / 2)) / G.PV).astype(int) + 1
    good = obs & (gsd > 0) & (gsd < a.gsd_good)
    # rib footprint band (the surface under the ribs is never glass): exclude from the glass-share denominators
    HU, HV = np.meshgrid(hu, hv)
    from trackA_ortho import line_dists, DECK_HV
    cross, diag, crest, vert = line_dists(HU, HV)
    # the glass field: outside the rib footprints (0.16 m), the crest channel (0.45 m: kerb, gutter, drains,
    # cable trays), the hub nodes (0.4 m) and the catwalk band (0.6 m)
    field = ~((cross < 0.16) | (diag < 0.16) | (crest < 0.45) | (vert < 0.4) | (np.abs(HV - DECK_HV) < 0.6))
    del HU, HV, cross, diag, crest, vert
    n2, lab2, st2, cen2 = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    # a piece counts when it is inside the good (gsd < limit) region and does not touch unobserved pixels
    cx = cen2[:, 0]
    cy = cen2[:, 1]
    unobs_d = cv2.dilate((~obs).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    touch = np.zeros(n2, bool)
    touch[np.unique(lab2[unobs_d])] = True
    good_c = np.zeros(n2, bool)
    ok_i = (cy >= 0) & (cy < H) & (cx >= 0) & (cx < W)
    good_c[ok_i] = good[cy[ok_i].astype(int), cx[ok_i].astype(int)]
    piece_ok = good_c & ~touch
    piece_ok[0] = False
    bays = {}
    for i in range(0, int(bi_col.max()) + 1):
        for j in range(0, 2):
            cols = np.nonzero(bi_col == i)[0]
            rows = np.nonzero(bj_row == j)[0]
            if len(cols) == 0 or len(rows) == 0:
                continue
            sl = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
            ob = obs[sl]
            gd = good[sl]
            fl = field[sl]
            mk = mask[sl]
            area_bay = ob.size * (mm / 1000) ** 2
            lb = lab2[sl]
            ids = np.unique(lb[mk & gd])
            ids = ids[piece_ok[ids]]
            glass_area = mask[sl][gd & fl].sum() * (mm / 1000) ** 2
            field_area = (gd & fl).sum() * (mm / 1000) ** 2
            bays[f"{i},{j}"] = {
                "bay_area_m2": round(area_bay, 2),
                "observed_frac": round(float(ob.mean()), 4),
                "good_frac": round(float(gd.mean()), 4),
                "observed_m2": round(float(ob.sum()) * (mm / 1000) ** 2, 2),
                "good_m2": round(float(gd.sum()) * (mm / 1000) ** 2, 2),
                "glass_share_of_good_field": round(float(glass_area / field_area), 4) if field_area > 0.5 else None,
                "pieces_counted": int(len(ids)),
                "pieces_per_m2_of_good_field": round(float(len(ids) / field_area), 2) if field_area > 0.5 else None,
                "gsd_mm_median_observed": round(float(np.median(gsd[sl][ob])), 2) if ob.any() else None,
            }
    all_ids = np.nonzero(piece_ok)[0]
    areas = st2[all_ids, cv2.CC_STAT_AREA] * (mm / 1000) ** 2 * 1e4  # cm2
    eqd = np.sqrt(areas / np.pi * 4) * 10  # mm equivalent diameter
    bw = st2[all_ids, cv2.CC_STAT_WIDTH] * mm
    bh = st2[all_ids, cv2.CC_STAT_HEIGHT] * mm
    longest = np.maximum(bw, bh)
    stats = {
        "pieces_counted": int(len(all_ids)),
        "good_field_m2": round(float((good & field).sum() * (mm / 1000) ** 2), 2),
        "pieces_per_m2_of_good_field": round(float(len(all_ids) / max((good & field).sum() * (mm / 1000) ** 2, 1e-6)), 2),
        "glass_share_of_good_field": round(float(mask[good & field].sum() / max((good & field).sum(), 1)), 4),
        "area_cm2_percentiles_5_25_50_75_95": [round(float(v), 1) for v in np.percentile(areas, [5, 25, 50, 75, 95])] if len(areas) else None,
        "eq_diameter_mm_percentiles_5_25_50_75_95": [round(float(v), 0) for v in np.percentile(eqd, [5, 25, 50, 75, 95])] if len(eqd) else None,
        "longest_bbox_side_mm_percentiles_5_25_50_75_95": [round(float(v), 0) for v in np.percentile(longest, [5, 25, 50, 75, 95])] if len(longest) else None,
        "size_bins_mm_longest_side": {"<100": int((longest < 100).sum()), "100-250": int(((longest >= 100) & (longest < 250)).sum()),
                                      "250-400": int(((longest >= 250) & (longest < 400)).sum()), ">=400": int((longest >= 400).sum())},
    }
    print("piece stats", json.dumps(stats))
    for k_, v in sorted(bays.items()):
        if v["observed_frac"] > 0:
            print(" bay", k_, v)
    used = sorted(set(int(c) for c in np.unique(cam[obs])))
    meta = {
        "hu0": hu0, "hv0": hv0, "hu1": hu1, "hv1": hv1, "mm_per_px": mm, "width": W, "height": H,
        "pixel_centre": "hu = hu0 + (px + 0.5) * mm_per_px / 1000; hv = hv0 + (py + 0.5) * mm_per_px / 1000",
        "orientation": "row 0 = south edge (hv0), col 0 = west end (hu0); hv grows downward, hu rightward; columns east of the model plate (hu > -4.635625) are the 8th bay the GLB does not have",
        "huv_from_world": {"hu": "x*0.975681 + z*0.219196", "hv": "x*(-0.219196) + z*0.975681"},
        "frames_used": [names[c] for c in used],
        "frames_registered_not_used": [n for n in names if names.index(n) not in used],
        "frames_rejected": args["excluded"],
        "frames_not_registered": ["v023", "v024"],
        "chain": args["sim"], "corr": args.get("corr"), "slab_m": args["slab"], "gsd_max_mm": args["gsd_max"],
        "occluders": args["occluders"],
        "gain": {"white_quantile": 0.80, "target_grey": target, "per_frame": {names[c]: round(v, 4) for c, v in gains.items()}},
        "mask": {"rule": "grey < local matrix white (85th pct per 0.5 m block) - delta, or HSV saturation > sat; then opening, specks dropped" if thresh is None else "grey < %g" % thresh,
                 "delta": a.delta, "sat": a.sat, "open_px": a.open, "min_area_mm2": a.min_area_mm2,
                 "note": "255 = dark glass slab on the white matrix after the per-frame gain; rib footprints, hubs, crest channel, deck band and unobserved = 0 (never observed there or not glass)",
                 "field_for_stats": "outside rib footprints (0.16 m), crest channel (0.45 m), hubs (0.4 m), deck band (0.6 m), and gsd < gsd_good"},
        "coverage_per_bay": bays,
        "piece_stats_gsd_lt_%g" % a.gsd_good: stats,
        "gsd_png": "value/8 = mm per image pixel of the chosen frame, 0 = unobserved",
        "cam_png": "uint16 index into frames_used order of render-args names; 65535 = unobserved",
    }
    json.dump(meta, open(os.path.join(d, "topside-meta.json"), "w"), indent=1)
    # ---- previews
    pv = os.path.join(d, "preview")
    os.makedirs(pv, exist_ok=True)
    scale = 2000 / W
    small = cv2.resize(rgb, (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(pv, "ortho-small.jpg"), cv2.cvtColor(small, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    ov = lattice_overlay(small.copy(), 0, 0, mm / scale, hu0, hv0, hu1, hv1, thick=1)
    cv2.imwrite(os.path.join(pv, "ortho-small-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    ms = cv2.resize((mask * 255).astype(np.uint8), (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    obs_s = cv2.resize(obs.astype(np.uint8) * 255, (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    cov = np.zeros((ms.shape[0], ms.shape[1], 3), np.uint8)
    cov[..., 1] = obs_s // 2
    cov[..., 0] = ms
    cov[..., 1] = np.maximum(cov[..., 1], ms)
    cov[..., 2] = ms
    cv2.imwrite(os.path.join(pv, "coverage-small.jpg"), cv2.cvtColor(lattice_overlay(cov, 0, 0, mm / scale, hu0, hv0, hu1, hv1, thick=1), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    g = np.clip(gsd, 0, 20) / 20 * 255
    g = cv2.resize(g.astype(np.uint8), (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    gc = cv2.applyColorMap(g, cv2.COLORMAP_JET)
    gc[obs_s == 0] = 0
    cv2.imwrite(os.path.join(pv, "gsd-small.jpg"), gc)
    # observed region as a whole at 2000 px wide (crop to the observed bbox for a closer look)
    ys, xs = np.nonzero(obs[::8, ::8])
    if len(xs):
        x0, x1 = xs.min() * 8, min(W, xs.max() * 8 + 8)
        y0, y1 = ys.min() * 8, min(H, ys.max() * 8 + 8)
        reg = rgb[y0:y1, x0:x1]
        sc = min(1.0, 2000 / reg.shape[1], 2000 / reg.shape[0])
        regs = cv2.resize(reg, (int(reg.shape[1] * sc), int(reg.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(pv, "observed-region.jpg"), cv2.cvtColor(regs, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        ov = lattice_overlay(regs.copy(), x0 * sc, y0 * sc, mm / sc, hu0, hv0, hu1, hv1, thick=1)
        cv2.imwrite(os.path.join(pv, "observed-region-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
        mk = cv2.resize((mask[y0:y1, x0:x1] * 255).astype(np.uint8), (regs.shape[1], regs.shape[0]), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(pv, "observed-region-mask.jpg"), mk, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print("observed bbox px", x0, y0, x1, y1, "huv", round(hu0 + x0 * mm / 1000, 2), round(hv0 + y0 * mm / 1000, 2), round(hu0 + x1 * mm / 1000, 2), round(hv0 + y1 * mm / 1000, 2))
    for c in a.crop:
        hu_, hv_, name = c.split(",")
        hu_, hv_ = float(hu_), float(hv_)
        cx = int((hu_ - hu0) * 1000 / mm)
        cy = int((hv_ - hv0) * 1000 / mm)
        x0, y0 = max(0, cx - 500), max(0, cy - 500)
        x1, y1 = min(W, x0 + 1000), min(H, y0 + 1000)
        crop = rgb[y0:y1, x0:x1].copy()
        cv2.imwrite(os.path.join(pv, f"crop-{name}.jpg"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        ov = lattice_overlay(crop.copy(), x0, y0, mm, hu0, hv0, hu1, hv1)
        cv2.imwrite(os.path.join(pv, f"crop-{name}-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        mk = (mask[y0:y1, x0:x1] * 255).astype(np.uint8)
        cv2.imwrite(os.path.join(pv, f"crop-{name}-mask.jpg"), mk, [cv2.IMWRITE_JPEG_QUALITY, 92])
        ob = obs[y0:y1, x0:x1]
        print("crop", name, "px", x0, y0, "observed %.1f%%" % (ob.mean() * 100), "gsd median mm", round(float(np.median(gsd[y0:y1, x0:x1][ob])), 2) if ob.any() else None)
    print("wrote", d)


if __name__ == "__main__":
    main()
