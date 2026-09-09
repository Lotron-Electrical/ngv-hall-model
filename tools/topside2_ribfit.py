"""Registration proof: find every steel member in the source frames and say, per bay and per member
class, how far it sits from where the lattice puts it.

Why not measure this on the ortho. The hips, the cross members and the crest ridges are CUT OUT of
the mosaic by the occluder test, and that cut is drawn from the lattice, so the hole in the image is
the model's opinion, not evidence. The members have to be found in the frames themselves.

Why not measure it on the dense cloud either. Away from the catwalk the roof-void cloud thins out to
a few per cent of cells and carries no rib ridge at all (topside2_memberfit.py, member-height-*.png):
it can measure the catwalk and a handful of hips near it, nothing more.

So: in the frames, as trackA_ribcheck.py does. A steel member top is SMOOTH where the glass field
either side of it is busy, so local texture drops over the member. For each member segment the
segment is slid sideways in the huv plane, offset by offset, projected into the frame at rib-top
height, and the along-segment mean texture is read; the minimum is where the member is.

The trap this adds, and why the answer is a regression and not a median. Sampling at an assumed
rib-top height h_a when the real top is at h_t puts the apparent offset at

    t_measured = t_true + (h_t - h_a) * k,     k = ((C - P) . n_horizontal) / (C_y - P_y)

where k is the frame's own parallax factor for that segment. Every camera walked the same catwalk,
so a segment out in a bay is seen from ONE side by all of them and a wrong height assumption biases
every frame the same way: a median over frames would report that bias as a real in-plane shift. k
does vary between near and far frames, so t is regressed on k per segment: the intercept is the
in-plane offset, the slope is the height error. Segments without enough spread in k are reported but
flagged and left out of the bay solution.

python topside2_ribfit.py --sim <chain.json> --out <dir> [--corr <corr.json>] [--tag before]
                          [--rib-h 0.45] [--max-frames 0]
"""
import sys, os, json, argparse, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from topside2_render import load_cameras, image_path

HALF = 0.60          # perpendicular search half-width (m)
STEP = 0.01          # perpendicular step (m)
TRIM = 0.35          # trim off each end of a segment: members blend where three of them meet
ALONG = 0.10         # along-segment sample pitch (m)
DECK_HV, DECK_KEEP = 7.544, 0.62     # the catwalk hides the mid crest, so skip that band
MAXDIST = 8.0
WIDTH = {"crest": 0.22, "cross": 0.20, "hip": 0.20}   # member widths, for the profile box filter


def texture_image(gray):
    """local standard deviation in a 9x9 window: member tops are smooth, the glass field is not."""
    g = gray.astype(np.float32)
    m = cv2.blur(g, (9, 9))
    m2 = cv2.blur(g * g, (9, 9))
    return np.sqrt(np.maximum(m2 - m * m, 0))


def segments():
    """(seg_id, bay_i, bay_j, class, huv points along the segment, huv unit normal)."""
    a, b = G.PU / 2, G.PV / 2
    out = []
    for i in range(-2, 7):
        cu = G.HU0 + i * G.PU
        for j in (-1, 0):
            cvv = G.HV0 + j * G.PV
            arms = []
            for su, sv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                arms.append(("cross", (cu, cvv), (cu + su * a, cvv + sv * b)))
            for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                arms.append(("hip", (cu, cvv), (cu + su * a, cvv + sv * b)))
            # only the +hu and +hv sides, so a crest shared with the next bay is measured once
            arms.append(("crest", (cu + a, cvv - b), (cu + a, cvv + b)))
            arms.append(("crest", (cu - a, cvv + b), (cu + a, cvv + b)))
            for cls, p0, p1 in arms:
                p0, p1 = np.array(p0, float), np.array(p1, float)
                d = p1 - p0
                L = float(np.linalg.norm(d))
                d /= L
                n = np.array([-d[1], d[0]])
                s = np.arange(TRIM, L - TRIM + 1e-9, ALONG)
                if len(s) < 4:
                    continue
                pts = p0[None, :] + s[:, None] * d[None, :]
                keep = (pts[:, 0] > G.PLATE_HU[0]) & (pts[:, 0] < G.PLATE_HU[1] + G.PU) \
                    & (pts[:, 1] > G.PLATE_HV[0]) & (pts[:, 1] < G.PLATE_HV[1]) \
                    & (np.abs(pts[:, 1] - DECK_HV) > DECK_KEEP)
                pts = pts[keep]
                if len(pts) < 4:
                    continue
                mid = pts.mean(0)
                bi = int(np.floor((mid[0] - (G.HU0 - G.PU / 2)) / G.PU)) + 1
                bj = int(np.floor((mid[1] - (G.HV0 - G.PV / 2)) / G.PV)) + 1
                out.append({"id": len(out), "bay": [bi, bj], "class": cls, "pts": pts, "normal": n,
                            "mid": mid.tolist()})
    return out


def measure(cam, tex, seg, offsets, rib_h):
    """the offset of the texture minimum for this segment in this frame, and the frame's parallax
    factor k. None when the frame does not see the segment well enough to be evidence."""
    pts, n = seg["pts"], seg["normal"]
    hu = pts[:, 0][:, None] + offsets[None, :] * n[0]
    hv = pts[:, 1][:, None] + offsets[None, :] * n[1]
    P = G.surface_xyz(hu.ravel(), hv.ravel(), rib_h)
    u, v, z = cam.project(P)
    Xc = P @ cam.R.T + cam.t
    ok = cam.inside(u, v, z, margin=4) & (Xc[:, 2] > 0.35 * np.linalg.norm(Xc, axis=1))
    ok = ok.reshape(hu.shape)
    good_rows = ok.all(1)
    if good_rows.sum() < 4:
        return None
    P0 = G.surface_xyz(pts[good_rows, 0], pts[good_rows, 1], rib_h)
    d = np.linalg.norm(P0 - cam.center, axis=1)
    if np.median(d) > MAXDIST:
        return None
    us = u.reshape(hu.shape)[good_rows].astype(np.float32)
    vs = v.reshape(hu.shape)[good_rows].astype(np.float32)
    samp = cv2.remap(tex, us, vs, cv2.INTER_LINEAR)
    prof = samp.mean(0)
    dist = float(np.median(d))
    w_px = WIDTH[seg["class"]] / (dist / cam.params[0])          # member width in image px
    # smooth the profile over the member width so a single dark slab cannot win
    k_s = max(1, int(round(w_px / 2 / (STEP * cam.params[0] / dist))))
    ker = np.ones(2 * k_s + 1) / (2 * k_s + 1)
    sm = np.convolve(prof, ker, mode="same")
    inner = slice(k_s, len(sm) - k_s)
    if inner.stop <= inner.start:
        return None
    i = int(np.argmin(sm[inner])) + k_s
    if i <= k_s or i >= len(sm) - k_s - 1:
        return None                                   # the minimum ran into the search edge
    contrast = float(np.median(prof) - sm[i])
    if contrast < 0.25 * np.median(prof):
        return None                                   # no member-like dip: not evidence
    y0_, y1_, y2_ = sm[i - 1], sm[i], sm[i + 1]
    den = y0_ - 2 * y1_ + y2_
    sub = 0.5 * (y0_ - y2_) / den if den != 0 else 0.0
    t = offsets[i] + np.clip(sub, -1, 1) * STEP
    # parallax factor: horizontal travel per metre of height, along the segment normal
    C = cam.center
    dyc = C[1] - P0[:, 1]
    hx = (C[0] - P0[:, 0])
    hz = (C[2] - P0[:, 2])
    nu_x, nu_z = G.huv_to_xz(n[0], n[1])              # the huv normal as a world horizontal vector
    kpar = float(np.median((hx * nu_x + hz * nu_z) / np.maximum(dyc, 0.05)))
    return {"t": float(t), "k": kpar, "dist": dist, "contrast": contrast, "n": int(good_rows.sum())}


def robust_line(k, t):
    """t = a + b k by least squares with one Huber-ish reweighting pass; returns a, b, rms."""
    A = np.stack([np.ones_like(k), k], 1)
    sol, *_ = np.linalg.lstsq(A, t, rcond=None)
    for _ in range(3):
        r = A @ sol - t
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-6
        w = 1.0 / np.maximum(1.0, np.abs(r) / (2 * s))
        Aw = A * w[:, None]
        sol, *_ = np.linalg.lstsq(Aw, t * w, rcond=None)
    r = A @ sol - t
    return float(sol[0]), float(sol[1]), float(np.sqrt((r ** 2).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--corr", default=None, help="lattice correction to apply before measuring (the 'after' pass)")
    ap.add_argument("--tag", default="before")
    ap.add_argument("--rib-h", type=float, default=0.45)
    ap.add_argument("--max-frames", type=int, default=0, help="0 = every frame")
    ap.add_argument("--min-frames", type=int, default=6)
    ap.add_argument("--min-kspread", type=float, default=0.6)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sim = G.load_sim(a.sim)
    cams = load_cameras(sim, {"w1", "w2", "w4", "w5"})
    excl = {"v021", "v022", "v025", "v026", "v027", "v028"}
    names = [n for n in sorted(cams) if n not in excl]
    if a.max_frames:
        names = names[:: max(1, len(names) // a.max_frames)]
    segs = segments()
    if a.corr:
        from trackA_render3 import make_corr
        corr = make_corr(a.corr)
        for s in segs:
            hu, hv = corr(s["pts"][:, 0], s["pts"][:, 1])
            s["pts"] = np.stack([hu, hv], 1)
    print("frames", len(names), "segments", len(segs), flush=True)
    offsets = np.arange(-HALF, HALF + 1e-9, STEP)
    obs = {s["id"]: [] for s in segs}
    t0 = time.time()
    for fi, nm in enumerate(names):
        cam = cams[nm]
        # cheap reject: the frame has to be within reach of the plate at all
        C = cam.center
        cu_, cv_ = G.xz_to_huv(C[0], C[2])
        near = [s for s in segs if abs(s["mid"][0] - cu_) < MAXDIST and abs(s["mid"][1] - cv_) < MAXDIST]
        if not near:
            continue
        gray = cv2.imread(image_path(nm), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        tex = texture_image(gray)
        for s in near:
            r = measure(cam, tex, s, offsets, a.rib_h)
            if r is not None:
                r["frame"] = nm
                obs[s["id"]].append(r)
        if fi % 100 == 0:
            print("  frame %d/%d  %d s" % (fi + 1, len(names), round(time.time() - t0)), flush=True)
    rows = []
    for s in segs:
        o = obs[s["id"]]
        if len(o) < a.min_frames:
            continue
        k = np.array([x["k"] for x in o])
        t = np.array([x["t"] for x in o])
        spread = float(k.max() - k.min())
        aa, bb, rms = robust_line(k, t)
        solid = spread >= a.min_kspread
        rows.append({"bay": s["bay"], "class": s["class"], "mid": [round(v, 3) for v in s["mid"]],
                     "normal": [round(float(s["normal"][0]), 4), round(float(s["normal"][1]), 4)],
                     "frames": len(o), "k_spread": round(spread, 2),
                     "offset_mm": round(aa * 1000, 1), "height_error_mm": round(bb * 1000, 1),
                     "fit_rms_mm": round(rms * 1000, 1),
                     "median_offset_mm": round(float(np.median(t)) * 1000, 1),
                     "usable": bool(solid)})
    good = [r for r in rows if r["usable"]]
    print("segments measured", len(rows), "usable", len(good), flush=True)

    def stats(v):
        v = np.array(v, float)
        return {"n": int(len(v)), "abs_p50_mm": round(float(np.percentile(np.abs(v), 50)), 1),
                "abs_p90_mm": round(float(np.percentile(np.abs(v), 90)), 1),
                "signed_median_mm": round(float(np.median(v)), 1)}
    by_class = {c: stats([r["offset_mm"] for r in good if r["class"] == c])
                for c in ("crest", "cross", "hip") if any(r["class"] == c for r in good)}
    bays = {}
    for bi in range(0, 9):
        for bj in (0, 1):
            sel = [r for r in good if r["bay"] == [bi, bj]]
            if len(sel) < 3:
                continue
            A = np.array([r["normal"] for r in sel])
            y = np.array([r["offset_mm"] for r in sel])
            sol, *_ = np.linalg.lstsq(A, y, rcond=None)
            res = A @ sol - y
            bays["%d,%d" % (bi, bj)] = {
                "segments": len(sel), "dhu_mm": round(float(sol[0]), 1), "dhv_mm": round(float(sol[1]), 1),
                "shift_mm": round(float(np.hypot(*sol)), 1),
                "resid_rms_mm": round(float(np.sqrt((res ** 2).mean())), 1),
                "per_class_abs_p50_mm": {c: round(float(np.median(np.abs([r["offset_mm"] for r in sel if r["class"] == c]))), 1)
                                         for c in ("crest", "cross", "hip") if any(r["class"] == c for r in sel)}}
    # one similarity in joint-corr's form over every usable segment
    sim_fit = None
    if len(good) >= 6:
        cu = (G.PLATE_HU[0] + G.PLATE_HU[1]) / 2
        cvc = (G.PLATE_HV[0] + G.PLATE_HV[1]) / 2
        mids = np.array([r["mid"] for r in good])
        nrm = np.array([r["normal"] for r in good])
        y = np.array([r["offset_mm"] for r in good]) / 1000.0
        du, dv = mids[:, 0] - cu, mids[:, 1] - cvc
        A = np.stack([nrm[:, 0] * du + nrm[:, 1] * dv, -nrm[:, 0] * dv + nrm[:, 1] * du,
                      nrm[:, 0], nrm[:, 1]], 1)
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = A @ sol - y
        sim_fit = {"s": float(1 + sol[0]), "theta_deg": float(np.degrees(sol[1])),
                   "tu": float(sol[2]), "tv": float(sol[3]), "about": [cu, cvc],
                   "segments": len(good),
                   "resid_mm_rms_before": round(float(np.sqrt((y ** 2).mean()) * 1000), 1),
                   "resid_mm_rms_after": round(float(np.sqrt((res ** 2).mean()) * 1000), 1)}
    out = {"tag": a.tag, "sim": a.sim, "corr": a.corr, "rib_top_height_m": a.rib_h,
           "frames_used": len(names),
           "summary": {"segments_measured": len(rows), "segments_usable": len(good),
                       "abs_offset_mm_p50": round(float(np.percentile(np.abs([r["offset_mm"] for r in good]), 50)), 1) if good else None,
                       "abs_offset_mm_p90": round(float(np.percentile(np.abs([r["offset_mm"] for r in good]), 90)), 1) if good else None,
                       "height_error_mm_p50": round(float(np.median([r["height_error_mm"] for r in good])), 1) if good else None,
                       "by_class": by_class},
           "per_bay": bays, "similarity": sim_fit, "segments_detail": rows,
           "note": "offset_mm is the intercept of t = a + b*k over the frames that saw the segment; "
                   "positive = the member sits towards +normal of the lattice line. height_error_mm "
                   "is the slope: how much higher the real member top is than --rib-h."}
    p = os.path.join(a.out, "rib-fit-%s.json" % a.tag)
    json.dump(out, open(p, "w"), indent=1)
    print(json.dumps({"summary": out["summary"], "similarity": sim_fit}, indent=1))
    for kk, v in sorted(bays.items(), key=lambda kv: (int(kv[0].split(",")[0]), kv[0])):
        print(" bay %-4s %2d segs  dhu %+7.1f  dhv %+7.1f  |d| %6.1f mm  rms %5.1f  %s"
              % (kk, v["segments"], v["dhu_mm"], v["dhv_mm"], v["shift_mm"], v["resid_rms_mm"],
                 v["per_class_abs_p50_mm"]))
    print("wrote", p)


if __name__ == "__main__":
    main()
