"""Measure the wall's true depth FROM THE FRAMES, not from the mesh.

WHY: model.glb's `walls` mesh is a decimated blocky envelope. Its dominant face fits a plane to
0.03 mm, but that plane is not necessarily where the stone the cameras photographed actually is:
the certified sparse cloud sits ~85 mm (north) and ~250 mm (south) in front of it. Either number,
if wrong, drags the orthophoto sideways by offset*tan(incidence) -- 250 mm at 70 deg is 0.7 m.

METHOD, per patch: take the two cameras that see it from the most different directions, resample
the patch from each at a range of surface offsets (the sampling plane pushed towards the room),
and score the pair by zero-mean normalised cross-correlation. Only the true depth makes the two
resamplings agree; a wrong depth shears them apart by the parallax between the two views. The
offset that maximises NCC is the wall's real depth at that patch, measured in the same frame the
render uses, with no appeal to the mesh at all.

  python tools/wall_depth_check.py --wall north|south --out <dir> [--patches 240]
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wall_ortho as W
import underside_geom as U

PATCH = 96          # px at --mm, i.e. 0.38 m square at 4 mm
# The sweep must be SYMMETRIC about the surface being tested. An asymmetric window biases the
# parabolic peak towards the long side, which on plain limestone (a 400 mm wide correlation peak)
# is worth tens of millimetres -- exactly the size of the thing being measured.
OFFS = np.arange(-0.10, 0.62, 0.02)


def set_sweep(half, step=0.02):
    global OFFS
    OFFS = np.arange(-half, half + step / 2, step)


def ncc(a, b):
    a = a.astype(np.float32).ravel()
    b = b.astype(np.float32).ravel()
    a = a - a.mean()
    b = b - b.mean()
    da, db = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    if da < 1e-6 or db < 1e-6:
        return -1.0
    return float((a * b).sum() / (da * db))


def sample(wall, cam, im, sv, hgt, prot, plane, sgn):
    dep = plane[0] + plane[1] * sv + plane[2] * hgt + sgn * prot
    uu, dd = W.hall_of(wall, sv, dep)
    P = W.hall_to_world(uu, dd, hgt)
    uu, vv, z = cam.project(P)
    if not (cam.inside(uu, vv, z, margin=4) & U.distortion_ok(cam, P)).all():
        return None
    n = len(uu)
    rows = (n + 255) // 256
    mx = np.zeros(rows * 256, np.float32); mx[:n] = uu
    my = np.zeros(rows * 256, np.float32); my[:n] = vv
    g = cv2.remap(im, mx.reshape(rows, 256), my.reshape(rows, 256), cv2.INTER_LINEAR,
                  borderMode=cv2.BORDER_REPLICATE)
    return g.reshape(-1)[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wall", required=True, choices=sorted(W.WALLS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--patches", type=int, default=240)
    ap.add_argument("--mm", type=float, default=4.0)
    ap.add_argument("--source", default="walk")
    ap.add_argument("--s-range", default=None,
                    help="lo,hi (metres of the across axis) to confine the patches to, e.g. the "
                         "flat stone piers of an end wall rather than its 6 m gallery recess")
    ap.add_argument("--min-angle", type=float, default=20.0,
                    help="smallest pair baseline angle, in degrees, that still resolves depth")
    ap.add_argument("--max-dist", type=float, default=30.0)
    ap.add_argument("--frame-check", choices=("full", "centre"), default="full",
                    help="full: a camera must hold the patch in frame across the WHOLE sweep, "
                         "which keeps the stacked profile unbiased. centre: only at offset 0, for "
                         "a first wide reconnaissance sweep where full would reject everything")
    ap.add_argument("--sweep", type=float, default=None,
                    help="half-width of a SYMMETRIC depth sweep in metres (default: the "
                         "asymmetric -0.10..+0.60 first-pass window)")
    ap.add_argument("--surface-offset", type=float, default=0.0,
                    help="metres already applied to the render's surface; the sweep is then "
                         "measured from THAT surface, so a verified correction peaks at 0")
    a = ap.parse_args()
    if a.sweep:
        set_sweep(a.sweep)

    room, alltri, nrm, plane, _ = W.wall_geometry(a.wall, os.path.join(a.out, "wall-%s-geom.npz" % a.wall))
    pl = plane["d = a + b*u + c*h"]
    sgn = W.WALLS[a.wall]["sgn"]
    C = W.coarse_map(a.wall, alltri) + a.surface_offset
    spec = W.WALLS[a.wall]
    S_LO, S_HI = spec["s0"], spec["s1"]
    S_BANDS = ([tuple(float(x) for x in b.split(":")) for b in a.s_range.split(",")]
               if a.s_range else [(S_LO, S_HI)])

    classes = list(U.CLASSES) if a.source == "all" else a.source.split(",")
    cc = {}
    for c in classes:
        for n, v in U.load_class(c).items():
            cc[c + "/" + n] = v
    names = sorted(cc)
    cams = [cc[n][0] for n in names]
    centres = np.array([c.center for c in cams])
    gray = {}

    rng = np.random.default_rng(3)
    rows = []
    tried = 0
    while len(rows) < a.patches and tried < a.patches * 12:
        tried += 1
        blo, bhi = S_BANDS[rng.integers(len(S_BANDS))]
        if bhi - blo < 0.4 + PATCH * a.mm / 1000:
            continue
        u0 = rng.uniform(blo + 0.2, bhi - 0.2 - PATCH * a.mm / 1000)
        h0 = rng.uniform(0.6, 11.0)
        gx, gy = np.meshgrid(np.arange(PATCH), np.arange(PATCH))
        u = (u0 + gx.ravel() * a.mm / 1000).astype(float)
        hgt = (h0 + gy.ravel() * a.mm / 1000).astype(float)
        q = W.coarse_lookup(a.wall, C, u, hgt)
        if (q < -8).any():
            continue
        prot0 = float(np.median(q))
        if q.std() > 0.02:
            continue                      # keep the patch on one flat face
        d0 = pl[0] + pl[1] * u + pl[2] * hgt + sgn * prot0
        P = W.hall_to_world(*W.hall_of(a.wall, u, d0), hgt)
        Pc = P.mean(0)
        # the two cameras with the widest angle between their lines of sight to the patch
        v = Pc[None, :] - centres
        dist = np.linalg.norm(v, axis=1)
        vv = v / dist[:, None]
        nvec = -sgn * W.depth_axis(a.wall)
        inc = np.degrees(np.arccos(np.clip(np.abs(vv @ nvec), 0, 1)))
        cand = np.nonzero((dist > 1.5) & (dist < a.max_dist) & (inc < 72))[0]
        if len(cand) < 2:
            continue
        # framing + occlusion. The framing test has to cover the WHOLE offset sweep, not just
        # the mesh depth: a camera that loses the patch off the edge at +0.6 m would score -1
        # there and hand the peak to whichever offset still happened to be in frame.
        corner = np.array([0, PATCH - 1, (PATCH - 1) * PATCH, PATCH * PATCH - 1])
        good = []
        for i in cand:
            ok = True
            for off in ((0.0,) if a.frame_check == "centre" else (OFFS[0], 0.0, OFFS[-1])):
                dq = pl[0] + pl[1] * u[corner] + pl[2] * hgt[corner] + sgn * (prot0 + off)
                Q = W.hall_to_world(*W.hall_of(a.wall, u[corner], dq), hgt[corner])
                a2, b2, z2 = cams[i].project(Q)
                if not (cams[i].inside(a2, b2, z2, margin=12) & U.distortion_ok(cams[i], Q)).all():
                    ok = False
                    break
            if not ok:
                continue
            if W._occluded(a.wall, u[corner], hgt[corner], np.full(4, prot0), P[corner],
                           cams[i].center, C, sgn, pl, W.COLUMN_FEET, True).any():
                continue
            if names[i] not in gray:
                gray[names[i]] = cv2.imread(cc[names[i]][1], cv2.IMREAD_GRAYSCALE)
            good.append(i)
            if len(good) > 40:
                break
        if len(good) < 2:
            continue
        gv = vv[good]
        ang = np.degrees(np.arccos(np.clip(gv @ gv.T, -1, 1)))
        ang = np.where(ang > 75, 0.0, ang)      # a pair that wide is two grazing views, not a baseline
        i, j = np.unravel_index(np.argmax(ang), ang.shape)
        if ang[i, j] < a.min_angle:
            continue
        ca, cb = good[i], good[j]
        best, curve = None, []
        for off in OFFS:
            pr = np.full(len(u), prot0 + off)
            A = sample(a.wall, cams[ca], gray[names[ca]], u, hgt, pr, pl, sgn)
            B = sample(a.wall, cams[cb], gray[names[cb]], u, hgt, pr, pl, sgn)
            if A is None or B is None:
                curve.append(-1.0)
                continue
            curve.append(ncc(A, B))
        curve = np.array(curve)
        if curve.max() < 0.5:
            continue
        k = int(np.argmax(curve))
        if k in (0, len(curve) - 1):
            continue
        # parabolic refinement on the three points around the peak
        y0, y1, y2 = curve[k - 1], curve[k], curve[k + 1]
        den = (y0 - 2 * y1 + y2)
        sub = 0.5 * (y0 - y2) / den if abs(den) > 1e-9 else 0.0
        off = OFFS[k] + sub * (OFFS[1] - OFFS[0])
        rows.append({"u": round(u0 + PATCH * a.mm / 2000, 2), "h": round(h0 + PATCH * a.mm / 2000, 2),
                     "mesh_prot_m": round(prot0, 3), "offset_m": round(float(off), 3),
                     "true_prot_m": round(float(prot0 + off), 3), "ncc": round(float(curve[k]), 3),
                     "angle_deg": round(float(ang[i, j]), 1),
                     "curve": [round(float(x), 3) for x in curve]})
    o = np.array([r["offset_m"] for r in rows])
    n = np.array([r["ncc"] for r in rows])
    hh = np.array([r["h"] for r in rows])
    uu = np.array([r["u"] for r in rows])
    strong = n > 0.75
    out = {"wall": a.wall, "source": a.source, "patches": len(rows),
           "surface_offset_already_applied_m": a.surface_offset,
           "plane": pl, "patch_px": PATCH, "offsets_m": [float(x) for x in OFFS],
           "offset_mm": {"median": float(1000 * np.median(o)),
                         "median_strong_ncc": float(1000 * np.median(o[strong])) if strong.any() else None,
                         "p25": float(1000 * np.percentile(o, 25)),
                         "p75": float(1000 * np.percentile(o, 75)),
                         "n_strong": int(strong.sum())},
           "by_height": {}, "by_u": {}, "rows": rows}
    for lo, hi in ((0, 3), (3, 6), (6, 9), (9, 12)):
        s = (hh >= lo) & (hh < hi)
        if s.sum() > 3:
            out["by_height"]["h%d_%d" % (lo, hi)] = {"n": int(s.sum()),
                                                     "median_offset_mm": float(1000 * np.median(o[s]))}
    for lo in range(0, 52, 10):
        s = (uu >= lo) & (uu < lo + 10)
        if s.sum() > 3:
            out["by_u"]["u%d_%d" % (lo, lo + 10)] = {"n": int(s.sum()),
                                                     "median_offset_mm": float(1000 * np.median(o[s]))}
    # THE NUMBER TO TRUST: a single patch of plain limestone gives a broad, badly localised NCC
    # peak, so the per-patch medians above scatter. Stacking the curves of every patch that sits on
    # the SAME modelled face turns 100 weak peaks into one sharp one, and that is what the report
    # quotes as the wall's real offset from the modelled surface.
    cur = np.array([r["curve"] for r in rows])
    out["stacked"] = {}
    mp = np.array([r["mesh_prot_m"] for r in rows])
    for nm, lo, hi in (("main_face", -0.02, 0.05), ("proud_course", 0.10, 0.30), ("all", -1, 9)):
        m = (mp >= lo) & (mp < hi)
        if m.sum() < 5:
            continue
        st = np.where(cur[m] > -0.5, cur[m], np.nan)
        prof = np.nanmean(st, axis=0)
        k = int(np.nanargmax(prof))
        y0, y1, y2 = prof[max(k - 1, 0)], prof[k], prof[min(k + 1, len(prof) - 1)]
        den = y0 - 2 * y1 + y2
        sub = 0.5 * (y0 - y2) / den if abs(den) > 1e-9 else 0.0
        pk = float(OFFS[k] + sub * (OFFS[1] - OFFS[0]))
        half = prof > (y1 + prof.min()) / 2
        out["stacked"][nm] = {"n": int(m.sum()), "peak_offset_mm": round(1000 * pk, 1),
                              "peak_ncc": round(float(y1), 4),
                              "fwhm_mm": round(1000 * float(half.sum() * (OFFS[1] - OFFS[0])), 0),
                              "profile": [round(float(x), 4) for x in prof]}
    p = os.path.join(a.out, "depth-check-%s.json" % a.wall)
    json.dump(out, open(p, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "offsets_m")}, indent=1))
    print("->", p)


if __name__ == "__main__":
    main()
