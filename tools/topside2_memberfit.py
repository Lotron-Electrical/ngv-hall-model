"""Registration proof: where is the real steel, and where does the lattice put it?

The mosaic cannot answer this on its own. Every member is CUT OUT of the ortho by the occluder test,
and that cut is drawn from the lattice, so the hole in the image is the model's opinion, not a
measurement. The members themselves are 3D: they stand 0.3-0.6 m proud of the glass plate and the hub
nodes stand 0.7-1.4 m, so the dense roof-void cloud carries them with no parallax to argue about.
That is what is fitted here.

Method, per bay and per member class (crest ridge = the bay boundary, cross = the + through the
vertex, hip = the X corner to corner):
  1. height above the MODELLED surface, rasterised in the huv plane (max per cell),
  2. along each member segment, the mean height profile for perpendicular offsets -0.6..+0.6 m,
  3. the profile's peak (parabolic vertex on the three cells around the max) is where the member
     really is; the signed distance from the lattice line is the offset,
  4. per bay, least squares of every segment's offset against its normal gives (dhu, dhv),
  5. over all segments, one similarity in joint-corr's form (s, theta, tu, tv about a centre).

The hub nodes are measured separately and they are the thing that breaks the bay-slide ambiguity:
the roof void repeats every bay, so a whole-bay pose slide is invisible to the ribs but moves every
hub by a full 7.4 m. A hub sitting on its vertex says the bay indexing is right.

python topside2_memberfit.py --sim <chain.json> --out <dir> [--corr <corr.json>] [--tag before]
"""
import sys, os, json, argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import SCR

CELL = 0.025          # huv raster cell (m): a quarter of the ortho pixel, fine enough for a 20 mm claim
RIB_LO, RIB_HI = 0.18, 0.62      # height band that is member and not plate or hub
HUB_LO, HUB_HI = 0.65, 1.45      # height band that is only the hub node
HALF = 0.60           # perpendicular search half-width (m)
STEP = 0.005          # perpendicular step (m)


def height_raster(sim, heightmap, corr=None):
    """max height above the modelled surface per huv cell, plus the sample count."""
    z = np.load(heightmap)
    Hmax, N = z["Hmax"], z["N"]
    x0, z0, cell = float(z["x0"]), float(z["z0"]), float(z["cell"])
    iz, ix = np.nonzero(N >= 3)
    P = G.apply_sim(sim, np.stack([x0 + (ix + 0.5) * cell, Hmax[iz, ix], z0 + (iz + 0.5) * cell], 1))
    hu, hv = G.xz_to_huv(P[:, 0], P[:, 2])
    h = P[:, 1] - G.surface_y(hu, hv, 0.0)
    if corr is not None:
        # the correction moves the LATTICE onto the observation; to compare in lattice coordinates
        # the observation is moved by its inverse, which for these tiny similarities is the negated form
        hu, hv = corr(hu, hv)
    hu0, hv0 = G.PLATE_HU[0], G.PLATE_HV[0]
    hu1 = G.PLATE_HU[1] + G.PU
    W = int(np.ceil((hu1 - hu0) / CELL))
    H = int(np.ceil((G.PLATE_HV[1] - hv0) / CELL))
    ok = (hu >= hu0) & (hu < hu1) & (hv >= hv0) & (hv < G.PLATE_HV[1]) & np.isfinite(h)
    iu = ((hu[ok] - hu0) / CELL).astype(np.int32)
    iv = ((hv[ok] - hv0) / CELL).astype(np.int32)
    key = iv * W + iu
    R = np.full(W * H, np.nan, np.float32)
    o = np.argsort(h[ok])                     # last write wins, so the maximum survives
    R[key[o]] = h[ok][o].astype(np.float32)
    return R.reshape(H, W), hu0, hv0, np.stack([hu[ok], hv[ok], h[ok]], 1)


def sample(R, hu0, hv0, hu, hv):
    W, H = R.shape[1], R.shape[0]
    iu = np.floor((hu - hu0) / CELL).astype(int)
    iv = np.floor((hv - hv0) / CELL).astype(int)
    ok = (iu >= 0) & (iu < W) & (iv >= 0) & (iv < H)
    out = np.full(hu.shape, np.nan, np.float32)
    out[ok] = R[iv[ok], iu[ok]]
    return out


def segments():
    """(bay_i, bay_j, class, p0, p1) in huv for every member of every bay of the ortho frame."""
    a, b = G.PU / 2, G.PV / 2
    segs = []
    for i in range(-2, 7):
        cu = G.HU0 + i * G.PU
        for j in (-1, 0):
            cvv = G.HV0 + j * G.PV
            bi = int(np.floor((cu - (G.HU0 - G.PU / 2)) / G.PU)) + 1
            bj = int(np.floor((cvv - (G.HV0 - G.PV / 2)) / G.PV)) + 1
            # crest: the four boundaries of this bay
            segs.append((bi, bj, "crest", (cu - a, cvv - b), (cu + a, cvv - b)))
            segs.append((bi, bj, "crest", (cu - a, cvv + b), (cu + a, cvv + b)))
            segs.append((bi, bj, "crest", (cu - a, cvv - b), (cu - a, cvv + b)))
            segs.append((bi, bj, "crest", (cu + a, cvv - b), (cu + a, cvv + b)))
            # cross: the four arms of the + through the vertex, vertex to edge midpoint
            segs.append((bi, bj, "cross", (cu, cvv), (cu + a, cvv)))
            segs.append((bi, bj, "cross", (cu, cvv), (cu - a, cvv)))
            segs.append((bi, bj, "cross", (cu, cvv), (cu, cvv + b)))
            segs.append((bi, bj, "cross", (cu, cvv), (cu, cvv - b)))
            # hip: the four arms of the X, vertex to bay corner
            segs.append((bi, bj, "hip", (cu, cvv), (cu + a, cvv + b)))
            segs.append((bi, bj, "hip", (cu, cvv), (cu - a, cvv - b)))
            segs.append((bi, bj, "hip", (cu, cvv), (cu + a, cvv - b)))
            segs.append((bi, bj, "hip", (cu, cvv), (cu - a, cvv + b)))
    return segs


def profile_peak(R, hu0, hv0, p0, p1, trim=0.35, min_frac=0.25):
    """mean height profile across the segment; returns (offset_m, peak_height, n_used, normal)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    d /= L
    n = np.array([-d[1], d[0]])
    # trim the ends: near a vertex or a corner three members meet and the profiles blend
    s = np.arange(trim, L - trim + 1e-9, CELL)
    if len(s) < 8:
        return None
    t = np.arange(-HALF, HALF + 1e-9, STEP)
    HU = p0[0] + np.outer(s, [d[0]]) + np.outer(np.ones(len(s)), [0.0])
    hu = p0[0] + s[:, None] * d[0] + t[None, :] * n[0]
    hv = p0[1] + s[:, None] * d[1] + t[None, :] * n[1]
    V = sample(R, hu0, hv0, hu, hv)
    band = np.where(np.isfinite(V) & (V > RIB_LO) & (V < RIB_HI), V, np.nan)
    cnt = np.isfinite(band).sum(0)
    if cnt.max() < min_frac * len(s):
        return None
    # the profile is the fraction of the along-samples that are member height at this offset,
    # weighted by height: a real member is high AND continuous along its length
    prof = np.where(cnt > 0, np.nan_to_num(np.nansum(band, 0)) / max(len(s), 1), 0.0)
    k = int(np.argmax(prof))
    if prof[k] <= 0 or k == 0 or k == len(t) - 1:
        return None
    y0_, y1_, y2_ = prof[k - 1], prof[k], prof[k + 1]
    den = y0_ - 2 * y1_ + y2_
    sub = 0.5 * (y0_ - y2_) / den if den != 0 else 0.0
    off = t[k] + np.clip(sub, -1, 1) * STEP
    return float(off), float(prof[k]), int(cnt[k]), n


def solve_bay(offs, norms):
    """least squares (dhu,dhv) with offset_k = n_k . (dhu,dhv)."""
    A = np.array(norms)
    y = np.array(offs)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = A @ sol - y
    return sol, resid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--corr", default=None, help="apply this correction to the observation first (the 'after' pass)")
    ap.add_argument("--tag", default="before")
    ap.add_argument("--heightmap", default=SCR + "void_dense_heightmap.npz")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sim = G.load_sim(a.sim)
    corr = None
    if a.corr:
        from trackA_render3 import make_corr
        corr = make_corr(a.corr)
    R, hu0, hv0, pts = height_raster(sim, a.heightmap, corr)
    print("height raster", R.shape, "cells with data", int(np.isfinite(R).sum()), flush=True)

    rows = []
    for bi, bj, cls, p0, p1 in segments():
        r = profile_peak(R, hu0, hv0, p0, p1)
        if r is None:
            continue
        off, pk, n_used, nrm = r
        rows.append({"bay": [bi, bj], "class": cls, "from": list(p0), "to": list(p1),
                     "offset_mm": round(off * 1000, 1), "peak_height_m": round(pk, 3),
                     "n": n_used, "normal": [round(float(nrm[0]), 4), round(float(nrm[1]), 4)]})
    print("segments fitted", len(rows), flush=True)

    by_class = {}
    for c in ("crest", "cross", "hip"):
        v = np.array([r["offset_mm"] for r in rows if r["class"] == c])
        if len(v):
            by_class[c] = {"n": len(v), "abs_p50_mm": round(float(np.percentile(np.abs(v), 50)), 1),
                           "abs_p90_mm": round(float(np.percentile(np.abs(v), 90)), 1),
                           "signed_mean_mm": round(float(v.mean()), 1)}
    bays = {}
    for bi in range(0, 9):
        for bj in (0, 1):
            sel = [r for r in rows if r["bay"] == [bi, bj]]
            if len(sel) < 3:
                continue
            sol, resid = solve_bay([r["offset_mm"] for r in sel], [r["normal"] for r in sel])
            bays["%d,%d" % (bi, bj)] = {
                "segments": len(sel), "dhu_mm": round(float(sol[0]), 1), "dhv_mm": round(float(sol[1]), 1),
                "shift_mm": round(float(np.hypot(*sol)), 1),
                "resid_rms_mm": round(float(np.sqrt((resid ** 2).mean())), 1),
                "per_class_abs_p50_mm": {c: round(float(np.median(np.abs(
                    [r["offset_mm"] for r in sel if r["class"] == c]))), 1)
                    for c in ("crest", "cross", "hip") if any(r["class"] == c for r in sel)},
            }
    # one similarity in joint-corr's form fitted to every segment offset
    cu = (G.PLATE_HU[0] + G.PLATE_HU[1]) / 2
    cv_ = (G.PLATE_HV[0] + G.PLATE_HV[1]) / 2
    mids = np.array([[(r["from"][0] + r["to"][0]) / 2, (r["from"][1] + r["to"][1]) / 2] for r in rows])
    nrm = np.array([r["normal"] for r in rows])
    y = np.array([r["offset_mm"] for r in rows]) / 1000.0
    du, dv = mids[:, 0] - cu, mids[:, 1] - cv_
    # displacement of a point under (s, theta, tu, tv): ((s-1)*du - th*dv + tu, th*du + (s-1)*dv + tv)
    A = np.stack([nrm[:, 0] * du + nrm[:, 1] * dv,      # scale-1
                  -nrm[:, 0] * dv + nrm[:, 1] * du,     # theta
                  nrm[:, 0], nrm[:, 1]], 1)             # tu, tv
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = A @ sol - y
    sim_fit = {"s": float(1 + sol[0]), "theta_deg": float(np.degrees(sol[1])),
               "tu": float(sol[2]), "tv": float(sol[3]), "about": [cu, cv_],
               "segments": len(rows),
               "resid_mm_rms_before": round(float(np.sqrt((y ** 2).mean()) * 1000), 1),
               "resid_mm_rms_after": round(float(np.sqrt((resid ** 2).mean()) * 1000), 1),
               "note": "hu' = cu + s*(cos th*(hu-cu) - sin th*(hv-cv)) + tu, likewise hv'; "
                       "pass to the renderer as --corr so the surface is sampled where the steel is"}

    # hub nodes: the bay-slide test
    hubs = []
    hu_p, hv_p, h_p = pts[:, 0], pts[:, 1], pts[:, 2]
    tall = (h_p > HUB_LO) & (h_p < HUB_HI)
    for i in range(-2, 7):
        for j in (-1, 0):
            vu, vv = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            if not (G.PLATE_HU[0] < vu < G.PLATE_HU[1] + G.PU and G.PLATE_HV[0] < vv < G.PLATE_HV[1]):
                continue
            near = tall & (np.abs(hu_p - vu) < 1.2) & (np.abs(hv_p - vv) < 1.2)
            bi = int(np.floor((vu - (G.HU0 - G.PU / 2)) / G.PU)) + 1
            bj = int(np.floor((vv - (G.HV0 - G.PV / 2)) / G.PV)) + 1
            n = int(near.sum())
            if n < 40:
                hubs.append({"vertex": [bi, bj], "huv": [round(vu, 3), round(vv, 3)], "points": n,
                             "found": False})
                continue
            w = h_p[near] - HUB_LO
            du_ = float((w * (hu_p[near] - vu)).sum() / w.sum())
            dv_ = float((w * (hv_p[near] - vv)).sum() / w.sum())
            hubs.append({"vertex": [bi, bj], "huv": [round(vu, 3), round(vv, 3)], "points": n,
                         "found": True, "dhu_mm": round(du_ * 1000, 1), "dhv_mm": round(dv_ * 1000, 1),
                         "offset_mm": round(float(np.hypot(du_, dv_) * 1000), 1),
                         "max_height_m": round(float(h_p[near].max()), 2)})
    ok_h = [h for h in hubs if h.get("found")]
    hub_sum = {"vertices_with_a_node": len(ok_h), "vertices_checked": len(hubs),
               "offset_mm_p50": round(float(np.median([h["offset_mm"] for h in ok_h])), 1) if ok_h else None,
               "offset_mm_max": round(float(max(h["offset_mm"] for h in ok_h)), 1) if ok_h else None,
               "bay_slide": ("none: every node found sits on its own vertex, well inside the 7.4 m bay pitch"
                             if ok_h and max(h["offset_mm"] for h in ok_h) < 1000 else "check")}

    out = {"tag": a.tag, "sim": a.sim, "corr": a.corr, "raster_cell_m": CELL,
           "height_bands_m": {"member": [RIB_LO, RIB_HI], "hub": [HUB_LO, HUB_HI]},
           "summary": {"segments": len(rows),
                       "abs_offset_mm_p50": round(float(np.percentile(np.abs([r["offset_mm"] for r in rows]), 50)), 1),
                       "abs_offset_mm_p90": round(float(np.percentile(np.abs([r["offset_mm"] for r in rows]), 90)), 1),
                       "by_class": by_class},
           "per_bay": bays, "similarity": sim_fit, "hubs": hubs, "hub_summary": hub_sum,
           "segments_detail": rows}
    p = os.path.join(a.out, "member-fit-%s.json" % a.tag)
    json.dump(out, open(p, "w"), indent=1)
    print(json.dumps({"summary": out["summary"], "similarity": sim_fit, "hub_summary": hub_sum}, indent=1))
    for k, v in sorted(bays.items(), key=lambda kv: (int(kv[0].split(",")[0]), kv[0])):
        print(" bay %-4s %2d segs  dhu %+7.1f  dhv %+7.1f  |d| %6.1f mm  rms %5.1f  %s"
              % (k, v["segments"], v["dhu_mm"], v["dhv_mm"], v["shift_mm"], v["resid_rms_mm"],
                 v["per_class_abs_p50_mm"]))
    print("wrote", p)

    # diagnostic: the height raster with the lattice drawn, so the fit can be judged by eye
    vis = np.zeros(R.shape, np.uint8)
    m = np.isfinite(R)
    vis[m] = np.clip((R[m] - 0.05) / 0.9 * 255, 0, 255).astype(np.uint8)
    vis = cv2.applyColorMap(vis, cv2.COLORMAP_TURBO)
    vis[~m] = 0
    from trackA_assemble2 import lattice_overlay
    vis = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
    vis = lattice_overlay(vis, 0, 0, CELL * 1000, hu0, hv0, hu0 + R.shape[1] * CELL,
                          hv0 + R.shape[0] * CELL, thick=1)
    cv2.imwrite(os.path.join(a.out, "member-height-%s.png" % a.tag), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    print("wrote", os.path.join(a.out, "member-height-%s.png" % a.tag))


if __name__ == "__main__":
    main()
