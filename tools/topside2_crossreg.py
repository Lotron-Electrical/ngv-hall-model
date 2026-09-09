"""Does the topside ortho land on the same glass as track B's bottom ortho?

Both orthos are indexed by the same huv plate coordinates, so a slab at (hu, hv) must be the same
slab in both. They do NOT look alike: from below the glass is lit and the concrete matrix is dark,
from above the matrix is white and the slab backs are dark, so the two are near negatives of each
other and a raw correlation reads as noise whichever way it is signed. What survives the polarity
difference is the PATTERN: local contrast, sign removed. Both images are locally normalised (a 0.5 m
box mean subtracted, divided by the local spread) and the correlation is run on the absolute
normalised field, so a slab edge is a slab edge in either image.

Per bay and over the whole plate: the shift that maximises normalised cross-correlation, searched to
+-0.7 m. A peak at zero shift means track A and track B put the same glass in the same place. A peak
elsewhere is the registration difference between the two tracks, in mm.

python topside2_crossreg.py <topside dir> [--bottom <bottom-ortho.png>] [--meta <bottom-meta.json>]
                            [--search 0.7] [--out json]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

BOTTOM = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-ortho-v29.png"
BMETA = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-meta-v29.json"


def local_contrast(g, mask, box):
    """|grey - local mean| / local spread, over the valid mask. Polarity free."""
    g = g.astype(np.float32)
    m = mask.astype(np.float32)
    gm = g * m
    num = cv2.blur(gm, (box, box))
    den = cv2.blur(m, (box, box))
    mean = np.where(den > 0.05, num / np.maximum(den, 1e-6), 0)
    d = (g - mean) * m
    s2 = cv2.blur(d * d, (box, box))
    sd = np.sqrt(np.where(den > 0.05, s2 / np.maximum(den, 1e-6), 0)) + 1e-3
    return np.abs(d) / sd * m


def ncc_peak(A, MA, B, MB, half, step):
    """brute-force masked NCC of A against B over integer shifts; returns (dx, dy, ncc, table)."""
    best = (0, 0, -2.0)
    tab = np.full((2 * half // step + 1, 2 * half // step + 1), np.nan, np.float32)
    H, W = A.shape
    for iy, dy in enumerate(range(-half, half + 1, step)):
        ys_a = slice(max(0, dy), min(H, H + dy))
        ys_b = slice(max(0, -dy), min(H, H - dy))
        for ix, dx in enumerate(range(-half, half + 1, step)):
            xs_a = slice(max(0, dx), min(W, W + dx))
            xs_b = slice(max(0, -dx), min(W, W - dx))
            a = A[ys_a, xs_a]
            b = B[ys_b, xs_b]
            m = MA[ys_a, xs_a] & MB[ys_b, xs_b]
            n = int(m.sum())
            if n < 5000:
                continue
            av, bv = a[m], b[m]
            av = av - av.mean()
            bv = bv - bv.mean()
            den = np.sqrt((av * av).sum() * (bv * bv).sum())
            if den <= 0:
                continue
            c = float((av * bv).sum() / den)
            tab[iy, ix] = c
            if c > best[2]:
                best = (dx, dy, c)
    return best[0], best[1], best[2], tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--bottom", default=BOTTOM)
    ap.add_argument("--meta", default=BMETA)
    ap.add_argument("--search", type=float, default=0.7, help="search half-width, metres")
    ap.add_argument("--work-mm", type=float, default=16.0, help="correlation works at this pitch")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = a.dir
    args = json.load(open(os.path.join(d, "render-args.json")))
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    bmeta = json.load(open(a.meta))
    assert abs(bmeta["hu0"] - hu0) < 1e-6 and abs(bmeta["hv0"] - hv0) < 1e-6, "different huv origins"
    top = cv2.imread(os.path.join(d, "topside-ortho.png"), cv2.IMREAD_GRAYSCALE)
    obs = cv2.imread(os.path.join(d, "topside-observed.png"), cv2.IMREAD_GRAYSCALE) > 127
    bot = cv2.imread(a.bottom, cv2.IMREAD_GRAYSCALE)
    bmm = bmeta["mm_per_px"]
    # put the bottom ortho on the topside grid: same origin, so it is a pure scale
    scale = bmm / mm
    bw = int(round(bot.shape[1] * scale))
    bh = int(round(bot.shape[0] * scale))
    botr = cv2.resize(bot, (bw, bh), interpolation=cv2.INTER_AREA)
    B = np.zeros_like(top)
    MB = np.zeros(top.shape, bool)
    h = min(bh, top.shape[0])
    w = min(bw, top.shape[1])
    B[:h, :w] = botr[:h, :w]
    MB[:h, :w] = botr[:h, :w] > 0
    # work pitch
    f = a.work_mm / mm
    ws = (int(top.shape[1] / f), int(top.shape[0] / f))
    box = max(3, int(round(0.5 * 1000 / a.work_mm)) | 1)
    Ts = cv2.resize(top, ws, interpolation=cv2.INTER_AREA)
    Tm = cv2.resize(obs.astype(np.uint8) * 255, ws, interpolation=cv2.INTER_AREA) > 200
    Bs = cv2.resize(B, ws, interpolation=cv2.INTER_AREA)
    Bm = cv2.resize(MB.astype(np.uint8) * 255, ws, interpolation=cv2.INTER_AREA) > 200
    A_ = local_contrast(Ts, Tm, box)
    B_ = local_contrast(Bs, Bm, box)
    half = int(round(a.search * 1000 / a.work_mm))
    print("work grid", ws, "box", box, "search +-", half, "cells =", round(half * a.work_mm), "mm", flush=True)

    def run(sl, label):
        dx, dy, c, tab = ncc_peak(A_[sl], Tm[sl], B_[sl], Bm[sl], half, 1)
        z = tab[half, half] if np.isfinite(tab[half, half]) else float("nan")
        r = {"shift_px_work": [dx, dy],
             "shift_mm": [round(dx * a.work_mm, 1), round(dy * a.work_mm, 1)],
             "shift_magnitude_mm": round(float(np.hypot(dx, dy) * a.work_mm), 1),
             "ncc_peak": round(c, 4), "ncc_at_zero": round(float(z), 4) if np.isfinite(z) else None,
             "overlap_cells": int((Tm[sl] & Bm[sl]).sum())}
        print("%-8s peak ncc %.3f at %+5.0f, %+5.0f mm   ncc at zero %.3f   overlap %d"
              % (label, c, r["shift_mm"][0], r["shift_mm"][1], z if np.isfinite(z) else float("nan"),
                 r["overlap_cells"]), flush=True)
        return r

    whole = run((slice(None), slice(None)), "whole")
    # per bay
    hu = hu0 + (np.arange(ws[0]) + 0.5) * a.work_mm / 1000
    hv = hv0 + (np.arange(ws[1]) + 0.5) * a.work_mm / 1000
    bi = np.floor((hu - (G.HU0 - G.PU / 2)) / G.PU).astype(int) + 1
    bj = np.floor((hv - (G.HV0 - G.PV / 2)) / G.PV).astype(int) + 1
    bays = {}
    for i in sorted(set(bi.tolist())):
        cols = np.nonzero(bi == i)[0]
        for j in sorted(set(bj.tolist())):
            rows = np.nonzero(bj == j)[0]
            sl = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
            if (Tm[sl] & Bm[sl]).sum() < 8000:
                continue
            bays["%d,%d" % (i, j)] = run(sl, "bay %d,%d" % (i, j))
    out = {"topside_dir": d, "bottom": a.bottom, "work_mm": a.work_mm,
           "search_half_mm": round(half * a.work_mm),
           "method": "masked NCC of the polarity-free local contrast of both orthos on the shared huv grid",
           "whole_plate": whole, "per_bay": bays}
    p = a.out or os.path.join(d, "crossreg-trackB.json")
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
