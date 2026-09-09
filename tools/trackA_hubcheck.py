"""Track A (resume): project the funnel vertices (column-head hubs) near the 4K spot into the stills
and crop 1:1 around them with the projected 8 rib directions drawn, so the chain can be judged by eye
at full resolution (the rib centrelines at the rib TOP, +RIB_H, and at the surface, both drawn).

python trackA_hubcheck.py --sim <chain.json> --out <dir> [--vertices 5,0 5,1 4,0 4,1 6,0 6,1]
"""
import sys, os, json, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import load_cameras, image_path, RIB_H

COLS = {(0, 0): "S1", (1, 0): "S2", (2, 0): "S3", (3, 0): "S4", (4, 0): "S5", (5, 0): "S6",
        (0, 1): "N1", (1, 1): "N2", (2, 1): "N3", (3, 1): "N4", (4, 1): "N5", (5, 1): "N6"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vertices", nargs="*", default=["5,0", "5,1", "4,0", "4,1", "6,0", "6,1"])
    ap.add_argument("--half", type=int, default=350)
    ap.add_argument("--corr", default=None, help="joint-corr json: also draw the corrected vertex (cyan)")
    a = ap.parse_args()
    corr = None
    if a.corr:
        from trackA_render2 import make_corr
        corr = make_corr(a.corr)
    os.makedirs(a.out, exist_ok=True)
    sim = G.load_sim(a.sim)
    cams = load_cameras(sim)
    excl = {"v021", "v022", "v025", "v026", "v027", "v028"}
    report = []
    for vs in a.vertices:
        i, j = [int(x) for x in vs.split(",")]
        hu, hv = G.HU0 + i * G.PU, G.HV0 + (j - 1) * G.PV   # j here = row index 0 south / 1 north
        X = G.surface_xyz(np.array([hu]), np.array([hv]), 0.0)
        cands = []
        for n, cam in cams.items():
            if n in excl:
                continue
            u, v, z = cam.project(X)
            Xc = X @ cam.R.T + cam.t
            if z[0] <= 0 or Xc[0, 2] < 0.35 * np.linalg.norm(Xc[0]):
                continue
            if not (a.half < u[0] < cam.w - a.half and a.half < v[0] < cam.h - a.half):
                continue
            dist = float(np.linalg.norm(X[0] - cam.center))
            r = np.hypot((u[0] - cam.w / 2) / cam.w, (v[0] - cam.h / 2) / cam.h)
            cands.append((dist * (1 + r), n, float(u[0]), float(v[0]), dist))
        cands.sort()
        for sc, n, u, v, dist in cands[:2]:
            cam = cams[n]
            im = cv2.imread(image_path(n), cv2.IMREAD_COLOR)
            x0, y0 = int(u - a.half), int(v - a.half)
            crop = im[y0:y0 + 2 * a.half, x0:x0 + 2 * a.half].copy()
            # rib directions: 8 short segments (0.9 m) from the vertex, at the surface and at the rib top
            s = np.linspace(0.05, 0.9, 30)
            for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nrm = np.hypot(du, dv)
                pu = hu + du / nrm * s
                pvv = hv + dv / nrm * s
                for h, col in ((0.0, (0, 200, 255)), (RIB_H, (0, 0, 255))):
                    P = G.surface_xyz(pu, pvv, h)
                    uu, vv, zz = cam.project(P)
                    pts = np.stack([uu - x0, vv - y0], 1).astype(np.int32)
                    cv2.polylines(crop, [pts.reshape(-1, 1, 2)], False, col, 1, cv2.LINE_AA)
            cv2.drawMarker(crop, (a.half, a.half), (255, 0, 255), cv2.MARKER_CROSS, 40, 1, cv2.LINE_AA)
            if corr is not None:
                hu2, hv2 = corr(np.array([hu]), np.array([hv]))
                for h, col in ((0.0, (255, 255, 0)), (RIB_H, (255, 128, 0))):
                    Xc2 = G.surface_xyz(hu2, hv2, h)
                    u2, v2, z2 = cam.project(Xc2)
                    cv2.drawMarker(crop, (int(u2[0] - x0), int(v2[0] - y0)), col, cv2.MARKER_TILTED_CROSS, 30, 2, cv2.LINE_AA)
            mmpp = 1000.0 * dist / cam.params[0]
            cv2.putText(crop, f"{n} V{i},{j} {COLS.get((i, j), '-')} d={dist:.2f}m {mmpp:.1f}mm/px", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(crop, f"{n} V{i},{j} {COLS.get((i, j), '-')} d={dist:.2f}m {mmpp:.1f}mm/px", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            out = os.path.join(a.out, f"hub_V{i}_{j}_{n}.jpg")
            cv2.imwrite(out, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
            report.append({"vertex": [i, j], "column": COLS.get((i, j)), "frame": n, "u": u, "v": v, "dist_m": dist, "mm_per_px": mmpp, "crop": out})
            print(f"V{i},{j} {COLS.get((i,j),'-')}: {n} at ({u:.0f},{v:.0f}) dist {dist:.2f} m, {mmpp:.1f} mm/px -> {out}")
    json.dump(report, open(os.path.join(a.out, "hubcheck.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
