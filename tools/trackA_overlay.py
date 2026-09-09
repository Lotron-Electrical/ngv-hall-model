"""Project the canopy lattice (bay edges, sub-square cross, diagonals, funnel vertices) into
void4k stills through a void->hall chain and draw it on a downsized copy, to check alignment.

python trackA_overlay.py <chain a|b|c|d> <outdir> v028 v045 ...  [--corr fit.json]
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

MAPPED = "E:/sitecapture-captures/ngv-video/void4k-register/mapped"
IMG = "E:/sitecapture-captures/ngv-video/void4k-register/images/void4k/"


def lattice_lines(step=0.05):
    """List of (kind, pts(N,2) huv) polylines covering the plate."""
    lines = []
    hu_lo, hu_hi = G.PLATE_HU
    hv_lo, hv_hi = G.PLATE_HV
    # bay edge ridges (crest rings): hu = HU0 + (i+0.5)PU, hv = HV0 + (j+0.5)PV
    for i in range(-2, 7):
        hu = G.HU0 + (i + 0.5) * G.PU
        if hu_lo - 0.1 <= hu <= hu_hi + 0.1:
            hv = np.arange(hv_lo, hv_hi + step, step)
            lines.append(("edge", np.stack([np.full_like(hv, hu), hv], 1)))
    for j in range(-2, 2):
        hv = G.HV0 + (j + 0.5) * G.PV
        if hv_lo - 0.1 <= hv <= hv_hi + 0.1:
            hu = np.arange(hu_lo, hu_hi + step, step)
            lines.append(("edge", np.stack([hu, np.full_like(hu, hv)], 1)))
    # sub-square cross through the vertices
    for i in range(-1, 6):
        hu = G.HU0 + i * G.PU
        hv = np.arange(hv_lo, hv_hi + step, step)
        lines.append(("cross", np.stack([np.full_like(hv, hu), hv], 1)))
    for j in range(-1, 1):
        hv = G.HV0 + j * G.PV
        hu = np.arange(hu_lo, hu_hi + step, step)
        lines.append(("cross", np.stack([hu, np.full_like(hu, hv)], 1)))
    # diagonals of each bay (main X through the vertex) and anti-diagonal diamond
    for i in range(-1, 6):
        for j in range(-1, 1):
            cu, cv = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            a, b = G.PU / 2, G.PV / 2
            s = np.linspace(-1, 1, int(2 * a / step))
            lines.append(("diag", np.stack([cu + s * a, cv + s * b], 1)))
            lines.append(("diag", np.stack([cu + s * a, cv - s * b], 1)))
            s2 = np.linspace(0, 1, int(a / step))
            for su, sv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                lines.append(("anti", np.stack([cu + su * a * s2, cv + sv * b * (1 - s2)], 1)))
    return lines


COL = {"edge": (255, 0, 0), "cross": (0, 200, 255), "diag": (255, 220, 0), "anti": (0, 255, 80)}


def draw_overlay(cam, img_path, out_path, corr=None, scale=0.25, slab=0.06, ridge_up=0.0):
    im = Image.open(img_path)
    im = im.resize((int(im.width * scale), int(im.height * scale)))
    dr = ImageDraw.Draw(im)
    for kind, pts in lattice_lines():
        hu, hv = pts[:, 0], pts[:, 1]
        if corr is not None:
            hu, hv = corr(hu, hv)
        X = G.surface_xyz(hu, hv, slab)
        u, v, z = cam.project(X)
        # camera-to-point distance limit and inside test
        d = np.linalg.norm(X - cam.center, axis=1)
        ok = cam.inside(u, v, z, margin=-200) & (d < 40)
        # also require the point in front by a decent angle (avoid wrap of distorted rays)
        Xc = X @ cam.R.T + cam.t
        ok &= Xc[:, 2] > 0.3 * np.linalg.norm(Xc, axis=1)
        u, v = u * scale, v * scale
        for k in range(len(u) - 1):
            if ok[k] and ok[k + 1]:
                dr.line([(u[k], v[k]), (u[k + 1], v[k + 1])], fill=COL[kind], width=2)
    # funnel vertices + crest corners
    for i in range(-1, 6):
        for j in range(-1, 1):
            hu, hv = G.HU0 + i * G.PU, G.HV0 + j * G.PV
            if corr is not None:
                hu, hv = corr(np.array([hu]), np.array([hv]))
                hu, hv = float(hu[0]), float(hv[0])
            X = G.surface_xyz(np.array([hu]), np.array([hv]), slab)
            u, v, z = cam.project(X)
            Xc = X @ cam.R.T + cam.t
            if z[0] > 0 and Xc[0, 2] > 0.3 * np.linalg.norm(Xc[0]) and 0 <= u[0] < cam.w and 0 <= v[0] < cam.h:
                uu, vv = u[0] * scale, v[0] * scale
                dr.ellipse([uu - 6, vv - 6, uu + 6, vv + 6], outline=(255, 0, 255), width=3)
                dr.text((uu + 8, vv - 8), f"V{i},{j}", fill=(255, 0, 255))
    im.save(out_path, quality=88)
    return im


def make_corr(path):
    j = json.load(open(path))
    s, th, tu, tv = j["s"], np.radians(j["theta_deg"]), j["tu"], j["tv"]
    cu, cv = j["about"]

    def corr(hu, hv):
        du, dv = hu - cu, hv - cv
        c, sn = np.cos(th), np.sin(th)
        return cu + s * (c * du - sn * dv) + tu, cv + s * (sn * du + c * dv) + tv
    return corr


if __name__ == "__main__":
    chain = sys.argv[1]
    outdir = sys.argv[2]
    names = [a for a in sys.argv[3:] if a.startswith("v") and len(a) == 4]
    corr = None
    if "--corr" in sys.argv:
        corr = make_corr(sys.argv[sys.argv.index("--corr") + 1])
    os.makedirs(outdir, exist_ok=True)
    if "--sim" in sys.argv:
        sim = G.load_sim(sys.argv[sys.argv.index("--sim") + 1])
        chain = os.path.basename(sys.argv[sys.argv.index("--sim") + 1])[:-5]
    else:
        sim = G.void_to_hall_chain(chain)
    cams = G.load_stills(MAPPED, sim)
    for n in names:
        cam = cams[n]
        out = os.path.join(outdir, f"{n}_chain{chain}{'_corr' if corr else ''}.jpg")
        draw_overlay(cam, IMG + n + ".jpg", out, corr)
        c = cam.center
        hu, hv = G.xz_to_huv(c[0], c[2])
        print(n, "cam hall xyz", c.round(3), "huv", round(float(hu), 3), round(float(hv), 3), "height above surface", round(float(c[1] - G.surface_y(np.array([hu]), np.array([hv]))[0]), 3), "->", out)
