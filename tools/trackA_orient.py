"""Track A step 2f: decide the discrete lattice symmetry (180 deg flip, whole-bay shift) by correlating the
TOPSIDE pane pattern (this track's ortho, glass = dark on white) with the UNDERSIDE pattern (track B's
bottom-ortho.png from the bake atlas, glass = bright on dark). Both are in the same huv frame, so the
right assignment gives a strong NEGATIVE correlation of grey levels; the lattice-consistent impostors
(other bays, flipped) should not.

Candidates: hu' = (flip ? 2*HU_C - hu : hu) + k*PU, hv' = flip ? 2*HV_C - hv : hv.

python trackA_orient.py <render dir> [--cell-mm 20] [--gsd-max 12]
"""
import sys, os, json, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_assemble import load_all

BOTTOM = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-ortho.png"
BOTTOM_META = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-meta.json"
HU_C = (G.PLATE_HU[0] + G.PLATE_HU[1]) / 2
HV_C = (G.PLATE_HV[0] + G.PLATE_HV[1]) / 2


def downsample_to_grid(img, valid, mm_in, cell_mm, hu0, hv0):
    """area-average img (float) over cells of cell_mm, weighted by valid; returns grid, weight."""
    f = int(round(cell_mm / mm_in))
    H, W = img.shape
    Hc, Wc = H // f, W // f
    a = img[:Hc * f, :Wc * f].reshape(Hc, f, Wc, f)
    v = valid[:Hc * f, :Wc * f].reshape(Hc, f, Wc, f).astype(np.float32)
    num = (a * v).sum(axis=(1, 3))
    den = v.sum(axis=(1, 3))
    return np.where(den > 0, num / np.maximum(den, 1), np.nan), den / (f * f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--cell-mm", type=float, default=20.0)
    ap.add_argument("--gsd-max", type=float, default=12.0)
    a = ap.parse_args()
    args, rgb, cam, gsd, obs, corr = load_all(a.dir)
    mm = args["mm"]
    top_gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    top_valid = obs & (gsd > 0) & (gsd < a.gsd_max)
    # exclude the rib bands (their smeared tops carry no pane information)
    T, Tw = downsample_to_grid(top_gray, top_valid, mm, a.cell_mm, G.PLATE_HU[0], G.PLATE_HV[0])
    bm = json.load(open(BOTTOM_META))
    bot = cv2.imread(BOTTOM, cv2.IMREAD_COLOR)
    bot_gray = cv2.cvtColor(bot, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bot_valid = bot_gray > 8
    assert abs(bm["hu0"] - G.PLATE_HU[0]) < 1e-6 and abs(bm["hv0"] - G.PLATE_HV[0]) < 1e-6
    B, Bw = downsample_to_grid(bot_gray, bot_valid, bm["mm_per_px"], a.cell_mm, bm["hu0"], bm["hv0"])
    print("top grid", T.shape, "valid cells", int(np.isfinite(T).sum()), " bottom grid", B.shape, "valid", int(np.isfinite(B).sum()))
    # high-pass both (remove illumination / smear gradients): subtract a 0.6 m box mean
    k = int(round(600 / a.cell_mm)) | 1

    def hp(X):
        Xz = np.where(np.isfinite(X), X, 0).astype(np.float32)
        Wm = np.isfinite(X).astype(np.float32)
        num = cv2.blur(Xz, (k, k))
        den = cv2.blur(Wm, (k, k))
        loc = np.where(den > 0.3, num / np.maximum(den, 1e-6), np.nan)
        return X - loc
    Th, Bh = hp(T), hp(B)
    Hc, Wc = Th.shape
    cell = a.cell_mm / 1000
    # cell centres in huv
    hu = G.PLATE_HU[0] + (np.arange(Wc) + 0.5) * cell
    hv = G.PLATE_HV[0] + (np.arange(Hc) + 0.5) * cell
    HU, HV = np.meshgrid(hu, hv)
    tv = np.isfinite(Th)
    rows = []
    for flip in (0, 1):
        for kshift in range(-6, 7):
            hu2 = (2 * HU_C - HU if flip else HU) + kshift * G.PU
            hv2 = (2 * HV_C - HV) if flip else HV
            ix = np.floor((hu2 - G.PLATE_HU[0]) / cell).astype(int)
            iy = np.floor((hv2 - G.PLATE_HV[0]) / cell).astype(int)
            inside = (ix >= 0) & (ix < B.shape[1]) & (iy >= 0) & (iy < B.shape[0]) & tv
            if inside.sum() < 2000:
                continue
            b = Bh[iy[inside], ix[inside]]
            t = Th[inside]
            m = np.isfinite(b) & np.isfinite(t)
            if m.sum() < 2000:
                continue
            b, t = b[m], t[m]
            ncc = float(np.corrcoef(t, b)[0, 1])
            # per-bay breakdown of the candidate
            bi, bj = G.bay_index(hu2[inside][m], hv2[inside][m])
            per = {}
            for i in np.unique(bi):
                for j in np.unique(bj):
                    s = (bi == i) & (bj == j)
                    if s.sum() > 800:
                        per[f"{int(i)},{int(j)}"] = (round(float(np.corrcoef(t[s], b[s])[0, 1]), 3), int(s.sum()))
            rows.append({"flip": flip, "k": kshift, "cells": int(m.sum()), "ncc": ncc, "per_bay": per})
    rows.sort(key=lambda r: r["ncc"])
    print("candidates (glass is dark on top, bright below: the right one should be the most NEGATIVE):")
    for r in rows:
        print(f"  flip {r['flip']} shift {r['k']:+d} bays: ncc {r['ncc']:+.4f} over {r['cells']} cells  per-bay {r['per_bay']}")
    out = os.path.join(a.dir, "orient-check.json")
    json.dump({"cell_mm": a.cell_mm, "gsd_max": a.gsd_max, "candidates": rows,
               "note": "ncc between high-passed topside grey (this ortho) and underside grey (track B atlas ortho) after mapping the topside through the candidate lattice symmetry; correct = most negative"},
              open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
