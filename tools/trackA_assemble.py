"""Track A: assemble rendered tiles into the full ortho PNGs + previews + lattice-overlay crops.

python trackA_assemble.py <render dir> [--preview-only] [--crop hu,hv,name ...]
Writes in <render dir>: topside-ortho.png, topside-observed.png, topside-gsd.png, topside-cam.png,
plus preview/*.jpg (<= 2000 px).
"""
import sys, os, json, glob, argparse
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G


def load_all(d):
    args = json.load(open(os.path.join(d, "render-args.json")))
    W, H, mm = args["W"], args["H"], args["mm"]
    rgb = np.zeros((H, W, 3), np.uint8)
    cam = np.full((H, W), 65535, np.uint16)
    gsd = np.zeros((H, W), np.float32)
    obs = np.zeros((H, W), bool)
    corr = np.zeros((H, W), np.float32)
    for p in glob.glob(os.path.join(d, "tiles", "t_*.npz")):
        _, py0, px0 = os.path.basename(p)[:-4].split("_")
        py0, px0 = int(py0), int(px0)
        z = np.load(p)
        th, tw = z["rgb"].shape[:2]
        rgb[py0:py0 + th, px0:px0 + tw] = z["rgb"]
        cam[py0:py0 + th, px0:px0 + tw] = z["cam"]
        gsd[py0:py0 + th, px0:px0 + tw] = z["gsd"]
        obs[py0:py0 + th, px0:px0 + tw] = z["obs"]
        corr[py0:py0 + th, px0:px0 + tw] = z["corr"]
    return args, rgb, cam, gsd, obs, corr


def lattice_overlay(img, px0, py0, mm, thick=2):
    """draw the lattice (edges red, cross cyan, diagonals yellow, anti-diagonals green) on a crop
    whose top-left pixel is (px0,py0) of the full ortho."""
    h, w = img.shape[:2]

    def to_px(hu, hv):
        return (hu - G.PLATE_HU[0]) * 1000 / mm - px0, (hv - G.PLATE_HV[0]) * 1000 / mm - py0

    def line(hu1, hv1, hu2, hv2, col):
        x1, y1 = to_px(hu1, hv1)
        x2, y2 = to_px(hu2, hv2)
        cv2.line(img, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), col, thick, cv2.LINE_AA)

    lo_u, hi_u = G.PLATE_HU
    lo_v, hi_v = G.PLATE_HV
    for i in range(-2, 7):
        hu = G.HU0 + (i + 0.5) * G.PU
        if lo_u - 0.01 <= hu <= hi_u + 0.01:
            line(hu, lo_v, hu, hi_v, (255, 0, 0))
    for j in range(-2, 2):
        hv = G.HV0 + (j + 0.5) * G.PV
        if lo_v - 0.01 <= hv <= hi_v + 0.01:
            line(lo_u, hv, hi_u, hv, (255, 0, 0))
    for i in range(-1, 6):
        line(G.HU0 + i * G.PU, lo_v, G.HU0 + i * G.PU, hi_v, (0, 200, 255))
    for j in range(-1, 1):
        line(lo_u, G.HV0 + j * G.PV, hi_u, G.HV0 + j * G.PV, (0, 200, 255))
    a, b = G.PU / 2, G.PV / 2
    for i in range(-1, 6):
        for j in range(-1, 1):
            cu, cv_ = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            line(cu - a, cv_ - b, cu + a, cv_ + b, (255, 220, 0))
            line(cu - a, cv_ + b, cu + a, cv_ - b, (255, 220, 0))
            line(cu + a, cv_, cu, cv_ + b, (0, 255, 80))
            line(cu, cv_ + b, cu - a, cv_, (0, 255, 80))
            line(cu - a, cv_, cu, cv_ - b, (0, 255, 80))
            line(cu, cv_ - b, cu + a, cv_, (0, 255, 80))
            x, y = to_px(cu, cv_)
            if 0 <= x < w and 0 <= y < h:
                cv2.circle(img, (int(x), int(y)), 12, (255, 0, 255), 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--preview-only", action="store_true")
    ap.add_argument("--crop", action="append", default=[], help="hu,hv,name : 1000x1000 crop centred there")
    a = ap.parse_args()
    d = a.dir
    args, rgb, cam, gsd, obs, corr = load_all(d)
    W, H, mm = args["W"], args["H"], args["mm"]
    pv = os.path.join(d, "preview")
    os.makedirs(pv, exist_ok=True)
    if not a.preview_only:
        cv2.imwrite(os.path.join(d, "topside-ortho.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(os.path.join(d, "topside-observed.png"), (obs * 255).astype(np.uint8))
        # gsd in mm per image pixel, stored x8 (0..255 -> 0..32 mm), 0 = unobserved
        cv2.imwrite(os.path.join(d, "topside-gsd.png"), np.clip(gsd * 8, 0, 255).astype(np.uint8))
        cv2.imwrite(os.path.join(d, "topside-cam.png"), cam.astype(np.uint16))
        np.save(os.path.join(d, "topside-gsd.npy"), gsd)
        print("wrote full PNGs", W, "x", H)
    # previews
    scale = 2000 / W
    small = cv2.resize(rgb, (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(pv, "ortho-small.jpg"), cv2.cvtColor(small, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    ov = lattice_overlay(small.copy(), 0, 0, mm / scale, thick=1)
    cv2.imwrite(os.path.join(pv, "ortho-small-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    g = np.clip(gsd, 0, 40) / 40 * 255
    g = cv2.resize(g.astype(np.uint8), (2000, int(H * scale)), interpolation=cv2.INTER_AREA)
    gc = cv2.applyColorMap(g, cv2.COLORMAP_JET)
    gc[cv2.resize(obs.astype(np.uint8), (2000, int(H * scale)), interpolation=cv2.INTER_NEAREST) == 0] = 0
    cv2.imwrite(os.path.join(pv, "gsd-small.jpg"), gc)
    for c in a.crop:
        hu, hv, name = c.split(",")
        hu, hv = float(hu), float(hv)
        cx = int((hu - G.PLATE_HU[0]) * 1000 / mm)
        cy = int((hv - G.PLATE_HV[0]) * 1000 / mm)
        x0, y0 = max(0, cx - 500), max(0, cy - 500)
        x1, y1 = min(W, x0 + 1000), min(H, y0 + 1000)
        crop = rgb[y0:y1, x0:x1].copy()
        cv2.imwrite(os.path.join(pv, f"crop-{name}.jpg"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        ov = lattice_overlay(crop.copy(), x0, y0, mm)
        cv2.imwrite(os.path.join(pv, f"crop-{name}-lattice.jpg"), cv2.cvtColor(ov, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("crop", name, "px", x0, y0, "gsd median mm", float(np.median(gsd[y0:y1, x0:x1][obs[y0:y1, x0:x1]])) if obs[y0:y1, x0:x1].any() else None)
    print("previews in", pv)


if __name__ == "__main__":
    main()
