"""Registration proof on the delivered ortho: where does the visible steel sit against the lattice?

Which members can be measured here, and why only these. The hips, the cross members and the crest
ridges are CUT OUT of the mosaic by the occluder test, and that cut is drawn from the lattice, so the
hole is the model's opinion and proves nothing. The DIAMOND members through the edge midpoints are
not in the occluder set, they lie on the plate surface (no parallax to argue about), and they read as
a dark band across every facet. They are the measurable member class, and they carry the same
registration as everything else on the plate.

The search is deliberately wide, +-0.8 m, several times any plausible error. trackA_jointcheck2.py
searches +-160 mm, which cannot tell a small offset from a whole-member slip; a wide search can, and
it is what settles whether the lattice is out by tens of millimetres or by most of a metre.

Per segment the ortho grey is averaged along the member for each perpendicular offset and the
darkest offset wins; per bay the segment offsets are solved for (dhu, dhv) against their normals; and
one similarity in joint-corr's form is fitted over all of them so a correction can be re-rendered.

python topside2_diamondfit.py <render dir> [--tag before] [--search 1.2] [--corr <corr.json>]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

TRIM = 0.45          # trim each end: the diamond meets the crest and the hip at its corners
ALONG = 0.02         # along-segment sample pitch (m)
STEP = 0.004         # perpendicular step (m): one ortho pixel
MIN_COVER = 0.30     # a segment is only evidence when this much of it is observed at the offset
MEMBER_W = 0.16      # the painted diamond member is about 140 mm wide (AGENTS: "the diamond ~140 mm")


def diamond_segments():
    """the four sides of each bay's edge-midpoint diamond, in huv, with the bay and the normal."""
    a, b = G.PU / 2, G.PV / 2
    out = []
    for i in range(-2, 7):
        cu = G.HU0 + i * G.PU
        for j in (-1, 0):
            cvv = G.HV0 + j * G.PV
            corners = [(cu + a, cvv), (cu, cvv + b), (cu - a, cvv), (cu, cvv - b)]
            for k in range(4):
                p0 = np.array(corners[k], float)
                p1 = np.array(corners[(k + 1) % 4], float)
                d = p1 - p0
                L = float(np.linalg.norm(d))
                d /= L
                n = np.array([-d[1], d[0]])
                s = np.arange(TRIM, L - TRIM + 1e-9, ALONG)
                if len(s) < 10:
                    continue
                pts = p0[None, :] + s[:, None] * d[None, :]
                mid = pts.mean(0)
                bi = int(np.floor((mid[0] - (G.HU0 - G.PU / 2)) / G.PU)) + 1
                bj = int(np.floor((mid[1] - (G.HV0 - G.PV / 2)) / G.PV)) + 1
                out.append({"bay": [bi, bj], "side": k, "pts": pts, "normal": n, "mid": mid})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--tag", default="before")
    ap.add_argument("--search", type=float, default=0.8)
    ap.add_argument("--corr", default=None, help="correction to apply to the lattice before measuring")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = a.dir
    args = json.load(open(os.path.join(d, "render-args.json")))
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    grey = cv2.imread(os.path.join(d, "topside-ortho.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    obs = cv2.imread(os.path.join(d, "topside-observed.png"), cv2.IMREAD_GRAYSCALE) > 127
    H, W = grey.shape
    segs = diamond_segments()
    if a.corr:
        from trackA_render3 import make_corr
        corr = make_corr(a.corr)
        for s in segs:
            hu, hv = corr(s["pts"][:, 0], s["pts"][:, 1])
            s["pts"] = np.stack([hu, hv], 1)
    offsets = np.arange(-a.search, a.search + 1e-9, STEP)
    rows = []
    for s in segs:
        hu = s["pts"][:, 0][:, None] + offsets[None, :] * s["normal"][0]
        hv = s["pts"][:, 1][:, None] + offsets[None, :] * s["normal"][1]
        px = ((hu - hu0) * 1000 / mm).astype(np.int32)
        py = ((hv - hv0) * 1000 / mm).astype(np.int32)
        inb = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        pxc, pyc = np.clip(px, 0, W - 1), np.clip(py, 0, H - 1)
        m = inb & obs[pyc, pxc]
        cnt = m.sum(0)
        cover = cnt / len(s["pts"])
        vals = np.where(m, grey[pyc, pxc], np.nan)
        with np.errstate(invalid="ignore"):
            prof = np.nanmean(np.where(m, vals, np.nan), axis=0)
        ok = cover >= MIN_COVER
        if ok.sum() < 20:
            continue
        p = np.where(ok, prof, np.nan)
        # matched filter: the member is a NARROW dark band, roughly MEMBER_W wide, on a lighter
        # surround. Plain "darkest offset" loses to any big dark slab or to the edge of the
        # occluder cut, which is why the first pass latched onto features a metre away.
        w = max(1, int(round(MEMBER_W / 2 / STEP)))
        ker = np.zeros(6 * w + 1)
        ker[3 * w - w:3 * w + w + 1] = -1.0 / (2 * w + 1)          # the band
        ker[:w] = 0.5 / w                                          # the flanks either side
        ker[-w:] = 0.5 / w
        pz = np.where(np.isfinite(p), p, np.nanmedian(p))
        resp = np.convolve(pz, ker[::-1], mode="same")
        resp = np.where(ok, resp, -np.inf)
        i = int(np.argmax(resp))
        if i <= 3 * w or i >= len(offsets) - 3 * w - 1:
            continue
        contrast = float(resp[i])
        if contrast < 6.0:
            continue                    # no member-like dark band: not evidence
        p = -resp                       # parabola on the response, so the vertex is its peak
        y0_, y1_, y2_ = p[i - 1], p[i], p[i + 1]
        den = y0_ - 2 * y1_ + y2_
        sub = 0.5 * (y0_ - y2_) / den if den != 0 else 0.0
        t = offsets[i] + float(np.clip(sub, -1, 1)) * STEP
        if not np.isfinite(t):
            continue                    # a flat response gives no vertex: not evidence
        rows.append({"bay": s["bay"], "side": s["side"], "mid": [round(float(v), 3) for v in s["mid"]],
                     "normal": [round(float(s["normal"][0]), 4), round(float(s["normal"][1]), 4)],
                     "offset_mm": round(float(t) * 1000, 1), "contrast": round(contrast, 1),
                     "cover": round(float(cover[i]), 3)})
    print("diamond segments measured", len(rows), flush=True)
    if not rows:
        return
    off = np.array([r["offset_mm"] for r in rows])
    summary = {"segments": len(rows),
               "abs_offset_mm_p50": round(float(np.percentile(np.abs(off), 50)), 1),
               "abs_offset_mm_p90": round(float(np.percentile(np.abs(off), 90)), 1),
               "signed_median_mm": round(float(np.median(off)), 1),
               "within_100mm_frac": round(float((np.abs(off) < 100).mean()), 3),
               "within_250mm_frac": round(float((np.abs(off) < 250).mean()), 3),
               "search_half_mm": round(a.search * 1000)}
    bays = {}
    for bi in range(0, 9):
        for bj in (0, 1):
            sel = [r for r in rows if r["bay"] == [bi, bj]]
            if len(sel) < 3:
                continue
            A = np.array([r["normal"] for r in sel])
            y = np.array([r["offset_mm"] for r in sel])
            sol, *_ = np.linalg.lstsq(A, y, rcond=None)
            res = A @ sol - y
            bays["%d,%d" % (bi, bj)] = {"segments": len(sel), "dhu_mm": round(float(sol[0]), 1),
                                        "dhv_mm": round(float(sol[1]), 1),
                                        "shift_mm": round(float(np.hypot(*sol)), 1),
                                        "resid_rms_mm": round(float(np.sqrt((res ** 2).mean())), 1),
                                        "offsets_mm": [r["offset_mm"] for r in sel]}
    cu = (G.PLATE_HU[0] + G.PLATE_HU[1]) / 2
    cvc = (G.PLATE_HV[0] + G.PLATE_HV[1]) / 2
    mids = np.array([r["mid"] for r in rows])
    nrm = np.array([r["normal"] for r in rows])
    y = off / 1000.0
    du, dv = mids[:, 0] - cu, mids[:, 1] - cvc
    A = np.stack([nrm[:, 0] * du + nrm[:, 1] * dv, -nrm[:, 0] * dv + nrm[:, 1] * du,
                  nrm[:, 0], nrm[:, 1]], 1)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = A @ sol - y
    sim_fit = {"s": float(1 + sol[0]), "theta_deg": float(np.degrees(sol[1])),
               "tu": float(sol[2]), "tv": float(sol[3]), "about": [cu, cvc], "segments": len(rows),
               "resid_mm_rms_before": round(float(np.sqrt((y ** 2).mean()) * 1000), 1),
               "resid_mm_rms_after": round(float(np.sqrt((res ** 2).mean()) * 1000), 1),
               "note": "hu' = cu + s*(cos th*(hu-cu) - sin th*(hv-cv)) + tu, likewise hv'; "
                       "pass to the renderer as --corr"}
    out = {"tag": a.tag, "dir": d, "corr_applied": a.corr, "summary": summary, "per_bay": bays,
           "similarity": sim_fit, "segments_detail": rows,
           "member": "the edge-midpoint diamond, the one member class the occluder does not cut out",
           "sign": "offset_mm > 0 = the observed member lies towards +normal of the lattice line"}
    p = a.out or os.path.join(d, "diamond-fit-%s.json" % a.tag)
    json.dump(out, open(p, "w"), indent=1)
    print(json.dumps({"summary": summary, "similarity": sim_fit}, indent=1))
    for k, v in sorted(bays.items(), key=lambda kv: (int(kv[0].split(",")[0]), kv[0])):
        print(" bay %-4s %2d segs  dhu %+7.1f  dhv %+7.1f  |d| %6.1f mm  rms %5.1f mm  offsets %s"
              % (k, v["segments"], v["dhu_mm"], v["dhv_mm"], v["shift_mm"], v["resid_rms_mm"],
                 v["offsets_mm"]))
    print("wrote", p)


if __name__ == "__main__":
    main()
