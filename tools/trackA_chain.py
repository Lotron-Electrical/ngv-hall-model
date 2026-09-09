"""Track A step 2c: turn the lattice fit (void frame -> lattice-locked huv) into a full 3D similarity
void -> hall for one discrete option (whole-bay shift along hu, optional 180 deg flip about the
plate centre), and write it in the site's transform-json shape:
  {"transform": {"scale": s, "R": [[..]], "t": [..]}}   x_hall = s*R@x_void + t

python trackA_chain.py --shift_i 1 --flip 0 --out <path.json>
"""
import sys, os, json, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"
HU_C = (G.PLATE_HU[0] + G.PLATE_HU[1]) / 2   # -30.635375 (vertex i=2)
HV_C = (G.PLATE_HV[0] + G.PLATE_HV[1]) / 2   # 7.54432 (between the two vertex rows)


def umeyama(src, dst):
    """similarity dst ~ s*R@src + t (Umeyama 1991)."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S, D = src - mu_s, dst - mu_d
    cov = D.T @ S / len(src)
    U, sig, Vt = np.linalg.svd(cov)
    d = np.ones(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        d[2] = -1
    R = U @ np.diag(d) @ Vt
    var_s = (S ** 2).sum() / len(src)
    s = (sig * d).sum() / var_s
    t = mu_d - s * R @ mu_s
    return s, R, t


def fit_to_plate_huv(fit, x, z, shift_i=0, flip=0):
    th, s, tu, tv = fit["theta_rad"], fit["s"], fit["tu"], fit["tv"]
    c, sn = np.cos(th), np.sin(th)
    hu = s * (c * x - sn * z) + tu
    hv = s * (sn * x + c * z) + tv
    if flip:
        hu, hv = 2 * HU_C - hu, 2 * HV_C - hv
    hu = hu + shift_i * G.PU
    return hu, hv


def build(fit, shift_i, flip):
    a, b, c = fit["plane_abc"]
    # synthetic correspondences on the vertex plane over the fitted coverage
    xs = np.linspace(-6, 16, 23)
    zs = np.linspace(-36, 14, 51)
    X, Z = np.meshgrid(xs, zs)
    X, Z = X.ravel(), Z.ravel()
    Y = a * X + b * Z + c
    hu, hv = fit_to_plate_huv(fit, X, Z, shift_i, flip)
    hx, hz = G.huv_to_xz(hu, hv)
    hy = G.vertex_plane_y(hu, hv)
    src = np.stack([X, Y, Z], 1)
    dst = np.stack([hx, hy, hz], 1)
    s, R, t = umeyama(src, dst)
    res = np.linalg.norm(G.apply_sim((s, R, t), src) - dst, axis=1)
    return (s, R, t), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shift_i", type=int, default=1)
    ap.add_argument("--flip", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--fit", default=SCR + "lattice_fit.json")
    a = ap.parse_args()
    fit = json.load(open(a.fit))
    sim, res = build(fit, a.shift_i, a.flip)
    s, R, t = sim
    print(f"shift_i {a.shift_i} flip {a.flip}: scale {s:.6f} det {np.linalg.det(R):.4f} umeyama resid max {res.max()*1000:.3f} mm")
    print("R", np.array2string(R, precision=6), "t", t.round(4))
    # where the 4K spot is
    cams = G.load_stills("E:/sitecapture-captures/ngv-video/void4k-register/mapped", sim)
    C = np.array([c.center for c in cams.values()])
    cm = C.mean(0)
    hu, hv = G.xz_to_huv(cm[0], cm[2])
    bi, bj = G.bay_index(np.array([hu]), np.array([hv]))
    print("4K spot mean hall xyz", cm.round(3), "huv", round(float(hu), 3), round(float(hv), 3), "bay", int(bi[0]), int(bj[0]),
          "height above plate surface", round(float(cm[1] - G.surface_y(np.array([hu]), np.array([hv]), 0.0)[0]), 3))
    # 12 column heads -> void frame: report their (x,z) and how far from a lattice vertex in the fit
    cols = np.array([(-46.577, 1.119, 11.432), (-39.518, 2.665, 11.410), (-32.373, 4.272, 11.401), (-25.166, 5.976, 11.398),
                     (-17.817, 7.557, 11.382), (-10.648, 9.210, 11.380), (-45.097, -6.326, 11.513), (-37.948, -4.598, 11.497),
                     (-30.828, -3.040, 11.495), (-23.268, -1.157, 11.485), (-16.486, -0.019, 11.522), (-9.315, 1.858, 11.516)])
    cols = cols[:, [0, 2, 1]]   # given as (x, z, top y) -> (x, y, z)
    inv = G.invert_sim(sim)
    cv = G.apply_sim(inv, cols)
    print("column heads in void frame (x,y,z):")
    for c0, v in zip(cols, cv):
        print("  hall", c0, "-> void", v.round(3))
    out = {
        "schema": "sitecapture.roofvoid-to-hall/1",
        "written_by": "trackA_chain.py (lattice fit of the dense void heightmap to the canopy relief; discrete option below)",
        "source_frame": "void register frame (rebuild-roofvoid/build/model == void4k-register/mapped)",
        "target_frame": "hall / GLB world of model.glb (metres, y up)",
        "transform": {"note": "x_hall = scale * R @ x_void + t, metres", "scale": float(s), "R": R.tolist(), "t": t.tolist()},
        "discrete_option": {"shift_i_bays": a.shift_i, "flip180": bool(a.flip)},
        "lattice_fit": fit,
        "umeyama_resid_max_mm": float(res.max() * 1000),
        "spot_4k": {"hall_xyz": cm.tolist(), "hu": float(hu), "hv": float(hv), "bay": [int(bi[0]), int(bj[0])]},
    }
    path = a.out or SCR + f"void-to-hall-trackA-s{a.shift_i}f{a.flip}.json"
    json.dump(out, open(path, "w"), indent=1)
    print("wrote", path)


if __name__ == "__main__":
    main()
