"""Track A step 2d: independent check of the chain against the stills.

For each still, every rib line of the lattice (cross lines through the hubs, the diagonals, the crest
lines) that lies within 9 m of the camera is projected at rib-top height (surface + RIB_H) and the
image brightness is averaged along the projected segment for perpendicular shifts of -80..+80 px.
Steel rib tops are uniformly bright; the glass field is a mix of white matrix and dark slabs, so the
brightness profile peaks on the rib. The shift of the peak is the residual (px), converted to mm
with the local ground-sampling distance. Also reports the in-plane offset of the dense-cloud rib
points (0.15-0.35 m above the model surface) from the nearest lattice line, in mm.

python trackA_ribcheck.py --sim <chain.json> [--frames v035,v040,...] [--out json]
"""
import sys, os, json, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import load_cameras, image_path, line_dists, RIB_H, IMG
from trackA_ply import read_ply

SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"


def rib_segments(step=0.1):
    """list of (kind, pts(N,2) huv) for the rib lines inside the plate, split per bay so that segments
    are short (<= half a bay)."""
    segs = []
    for i in range(-1, 6):
        for j in range(-1, 1):
            cu, cv_ = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            a, b = G.PU / 2, G.PV / 2
            s = np.arange(0, 1 + 1e-9, step / a)
            for su, sv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                segs.append(("cross", np.stack([cu + su * a * s, cv_ + sv * b * s], 1)))
            for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                segs.append(("diag", np.stack([cu + su * a * s, cv_ + sv * b * s], 1)))
            # crest lines around the bay (4 half-sides each, shared with neighbours: only take two)
            segs.append(("crest", np.stack([cu + a * np.ones_like(s), cv_ + b * (2 * s - 1)], 1)))
            segs.append(("crest", np.stack([cu + a * (2 * s - 1), cv_ + b * np.ones_like(s)], 1)))
    out = []
    for kind, pts in segs:
        ok = (pts[:, 0] >= G.PLATE_HU[0]) & (pts[:, 0] <= G.PLATE_HU[1]) & (pts[:, 1] >= G.PLATE_HV[0]) & (pts[:, 1] <= G.PLATE_HV[1])
        if ok.sum() >= 5:
            out.append((kind, pts[ok]))
    return out


def texture_image(gray):
    """local standard deviation in a 9x9 window (rib tops are smooth, the glass field is not)."""
    g = gray.astype(np.float32)
    m = cv2.blur(g, (9, 9))
    m2 = cv2.blur(g * g, (9, 9))
    return np.sqrt(np.maximum(m2 - m * m, 0))


def check_frame(name, cam, gray, segs, maxdist=9.0, shifts=np.arange(-120, 121, 2)):
    """Rib centre = the minimum of the along-segment mean of the texture image, box-filtered over the
    expected rib width, searched over perpendicular shifts of +-120 px."""
    tex = texture_image(gray)
    res = []
    for kind, pts in segs:
        hu, hv = pts[:, 0], pts[:, 1]
        P = G.surface_xyz(hu, hv, RIB_H)
        d = np.linalg.norm(P - cam.center, axis=1)
        u, v, z = cam.project(P)
        Xc = P @ cam.R.T + cam.t
        ok = cam.inside(u, v, z, margin=130) & (d < maxdist) & (Xc[:, 2] > 0.35 * np.linalg.norm(Xc, axis=1))
        ok &= np.abs(hv - 7.544) > 0.6
        if ok.sum() < 6:
            continue
        u, v, d = u[ok], v[ok], d[ok]
        du, dv = np.gradient(u), np.gradient(v)
        L = np.hypot(du, dv) + 1e-9
        pu, pv = -dv / L, du / L
        prof = []
        for s in shifts:
            us, vs = u + s * pu, v + s * pv
            samp = cv2.remap(tex, us.astype(np.float32).reshape(1, -1), vs.astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR)
            prof.append(samp.mean())
        prof = np.array(prof)
        dist = float(np.median(d))
        w_px = 0.22 * cam.params[0] / dist
        k = max(1, int(round(w_px / 2 / 2)))  # half-width in profile samples (2 px per sample)
        sm = np.convolve(prof, np.ones(2 * k + 1) / (2 * k + 1), mode="same")
        inner = slice(k, len(sm) - k)
        i = int(np.argmin(sm[inner])) + k
        centre = float(shifts[i])
        contrast = float(np.median(prof) - sm[i])
        if contrast < 0.25 * np.median(prof):
            continue
        mmpp = 1000.0 * dist / cam.params[0]
        res.append({"kind": kind, "n": int(ok.sum()), "dist_m": dist, "resid_px": centre, "resid_mm_est": centre * mmpp,
                    "rib_width_px": float(w_px), "contrast": contrast})
    return res


def cloud_offsets(sim):
    mm, _ = read_ply("E:/sitecapture-captures/ngv-site/rebuild-roofvoid/topside-extended-20260821.ply")
    P = np.stack([np.asarray(mm["x"], np.float32), np.asarray(mm["y"], np.float32), np.asarray(mm["z"], np.float32)], 1).astype(np.float64)
    P = G.apply_sim(sim, P)
    hu, hv = G.xz_to_huv(P[:, 0], P[:, 2])
    h = P[:, 1] - G.surface_y(hu, hv, 0)
    inp = (hu > G.PLATE_HU[0]) & (hu < G.PLATE_HU[1]) & (hv > G.PLATE_HV[0]) & (hv < G.PLATE_HV[1]) & (h > 0.15) & (h < 0.35) & (np.abs(hv - 7.544) > 0.7)
    hu, hv = hu[inp], hv[inp]
    du = ((hu - G.HU0 + G.PU / 2) % G.PU) - G.PU / 2
    dv = ((hv - G.HV0 + G.PV / 2) % G.PV) - G.PV / 2
    out = {}
    # cross lines: signed offset from the nearest vertex row / column line (points within 0.3 m)
    m = (np.abs(dv) < 0.3) & (np.abs(du) > 0.5)
    out["cross_row_offset_mm"] = {"n": int(m.sum()), "median": float(np.median(dv[m]) * 1000), "p25": float(np.percentile(dv[m], 25) * 1000), "p75": float(np.percentile(dv[m], 75) * 1000)}
    m = (np.abs(du) < 0.3) & (np.abs(dv) > 0.5)
    out["cross_col_offset_mm"] = {"n": int(m.sum()), "median": float(np.median(du[m]) * 1000), "p25": float(np.percentile(du[m], 25) * 1000), "p75": float(np.percentile(du[m], 75) * 1000)}
    sd = (np.abs(du) - np.abs(dv)) / np.sqrt(2)
    m = (np.abs(sd) < 0.3) & (np.abs(du) > 0.5) & (np.abs(dv) > 0.5)
    out["diag_offset_mm"] = {"n": int(m.sum()), "median": float(np.median(sd[m]) * 1000), "p25": float(np.percentile(sd[m], 25) * 1000), "p75": float(np.percentile(sd[m], 75) * 1000)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--frames", default="v001,v003,v005,v008,v010,v012,v033,v035,v037,v040,v042,v044,v046,v050,v053,v056,v058,v060,v062")
    ap.add_argument("--out", default=SCR + "ribcheck.json")
    a = ap.parse_args()
    sim = G.load_sim(a.sim)
    cams = load_cameras(sim)
    segs = rib_segments()
    allres = {}
    flat = []
    for n in a.frames.split(","):
        gray = cv2.imread(image_path(n), cv2.IMREAD_GRAYSCALE)
        r = check_frame(n, cams[n], gray, segs)
        allres[n] = r
        px = np.array([x["resid_px"] for x in r])
        mmv = np.array([x["resid_mm_est"] for x in r])
        flat += r
        if len(r):
            print(f"{n}: {len(r)} rib segments  resid px median {np.median(px):+.1f} (|.| p50 {np.median(np.abs(px)):.1f}, p90 {np.percentile(np.abs(px),90):.1f})  "
                  f"mm median {np.median(mmv):+.0f} (|.| p50 {np.median(np.abs(mmv)):.0f})")
        else:
            print(n, "no measurable rib segments")
    px = np.array([x["resid_px"] for x in flat])
    mmv = np.array([x["resid_mm_est"] for x in flat])
    summary = {"segments": len(flat), "resid_px_median_signed": float(np.median(px)), "resid_px_abs_p50": float(np.median(np.abs(px))),
               "resid_px_abs_p90": float(np.percentile(np.abs(px), 90)), "resid_mm_abs_p50": float(np.median(np.abs(mmv))),
               "resid_mm_abs_p90": float(np.percentile(np.abs(mmv), 90)), "resid_mm_median_signed": float(np.median(mmv))}
    for kind in ("cross", "diag", "crest"):
        k = [x for x in flat if x["kind"] == kind]
        if k:
            summary[kind] = {"n": len(k), "px_abs_p50": float(np.median([abs(x["resid_px"]) for x in k])), "mm_abs_p50": float(np.median([abs(x["resid_mm_est"]) for x in k]))}
    print("ALL:", json.dumps(summary))
    cl = cloud_offsets(sim)
    print("dense-cloud rib points vs lattice lines (in-plane, mm):", json.dumps(cl))
    json.dump({"summary": summary, "cloud_offsets": cl, "frames": allres, "note": "resid_px = perpendicular shift of the bright rib-top plateau from the projected rib line (rib top at surface+%.2f m); positive = towards +perp of the segment direction" % RIB_H},
              open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
