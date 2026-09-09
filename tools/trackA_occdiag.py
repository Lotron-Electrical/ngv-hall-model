"""Track A (resume): occluder diagnostic. Project the tile's surface points into one frame, mark the
ones the analytic occluder rejects (red) and the ones it keeps (green), draw on the frame region.

python trackA_occdiag.py --sim <chain.json> --frame v006 --hu -9.5 --hv 4.5 --half 2 --out <jpg>
"""
import sys, os, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import load_cameras, image_path
from trackA_render2 import analytic_occluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--frame", required=True)
    ap.add_argument("--hu", type=float, required=True)
    ap.add_argument("--hv", type=float, required=True)
    ap.add_argument("--half", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cam = load_cameras(G.load_sim(a.sim))[a.frame]
    hu = np.arange(a.hu - a.half, a.hu + a.half, 0.04)
    hv = np.arange(a.hv - a.half, a.hv + a.half, 0.04)
    HU, HV = np.meshgrid(hu, hv)
    HU, HV = HU.ravel(), HV.ravel()
    P = G.surface_xyz(HU, HV, 0.02)
    occ = analytic_occluded(P, cam, HU, HV)
    u, v, z = cam.project(P)
    im = cv2.imread(image_path(a.frame), cv2.IMREAD_COLOR)
    for k in range(len(u)):
        if 0 <= u[k] < cam.w and 0 <= v[k] < cam.h:
            cv2.circle(im, (int(u[k]), int(v[k])), 3, (0, 0, 255) if occ[k] else (0, 200, 0), -1)
    ok = (u >= 0) & (u < cam.w) & (v >= 0) & (v < cam.h)
    x0, y0 = int(max(0, u[ok].min() - 50)), int(max(0, v[ok].min() - 50))
    x1, y1 = int(min(cam.w, u[ok].max() + 50)), int(min(cam.h, v[ok].max() + 50))
    reg = im[y0:y1, x0:x1]
    sc = min(1.0, 1600 / max(reg.shape[:2]))
    reg = cv2.resize(reg, (int(reg.shape[1] * sc), int(reg.shape[0] * sc)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(a.out, reg, [cv2.IMWRITE_JPEG_QUALITY, 88])
    c = cam.center
    chu, chv = G.xz_to_huv(c[0], c[2])
    print("camera huv", round(float(chu), 2), round(float(chv), 2), "y", round(float(c[1]), 3), "surface y at crop centre", round(float(G.surface_y(np.array([a.hu]), np.array([a.hv]), 0.0)[0]), 3), "occluded frac", occ.mean().round(3))


if __name__ == "__main__":
    main()
