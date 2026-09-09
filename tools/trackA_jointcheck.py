"""Track A step 2e: in-plane residual of the lattice measured on the ORTHO from the panel joint lines.

The anti-diagonal joints (the diamond joining the bay-edge midpoints) are thin dark lines ON the plate
surface (no parallax, unlike the rib tops), so their position in the ortho is a direct test of the
chain + surface model. For every anti-diagonal segment the darkness profile perpendicular to the
expected line is sampled (+-40 px = +-160 mm at 4 mm/px) at points where the ortho is observed with
GSD < gsd_max; the dark line's offset is taken per point, the segment offset is the median. Per bay the
segment offsets (two diagonal orientations) are solved for a residual vector (dhu, dhv).

python trackA_jointcheck.py <render dir> [--gsd-max 8] [--out json]
"""
import sys, os, json, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_assemble import load_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--gsd-max", type=float, default=8.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--half", type=int, default=40)
    a = ap.parse_args()
    args, rgb, cam, gsd, obs, corr = load_all(a.dir)
    mm = args["mm"]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    dark = 255 - gray
    good = obs & (gsd > 0) & (gsd < a.gsd_max)
    H, W = gray.shape

    def to_px(hu, hv):
        return (hu - G.PLATE_HU[0]) * 1000 / mm, (hv - G.PLATE_HV[0]) * 1000 / mm

    shifts = np.arange(-a.half, a.half + 1)
    segs = []
    for i in range(-1, 6):
        for j in range(-1, 1):
            cu, cv_ = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            aa, bb = G.PU / 2, G.PV / 2
            bi, bj = i + 1, j + 1
            for (p, q) in (((cu + aa, cv_), (cu, cv_ + bb)), ((cu, cv_ + bb), (cu - aa, cv_)), ((cu - aa, cv_), (cu, cv_ - bb)), ((cu, cv_ - bb), (cu + aa, cv_))):
                segs.append((bi, bj, p, q))
    results = []
    for bi, bj, p, q in segs:
        x0, y0 = to_px(*p)
        x1, y1 = to_px(*q)
        L = np.hypot(x1 - x0, y1 - y0)
        t = np.linspace(0.06, 0.94, int(L / 4))  # skip the ends (rib crossings)
        xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        offs = []
        for x, y in zip(xs, ys):
            xi, yi = int(round(x)), int(round(y))
            if not (a.half < xi < W - a.half and a.half < yi < H - a.half):
                continue
            if not good[yi, xi]:
                continue
            us = (x + shifts * nx).astype(np.float32).reshape(1, -1)
            vs = (y + shifts * ny).astype(np.float32).reshape(1, -1)
            if not good[np.clip(vs.astype(int), 0, H - 1), np.clip(us.astype(int), 0, W - 1)].all():
                continue
            prof = cv2.remap(dark, us, vs, cv2.INTER_LINEAR).ravel()
            base = np.median(prof)
            pk = prof.max()
            if pk - base < 45:
                continue
            k = int(np.argmax(prof))
            # sub-pixel: centroid over the peak's neighbourhood above half contrast
            m = prof > base + 0.5 * (pk - base)
            # keep only the connected run containing k
            lo, hi = k, k
            while lo > 0 and m[lo - 1]:
                lo -= 1
            while hi < len(m) - 1 and m[hi + 1]:
                hi += 1
            if hi - lo > 12:  # too wide to be a joint (a slab edge / shadow)
                continue
            w = prof[lo:hi + 1] - base
            offs.append(float((shifts[lo:hi + 1] * w).sum() / w.sum()))
        if len(offs) >= 8:
            offs = np.array(offs)
            results.append({"bay": [bi, bj], "n": len(offs), "off_px": float(np.median(offs)), "iqr_px": float(np.percentile(offs, 75) - np.percentile(offs, 25)),
                            "normal": [float(nx), float(ny)], "from": list(p), "to": list(q)})
    per_bay = {}
    for bi in range(0, 7):
        for bj in range(0, 2):
            rs = [r for r in results if r["bay"] == [bi, bj]]
            if len(rs) < 2:
                continue
            A = np.array([r["normal"] for r in rs])
            b = np.array([r["off_px"] for r in rs])
            sol, *_ = np.linalg.lstsq(A, b, rcond=None)
            fit_res = b - A @ sol
            per_bay[f"{bi},{bj}"] = {"segments": len(rs), "dhu_mm": float(sol[0] * mm), "dhv_mm": float(sol[1] * mm),
                                    "seg_offsets_px": [round(r["off_px"], 1) for r in rs], "fit_resid_px_rms": float(np.sqrt(np.mean(fit_res ** 2)))}
    allo = np.array([r["off_px"] for r in results])
    summary = {"segments": len(results), "abs_off_px_p50": float(np.median(np.abs(allo))) if len(allo) else None,
               "abs_off_mm_p50": float(np.median(np.abs(allo)) * mm) if len(allo) else None,
               "abs_off_mm_p90": float(np.percentile(np.abs(allo), 90) * mm) if len(allo) else None, "mm_per_px": mm}
    print("joint check:", json.dumps(summary))
    for k, v in sorted(per_bay.items()):
        print(f"  bay {k}: {v['segments']} segs  dhu {v['dhu_mm']:+.0f} mm  dhv {v['dhv_mm']:+.0f} mm  offsets px {v['seg_offsets_px']}  fit rms {v['fit_resid_px_rms']:.1f} px")
    out = a.out or os.path.join(a.dir, "joint-check.json")
    json.dump({"summary": summary, "per_bay": per_bay, "segments": results,
               "note": "off_px = perpendicular offset of the dark joint line from the lattice anti-diagonal in the ortho (px of %g mm); dhu/dhv = per-bay least-squares translation of the joints relative to the lattice" % mm},
              open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
