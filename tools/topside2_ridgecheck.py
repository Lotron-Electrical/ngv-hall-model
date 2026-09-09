"""Which track is out of register? Settle it on the one feature both tracks and the 3D data share:
the mid crest ridge, the ridge line the catwalk runs along, at lattice hv = 7.544.

Three independent statements about the same line, per bay:
  CLOUD    the catwalk deck is the strongest thing in the roof-void cloud. Its hv profile (cells
           0.33-0.62 m above the modelled plate) gives the ridge position with no imagery involved.
  TRACK A  this ortho cuts the deck band out at the lattice hv, so the ridge cannot be measured in
           the image; what CAN be measured is that the observed area stops where the cloud says the
           deck starts. The gap's centre is reported.
  TRACK B  the bake's bottom ortho shows the ridge as a dark band. Matched-filtered against a wide
           search so a half-metre slip cannot hide.

If the cloud and track A agree and track B does not, the disagreement between the two orthos is track
B's registration, not this one's.

python topside2_ridgecheck.py <topside dir> [--bottom <png>] [--meta <json>] [--out json]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import SCR

BOTTOM = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-ortho-v29.png"
BMETA = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-meta-v29.json"
RIDGE_HV = 7.544
DECK_LO, DECK_HI = 0.33, 0.62      # the deck slab, above the ribs and below the hub nodes
BAND = (6.0, 9.1)                  # hv window the ridge is searched in


def cloud_ridge(sim, heightmap, hu_lo, hu_hi):
    z = np.load(heightmap)
    Hmax, N = z["Hmax"], z["N"]
    x0, z0, cell = float(z["x0"]), float(z["z0"]), float(z["cell"])
    iz, ix = np.nonzero(N >= 3)
    P = G.apply_sim(sim, np.stack([x0 + (ix + 0.5) * cell, Hmax[iz, ix], z0 + (iz + 0.5) * cell], 1))
    hu, hv = G.xz_to_huv(P[:, 0], P[:, 2])
    h = P[:, 1] - G.surface_y(hu, hv, 0.0)
    m = (h > DECK_LO) & (h < DECK_HI) & (hu >= hu_lo) & (hu < hu_hi) & (hv > BAND[0]) & (hv < BAND[1])
    if m.sum() < 150:
        return None
    hist, edges = np.histogram(hv[m], bins=np.arange(BAND[0], BAND[1], 0.02))
    c = 0.5 * (edges[:-1] + edges[1:])
    sel = hist > 0.5 * hist.max()
    lo, hi = float(c[sel].min()), float(c[sel].max())
    return {"cells": int(m.sum()), "peak_hv": float(c[int(np.argmax(hist))]),
            "half_max_span_hv": [round(lo, 3), round(hi, 3)],
            "centre_hv": round(0.5 * (lo + hi), 3),
            "offset_from_lattice_mm": round((0.5 * (lo + hi) - RIDGE_HV) * 1000, 1)}


def band_fit(prof, hv_axis, width_m, min_contrast=4.0):
    """matched filter for a dark band of the given width; returns (hv, contrast)."""
    step = hv_axis[1] - hv_axis[0]
    w = max(1, int(round(width_m / 2 / step)))
    ker = np.zeros(6 * w + 1)
    ker[2 * w:4 * w + 1] = -1.0 / (2 * w + 1)
    ker[:w] = 0.5 / w
    ker[-w:] = 0.5 / w
    good = np.isfinite(prof)
    if good.sum() < 6 * w + 2:
        return None
    pz = np.where(good, prof, np.nanmedian(prof[good]))
    resp = np.convolve(pz, ker[::-1], mode="same")
    resp[:3 * w] = -np.inf
    resp[-3 * w:] = -np.inf
    i = int(np.argmax(resp))
    if not np.isfinite(resp[i]) or resp[i] < min_contrast:
        return None
    y0_, y1_, y2_ = -resp[i - 1], -resp[i], -resp[i + 1]
    den = y0_ - 2 * y1_ + y2_
    sub = 0.5 * (y0_ - y2_) / den if den != 0 else 0.0
    return float(hv_axis[i] + np.clip(sub, -1, 1) * step), float(resp[i])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--bottom", default=BOTTOM)
    ap.add_argument("--meta", default=BMETA)
    ap.add_argument("--heightmap", default=SCR + "void_dense_heightmap.npz")
    ap.add_argument("--sim", default="E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackA/void-to-hall-trackA-final.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = a.dir
    args = json.load(open(os.path.join(d, "render-args.json")))
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    sim = G.load_sim(a.sim)
    obs = cv2.imread(os.path.join(d, "topside-observed.png"), cv2.IMREAD_GRAYSCALE) > 127
    bmeta = json.load(open(a.meta))
    bot = cv2.imread(a.bottom, cv2.IMREAD_GRAYSCALE).astype(np.float32)
    bmm, bhu0, bhv0 = bmeta["mm_per_px"], bmeta["hu0"], bmeta["hv0"]
    rows = {}
    for i in range(0, 8):
        hu_lo = G.HU0 - G.PU / 2 + (i - 1) * G.PU
        hu_hi = hu_lo + G.PU
        e = {"bay_i": i, "hu_range": [round(hu_lo, 2), round(hu_hi, 2)]}
        e["cloud"] = cloud_ridge(sim, a.heightmap, hu_lo, hu_hi)
        # track A: the centre of the unobserved deck gap, per bay
        c0 = int(max(0, (hu_lo - hu0) * 1000 / mm))
        c1 = int(min(obs.shape[1], (hu_hi - hu0) * 1000 / mm))
        r0 = int((BAND[0] - hv0) * 1000 / mm)
        r1 = int((BAND[1] - hv0) * 1000 / mm)
        if c1 > c0 and r1 > r0:
            frac = obs[r0:r1, c0:c1].mean(1)
            hv_ax = hv0 + (np.arange(r0, r1) + 0.5) * mm / 1000
            gap = frac < 0.02
            if gap.any():
                idx = np.nonzero(gap)[0]
                # the widest run of unobserved rows is the deck cut
                brk = np.nonzero(np.diff(idx) > 1)[0]
                runs = np.split(idx, brk + 1)
                run = max(runs, key=len)
                e["trackA_gap"] = {"hv_lo": round(float(hv_ax[run[0]]), 3),
                                   "hv_hi": round(float(hv_ax[run[-1]]), 3),
                                   "centre_hv": round(float(0.5 * (hv_ax[run[0]] + hv_ax[run[-1]])), 3),
                                   "offset_from_lattice_mm": round(float(0.5 * (hv_ax[run[0]] + hv_ax[run[-1]]) - RIDGE_HV) * 1000, 1)}
        # track B: the dark ridge band in the bake
        bc0 = int(max(0, (hu_lo - bhu0) * 1000 / bmm))
        bc1 = int(min(bot.shape[1], (hu_hi - bhu0) * 1000 / bmm))
        br0 = int(max(0, (BAND[0] - bhv0) * 1000 / bmm))
        br1 = int(min(bot.shape[0], (BAND[1] - bhv0) * 1000 / bmm))
        if bc1 - bc0 > 50 and br1 - br0 > 50:
            seg = bot[br0:br1, bc0:bc1]
            valid = seg > 0
            prof = np.where(valid.sum(1) > 0.3 * seg.shape[1],
                            np.divide(np.where(valid, seg, 0).sum(1), np.maximum(valid.sum(1), 1)), np.nan)
            hv_ax = bhv0 + (np.arange(br0, br1) + 0.5) * bmm / 1000
            f = band_fit(prof, hv_ax, 0.45)
            if f:
                e["trackB_ridge"] = {"hv": round(f[0], 3), "contrast": round(f[1], 1),
                                     "offset_from_lattice_mm": round((f[0] - RIDGE_HV) * 1000, 1)}
        rows["bay_i_%d" % i] = e
        cl = e.get("cloud") or {}
        ga = e.get("trackA_gap") or {}
        tb = e.get("trackB_ridge") or {}
        print("bay i=%d  cloud deck centre hv %-7s (%+7s mm)   trackA gap centre %-7s (%+7s mm)   "
              "trackB ridge %-7s (%+8s mm)"
              % (i, cl.get("centre_hv", "-"), cl.get("offset_from_lattice_mm", "-"),
                 ga.get("centre_hv", "-"), ga.get("offset_from_lattice_mm", "-"),
                 tb.get("hv", "-"), tb.get("offset_from_lattice_mm", "-")), flush=True)

    def agg(key, sub):
        v = [r[key][sub] for r in rows.values() if r.get(key)]
        return {"n": len(v), "median_mm": round(float(np.median(v)), 1),
                "abs_max_mm": round(float(np.max(np.abs(v))), 1)} if v else None
    summary = {"lattice_ridge_hv": RIDGE_HV,
               "cloud_vs_lattice": agg("cloud", "offset_from_lattice_mm"),
               "trackA_gap_vs_lattice": agg("trackA_gap", "offset_from_lattice_mm"),
               "trackB_ridge_vs_lattice": agg("trackB_ridge", "offset_from_lattice_mm")}
    print(json.dumps(summary, indent=1))
    out = {"summary": summary, "per_bay": rows,
           "note": "the cloud is imagery-free evidence; track A's gap is where the render stops "
                   "because of the deck; track B's ridge is the dark band in the bake"}
    p = a.out or os.path.join(d, "ridge-check.json")
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
