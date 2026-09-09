"""How well do two traverses agree where they overlap on the plate?

The four walk traverses and the stills are one COLMAP reconstruction, so a disagreement between them
is not a frame error; it is what the surface model and the pose noise leave behind, and it is what a
seam in the mosaic actually looks like. Measure it, do not assume it: pick windows the mosaic fills
from two different traverses, re-render each window from ONE traverse at a time, and phase-correlate
the two images over the pixels both of them observed. The shift is the seam misalignment.

python topside2_seamcheck.py <render dir> --sim <chain.json> [--corr <corr.json>] [--win 512] [--n 6]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import depth_buffers, residual_field
from trackA_render3 import make_corr
from topside2_render import load_cameras, ImageCache, render_tile


def traverse_of(name):
    return "stills" if name.startswith("v") else name.split("_")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--sim", required=True)
    ap.add_argument("--corr", default=None)
    ap.add_argument("--win", type=int, default=512)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = a.dir
    args = json.load(open(os.path.join(d, "render-args.json")))
    names = args["names"]
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    cam = cv2.imread(os.path.join(d, "topside-cam.png"), cv2.IMREAD_UNCHANGED)
    tr_of_idx = np.array([traverse_of(n) for n in names] + ["none"])
    idx = np.minimum(cam.astype(np.int32), len(names))
    trav = tr_of_idx[idx]
    obs = cam != 65535
    W_, S = args["W"], a.win
    # windows the mosaic fills from two traverses in real proportion
    cand = []
    for y0 in range(0, args["H"] - S + 1, S):
        for x0 in range(0, W_ - S + 1, S):
            o = obs[y0:y0 + S, x0:x0 + S]
            if o.mean() < 0.5:
                continue
            t = trav[y0:y0 + S, x0:x0 + S][o]
            u, c = np.unique(t, return_counts=True)
            order = np.argsort(-c)
            if len(u) < 2 or c[order[1]] < 0.25 * c.sum():
                continue
            cand.append((float(c[order[1]]) / c.sum(), x0, y0, str(u[order[0]]), str(u[order[1]])))
    cand.sort(reverse=True)
    print("candidate windows", len(cand))
    if not cand:
        return
    # everything the renderer needs, built once
    sim = G.load_sim(a.sim)
    cams_all = load_cameras(sim, {"w1", "w2", "w4", "w5"})
    cams = {n: cams_all[n] for n in names}
    dbufs = depth_buffers(cams, sim, os.path.join(d, "depth-buffers.npz"))
    Fs, cellF = residual_field(sim)
    corr = make_corr(a.corr) if a.corr else None
    get_img = ImageCache(cap=40)
    results = []
    for frac, x0, y0, ta, tb in cand[:a.n]:
        imgs, masks = {}, {}
        for t in (ta, tb):
            sub = [n for n in names if traverse_of(n) == t]
            if not sub:
                continue
            fac = np.ones(len(sub), np.float32)
            rgb, c_, g_, o_, _, _, _ = render_tile(x0, y0, S, S, mm, hu0, hv0, cams, sub, fac,
                                                   dbufs, get_img, Fs, cellF, args["slab"],
                                                   args["gsd_max"], corr)
            imgs[t] = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
            masks[t] = o_
        if len(imgs) < 2:
            continue
        both = masks[ta] & masks[tb]
        if both.mean() < 0.15:
            continue
        # phase correlation wants the same content either side: fill the unseen pixels of each image
        # with that image's own mean so a coverage difference does not read as a shift
        A, B = imgs[ta].copy(), imgs[tb].copy()
        A[~both] = A[both].mean()
        B[~both] = B[both].mean()
        win = cv2.createHanningWindow((S, S), cv2.CV_32F)
        (dx, dy), resp = cv2.phaseCorrelate(A, B, win)
        ncc = float(np.corrcoef(A[both], B[both])[0, 1])
        r = {"px": [x0, y0], "traverses": [ta, tb], "overlap_frac": round(float(both.mean()), 4),
             "shift_px": [round(dx, 2), round(dy, 2)],
             "shift_mm": [round(dx * mm, 1), round(dy * mm, 1)],
             "shift_magnitude_mm": round(float(np.hypot(dx, dy) * mm), 1),
             "phase_response": round(float(resp), 4), "grey_correlation": round(ncc, 4),
             "huv": [round(hu0 + x0 * mm / 1000, 2), round(hv0 + y0 * mm / 1000, 2)]}
        results.append(r)
        print("window %5d,%4d %-6s vs %-6s overlap %.2f  shift %6.1f, %6.1f mm  (|d| %5.1f mm)"
              " response %.3f  grey corr %.3f"
              % (x0, y0, ta, tb, both.mean(), r["shift_mm"][0], r["shift_mm"][1],
                 r["shift_magnitude_mm"], resp, ncc), flush=True)
    if results:
        mag = [r["shift_magnitude_mm"] for r in results]
        summary = {"windows": len(results), "window_px": S,
                   "shift_mm_median": round(float(np.median(mag)), 1),
                   "shift_mm_max": round(float(np.max(mag)), 1),
                   "note": "phase correlation of the same window rendered from one traverse at a time,"
                           " over the pixels both traverses observed"}
        print(json.dumps(summary))
        out = a.out or os.path.join(d, "seam-check.json")
        json.dump({"summary": summary, "windows": results}, open(out, "w"), indent=1)
        print("wrote", out)


if __name__ == "__main__":
    main()
