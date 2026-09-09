"""Track A (resume): show where an ortho crop comes from. For a crop centre (hu,hv) and half-size,
find the frames used there (topside-cam.png), project the crop outline and a 0.5 m grid at the
modelled surface into the most-used frame, draw them and save that frame region downsized.

python trackA_cropcheck.py <render dir> --sim <chain.json> --hu -9.5 --hv 4.5 --half 2 --out <jpg>
"""
import sys, os, json, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G
from trackA_ortho import load_cameras, image_path, residual_field
from trackA_render2 import surface_with_corr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--sim", required=True)
    ap.add_argument("--hu", type=float, required=True)
    ap.add_argument("--hv", type=float, required=True)
    ap.add_argument("--half", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    args = json.load(open(os.path.join(a.dir, "render-args.json")))
    mm, hu0, hv0 = args["mm"], args["hu0"], args["hv0"]
    cam_img = cv2.imread(os.path.join(a.dir, "topside-cam.png"), cv2.IMREAD_UNCHANGED)
    cx, cy = int((a.hu - hu0) * 1000 / mm), int((a.hv - hv0) * 1000 / mm)
    hp = int(a.half * 1000 / mm)
    sub = cam_img[max(0, cy - hp):cy + hp, max(0, cx - hp):cx + hp]
    ids, cnt = np.unique(sub[sub != 65535], return_counts=True)
    order = np.argsort(-cnt)
    print("frames used in the crop:", [(args["names"][i], int(c)) for i, c in zip(ids[order], cnt[order])][:8])
    sim = G.load_sim(a.sim)
    cams = load_cameras(sim)
    Fs, cellF = residual_field(sim)
    name = args["names"][ids[order][0]]
    cam = cams[name]
    im = cv2.imread(image_path(name), cv2.IMREAD_COLOR)
    # grid lines every 0.5 m over the crop
    pts_all = []
    for k in np.arange(-a.half, a.half + 1e-6, 0.5):
        for (pu, pv) in ((np.full(200, a.hu + k), np.linspace(a.hv - a.half, a.hv + a.half, 200)),
                         (np.linspace(a.hu - a.half, a.hu + a.half, 200), np.full(200, a.hv + k))):
            P, n, c = surface_with_corr(pu, pv, args["slab"], Fs, cellF)
            u, v, z = cam.project(P)
            pts = np.stack([u, v], 1).astype(np.int32)
            col = (0, 0, 255) if abs(k) < 1e-6 else (0, 200, 255)
            cv2.polylines(im, [pts.reshape(-1, 1, 2)], False, col, 2, cv2.LINE_AA)
            pts_all.append(pts)
    P = np.concatenate(pts_all)
    x0, y0 = max(0, P[:, 0].min() - 100), max(0, P[:, 1].min() - 100)
    x1, y1 = min(im.shape[1], P[:, 0].max() + 100), min(im.shape[0], P[:, 1].max() + 100)
    reg = im[y0:y1, x0:x1]
    sc = min(1.0, 1600 / max(reg.shape[:2]))
    reg = cv2.resize(reg, (int(reg.shape[1] * sc), int(reg.shape[0] * sc)), interpolation=cv2.INTER_AREA)
    cv2.putText(reg, f"{name} crop ({a.hu},{a.hv}) +-{a.half} m, grid 0.5 m (red = centre lines)", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imwrite(a.out, reg, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("wrote", a.out, "region", x0, y0, x1, y1)


if __name__ == "__main__":
    main()
