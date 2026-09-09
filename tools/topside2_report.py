"""Reporting pass over a topside2 render: the gsd_max coverage sweep, the per-bay table, the 1:1
crops, and the sharpness check against the earlier w1-only ortho.

The sweep is read off the min-gsd channel topside2_render.py carries (best gsd ANY camera offers for
the pixel), so coverage at a cap TIGHTER than the render's cap is exact rather than re-rendered.
Coverage is quoted twice: over the whole ortho frame (which runs one bay east of the GLB plate,
because the real hall does) and over the model plate rect alone, so the two are not confused.

Crops are picked, not chosen by hand: the best, median and worst covered 1000-px windows among the
windows that hold any data at all, so the previews cannot flatter the result.

python topside2_report.py <render dir> [--compare <ortho-walk dir>] [--caps 10,14,20]
"""
import sys, os, json, glob, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_assemble2 import lattice_overlay


def load_channels(d):
    """obs / gsd / mingsd of a render dir, assembled from its tiles."""
    args = json.load(open(os.path.join(d, "render-args.json")))
    W, H = args["W"], args["H"]
    obs = np.zeros((H, W), bool)
    gsd = np.zeros((H, W), np.float32)
    mgs = np.zeros((H, W), np.float32)
    for p in glob.glob(os.path.join(d, "tiles", "t_*.npz")):
        _, py0, px0 = os.path.basename(p)[:-4].split("_")
        py0, px0 = int(py0), int(px0)
        z = np.load(p)
        th, tw = z["obs"].shape[:2]
        obs[py0:py0 + th, px0:px0 + tw] = z["obs"]
        gsd[py0:py0 + th, px0:px0 + tw] = z["gsd"]
        if "mingsd" in z.files:
            mgs[py0:py0 + th, px0:px0 + tw] = z["mingsd"]
    return args, obs, gsd, mgs


def bay_grids(args):
    """per-column bay i and per-row bay j of the ortho frame."""
    W, H, mm = args["W"], args["H"], args["mm"]
    hu = args["hu0"] + (np.arange(W) + 0.5) * mm / 1000
    hv = args["hv0"] + (np.arange(H) + 0.5) * mm / 1000
    bi = np.floor((hu - (G.HU0 - G.PU / 2)) / G.PU).astype(int) + 1
    bj = np.floor((hv - (G.HV0 - G.PV / 2)) / G.PV).astype(int) + 1
    return hu, hv, bi, bj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--compare", default=None, help="an earlier render dir to measure sharpness against")
    ap.add_argument("--caps", default="10,14,20")
    ap.add_argument("--crop", type=int, default=1000)
    a = ap.parse_args()
    d = a.dir
    args, obs, gsd, mgs = load_channels(d)
    W, H, mm = args["W"], args["H"], args["mm"]
    caps = [float(c) for c in a.caps.split(",")]
    px_m2 = (mm / 1000.0) ** 2
    hu, hv, bi, bj = bay_grids(args)
    # the min-gsd map is what the sweep is read off, so it ships alongside the chosen-frame gsd map
    np.save(os.path.join(d, "topside-mingsd.npy"), mgs)
    cv2.imwrite(os.path.join(d, "topside-mingsd.png"), np.clip(mgs * 8, 0, 255).astype(np.uint8))
    # the GLB plate rect: the 8th bay east of it is real hall the model does not close
    in_plate = (hu >= G.PLATE_HU[0]) & (hu < G.PLATE_HU[1])
    plate_cols = np.nonzero(in_plate)[0]
    sl_plate = (slice(None), slice(plate_cols[0], plate_cols[-1] + 1))
    sweep = {}
    for c in caps:
        m = obs & (mgs > 0) & (mgs < c)
        sweep[str(c)] = {
            "frame_covered_frac": round(float(m.mean()), 5),
            "frame_covered_m2": round(float(m.sum()) * px_m2, 2),
            "plate_covered_frac": round(float(m[sl_plate].mean()), 5),
            "plate_covered_m2": round(float(m[sl_plate].sum()) * px_m2, 2),
        }
        print("gsd_max %5.1f mm: frame %.2f%% (%.1f m2)  plate rect %.2f%% (%.1f m2)"
              % (c, m.mean() * 100, m.sum() * px_m2, m[sl_plate].mean() * 100, m[sl_plate].sum() * px_m2))
    rendered = obs.mean()
    print("rendered (this render's own cap %.1f mm): frame %.2f%% (%.1f m2)"
          % (args["gsd_max"], rendered * 100, obs.sum() * px_m2))

    # ---- per-bay table; the sub-square is the 2x2 quarter of the bay (a=west/east, b=south/north)
    bays = {}
    for i in sorted(set(bi.tolist())):
        cols = np.nonzero(bi == i)[0]
        for j in sorted(set(bj.tolist())):
            rows = np.nonzero(bj == j)[0]
            if len(cols) == 0 or len(rows) == 0:
                continue
            sl = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
            ob, mg = obs[sl], mgs[sl]
            if ob.size == 0:
                continue
            e = {"bay_area_m2": round(ob.size * px_m2, 2),
                 "observed_frac": round(float(ob.mean()), 4),
                 "observed_m2": round(float(ob.sum()) * px_m2, 2),
                 "gsd_mm_median_observed": round(float(np.median(gsd[sl][ob])), 2) if ob.any() else None}
            for c in caps:
                e["frac_gsd_lt_%g" % c] = round(float(((mg > 0) & (mg < c)).mean()), 4)
            # sub-squares: the four quarters of the bay, the unit the lattice actually repeats on
            hh, ww = ob.shape
            sub = {}
            for si, (r0, r1) in enumerate(((0, hh // 2), (hh // 2, hh))):
                for sj, (c0, c1) in enumerate(((0, ww // 2), (ww // 2, ww))):
                    q = ob[r0:r1, c0:c1]
                    sub["%s%s" % ("SN"[si], "WE"[sj])] = round(float(q.mean()), 4)
            e["sub_square_observed_frac"] = sub
            bays["%d,%d" % (i, j)] = e
    for k, v in sorted(bays.items(), key=lambda kv: (int(kv[0].split(",")[0]), kv[0])):
        print(" bay %-4s obs %.3f  gsd<10 %.3f  gsd<14 %.3f  gsd<20 %.3f  median gsd %s"
              % (k, v["observed_frac"], v.get("frac_gsd_lt_10", 0), v.get("frac_gsd_lt_14", 0),
                 v.get("frac_gsd_lt_20", 0), v["gsd_mm_median_observed"]))

    # ---- crops: best / median / worst covered window that holds any data
    rgb = cv2.cvtColor(cv2.imread(os.path.join(d, "topside-ortho.png"), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    S = a.crop
    cov = []
    for y0 in range(0, H - S + 1, S // 2):
        for x0 in range(0, W - S + 1, S // 2):
            f = obs[y0:y0 + S, x0:x0 + S].mean()
            if f > 0.02:
                cov.append((f, x0, y0))
    cov.sort()
    picks = {}
    if cov:
        picks["best"] = cov[-1]
        picks["median"] = cov[len(cov) // 2]
        picks["worst"] = cov[0]
    pv = os.path.join(d, "preview")
    os.makedirs(pv, exist_ok=True)
    crop_meta = {}
    for name, (f, x0, y0) in picks.items():
        crop = rgb[y0:y0 + S, x0:x0 + S].copy()
        cv2.imwrite(os.path.join(pv, "crop-%s.jpg" % name), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 93])
        ov = lattice_overlay(crop.copy(), x0, y0, mm, args["hu0"], args["hv0"], args["hu1"], args["hv1"])
        cv2.imwrite(os.path.join(pv, "crop-%s-lattice.jpg" % name), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 93])
        crop_meta[name] = {"px": [x0, y0], "size_px": S, "observed_frac": round(float(f), 4),
                           "huv": [round(args["hu0"] + x0 * mm / 1000, 3), round(args["hv0"] + y0 * mm / 1000, 3)],
                           "bay": [int(bi[x0]), int(bj[y0])]}
        print("crop %-7s px %5d,%4d  huv %8.2f,%6.2f  observed %.1f%%" % (name, x0, y0, *crop_meta[name]["huv"], f * 100))

    # ---- sharpness: Laplacian variance on the pixels BOTH renders observed, so the comparison is
    # like for like (a window one render only half covers would otherwise score its background)
    sharp = None
    if a.compare:
        cargs, cobs, cgsd, _ = load_channels(a.compare)
        crgbp = os.path.join(a.compare, "topside-ortho.png")
        crgb = cv2.cvtColor(cv2.imread(crgbp, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        both = obs & cobs
        # the best-covered 1000 px window of the OVERLAP, so both have real data there
        best = None
        for y0 in range(0, H - S + 1, S // 2):
            for x0 in range(0, W - S + 1, S // 2):
                f = both[y0:y0 + S, x0:x0 + S].mean()
                if best is None or f > best[0]:
                    best = (f, x0, y0)
        f, x0, y0 = best
        m = both[y0:y0 + S, x0:x0 + S]

        def lapvar(img):
            g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
            L = cv2.Laplacian(g, cv2.CV_32F)
            return float(L[m].var()), float(g[m].std())
        v_new, s_new = lapvar(rgb[y0:y0 + S, x0:x0 + S])
        v_old, s_old = lapvar(crgb[y0:y0 + S, x0:x0 + S])
        for nm, img in (("sharp-new.jpg", rgb), ("sharp-old.jpg", crgb)):
            cv2.imwrite(os.path.join(pv, nm), cv2.cvtColor(img[y0:y0 + S, x0:x0 + S], cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 93])
        sharp = {"window_px": [x0, y0, S], "overlap_frac": round(float(f), 4),
                 "compare_dir": a.compare,
                 "laplacian_var": {"this": round(v_new, 2), "compare": round(v_old, 2)},
                 "grey_std": {"this": round(s_new, 2), "compare": round(s_old, 2)},
                 "gsd_mm_median": {"this": round(float(np.median(gsd[y0:y0 + S, x0:x0 + S][m])), 2),
                                   "compare": round(float(np.median(cgsd[y0:y0 + S, x0:x0 + S][m])), 2)},
                 "note": "measured on the pixels both renders observed inside the window"}
        print("sharpness window", x0, y0, "overlap %.1f%%" % (f * 100),
              "laplacian var this %.1f vs compare %.1f" % (v_new, v_old))

    out = {"render_dir": d, "mm_per_px": mm, "width": W, "height": H,
           "hu0": args["hu0"], "hv0": args["hv0"], "hu1": args["hu1"], "hv1": args["hv1"],
           "render_gsd_max_mm": args["gsd_max"],
           "cameras": len(args["names"]), "traverses": args.get("traverses"),
           "plate_rect_hu": list(G.PLATE_HU), "plate_rect_hv": list(G.PLATE_HV),
           "coverage_by_gsd_max": sweep,
           "rendered_frac_at_render_cap": round(float(rendered), 5),
           "coverage_per_bay": bays, "crops": crop_meta, "sharpness": sharp}
    json.dump(out, open(os.path.join(d, "coverage-report.json"), "w"), indent=1)
    print("wrote", os.path.join(d, "coverage-report.json"))


if __name__ == "__main__":
    main()
