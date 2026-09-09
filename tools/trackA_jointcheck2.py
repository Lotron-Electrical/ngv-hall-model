"""Track A (resume, v2): in-plane residual of the lattice measured on the ortho from the anti-diagonal
panel joint lines (thin dark lines ON the plate surface, so no parallax), extended to the 8th bay and
to the ortho frame of trackA_render2.py. Per bay the segment offsets are solved for (dhu, dhv), and a
global 2D similarity (scale, rotation, shift) is fitted to all segment offsets and written as a
--corr json for trackA_render2.py.

python trackA_jointcheck2.py <render dir> [--gsd-max 10] [--half 40] [--out json] [--corr-out json]
"""
import sys, os, json, argparse
import numpy as np
import cv2
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_assemble2 import load_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--gsd-max", type=float, default=10.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--corr-out", default=None)
    ap.add_argument("--half", type=int, default=40)
    ap.add_argument("--min-contrast", type=float, default=45.0)
    a = ap.parse_args()
    args, rgb, cam, gsd, obs, _ = load_all(a.dir)
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    del rgb
    dark = 255 - gray
    good = obs & (gsd > 0) & (gsd < a.gsd_max)
    H, W = gray.shape

    def to_px(hu, hv):
        return (hu - hu0) * 1000 / mm, (hv - hv0) * 1000 / mm

    shifts = np.arange(-a.half, a.half + 1)
    segs = []
    for i in range(-1, 7):
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
        t = np.linspace(0.06, 0.94, int(L / 4))
        xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        offs, poss = [], []
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
            if pk - base < a.min_contrast:
                continue
            k = int(np.argmax(prof))
            m = prof > base + 0.5 * (pk - base)
            lo, hi = k, k
            while lo > 0 and m[lo - 1]:
                lo -= 1
            while hi < len(m) - 1 and m[hi + 1]:
                hi += 1
            if hi - lo > 12:
                continue
            w = prof[lo:hi + 1] - base
            offs.append(float((shifts[lo:hi + 1] * w).sum() / w.sum()))
            poss.append((x, y))
        if len(offs) >= 8:
            offs = np.array(offs)
            med = float(np.median(offs))
            inl = np.abs(offs - med) < 8
            results.append({"bay": [bi, bj], "n": int(inl.sum()), "off_px": float(np.median(offs[inl])),
                            "iqr_px": float(np.percentile(offs, 75) - np.percentile(offs, 25)),
                            "normal": [float(nx), float(ny)], "from": list(p), "to": list(q),
                            "mid_huv": [float((p[0] + q[0]) / 2), float((p[1] + q[1]) / 2)]})
    per_bay = {}
    for bi in range(0, 8):
        for bj in range(0, 2):
            rs = [r for r in results if r["bay"] == [bi, bj]]
            if len(rs) < 2:
                continue
            A = np.array([r["normal"] for r in rs])
            b = np.array([r["off_px"] for r in rs])
            if np.linalg.matrix_rank(A) < 2:
                continue
            sol, *_ = np.linalg.lstsq(A, b, rcond=None)
            fit_res = b - A @ sol
            per_bay[f"{bi},{bj}"] = {"segments": len(rs), "dhu_mm": float(sol[0] * mm), "dhv_mm": float(sol[1] * mm),
                                    "seg_offsets_px": [round(r["off_px"], 1) for r in rs], "seg_n": [r["n"] for r in rs],
                                    "fit_resid_px_rms": float(np.sqrt(np.mean(fit_res ** 2)))}
    allo = np.array([r["off_px"] for r in results])
    summary = {"segments": len(results), "abs_off_px_p50": float(np.median(np.abs(allo))) if len(allo) else None,
               "abs_off_mm_p50": float(np.median(np.abs(allo)) * mm) if len(allo) else None,
               "abs_off_mm_p90": float(np.percentile(np.abs(allo), 90) * mm) if len(allo) else None, "mm_per_px": mm,
               "sign": "off_px > 0 = the observed joint lies towards +normal of the segment (normal = (-dy, dx) of from->to in px)"}
    print("joint check:", json.dumps(summary))
    for k, v in sorted(per_bay.items()):
        print(f"  bay {k}: {v['segments']} segs  dhu {v['dhu_mm']:+.0f} mm  dhv {v['dhv_mm']:+.0f} mm  offsets px {v['seg_offsets_px']} n {v['seg_n']}  fit rms {v['fit_resid_px_rms']:.1f} px")
    # global 2D similarity: observed joint position = corr(lattice position); corr(h) = c + s R (h - c) + t
    corr = None
    if len(results) >= 4:
        mids = np.array([r["mid_huv"] for r in results])
        nrm = np.array([r["normal"] for r in results])
        off_m = np.array([r["off_px"] for r in results]) * mm / 1000.0
        cu, cv_ = float(mids[:, 0].mean()), float(mids[:, 1].mean())

        def resid(p):
            s, th, tu, tv = p
            c, sn = np.cos(th), np.sin(th)
            du, dv = mids[:, 0] - cu, mids[:, 1] - cv_
            hu2 = cu + s * (c * du - sn * dv) + tu
            hv2 = cv_ + s * (sn * du + c * dv) + tv
            # predicted perpendicular offset (m) of the moved line at the segment midpoint
            pred = (hu2 - mids[:, 0]) * nrm[:, 0] + (hv2 - mids[:, 1]) * nrm[:, 1]
            return pred - off_m
        fit = least_squares(resid, [1.0, 0.0, 0.0, 0.0], loss="soft_l1", f_scale=0.02)
        s, th, tu, tv = fit.x
        r = resid(fit.x)
        # translation-only fit for comparison
        fit_t = least_squares(lambda p: resid([1.0, 0.0, p[0], p[1]]), [0.0, 0.0], loss="soft_l1", f_scale=0.02)
        rt = resid([1.0, 0.0, fit_t.x[0], fit_t.x[1]])
        corr = {"s": float(s), "theta_deg": float(np.degrees(th)), "tu": float(tu), "tv": float(tv), "about": [cu, cv_],
                "segments": len(results), "resid_mm_rms_before": float(np.sqrt(np.mean(off_m ** 2)) * 1000),
                "resid_mm_rms_after_similarity": float(np.sqrt(np.mean(r ** 2)) * 1000),
                "translation_only": {"tu": float(fit_t.x[0]), "tv": float(fit_t.x[1]), "resid_mm_rms_after": float(np.sqrt(np.mean(rt ** 2)) * 1000)},
                "note": "observed joint position = corr(lattice position): hu' = cu + s*(cos th*(hu-cu) - sin th*(hv-cv)) + tu, hv' = cv + s*(sin th*(hu-cu) + cos th*(hv-cv)) + tv. Pass to trackA_render2.py --corr so the render samples the surface at the observed position for each lattice pixel."}
        print("similarity fit:", json.dumps({k: corr[k] for k in ("s", "theta_deg", "tu", "tv", "resid_mm_rms_before", "resid_mm_rms_after_similarity", "translation_only")}))
        if a.corr_out:
            json.dump(corr, open(a.corr_out, "w"), indent=1)
            print("wrote", a.corr_out)
    out = a.out or os.path.join(a.dir, "joint-check.json")
    json.dump({"summary": summary, "per_bay": per_bay, "similarity": corr, "segments": results}, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
