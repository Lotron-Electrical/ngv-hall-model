"""Track A step 2b: fit the canopy lattice (inverted-pyramid relief) to the void-frame dense heightmap.

Model: H10(x,z) ~ a*x + b*z + c + relief(hu,hv),  (hu,hv) = s*R(theta)*(x,z) + (tu,tv)
with relief() the index.html coffRelief (0.86 m rise, PU x PV module) in the huv plate frame.
The huv frame here is 'lattice-locked' only: which bay is which (180 deg flip + whole-bay shifts) is
decided later (trackA_orient.py). This script fixes theta, s, tu, tv (mod the lattice symmetry)
and the void-frame plane, and writes <scratch>/trackA/lattice_fit.json.

python trackA_fit.py
"""
import sys, os, json
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trackA_geom as G

SCR = "C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs/046860d0-c13c-4e5d-847c-7ad01cef102a/scratchpad/trackA/"


def relief_phase(pu, pv):
    """relief as a function of the phase offset from the nearest vertex (pu,pv in [0,PU)x[0,PV))."""
    du = pu - G.PU * np.round(pu / G.PU)   # offset from the nearest vertex (vertex at phase 0)
    dv = pv - G.PV * np.round(pv / G.PV)
    a = G.PU / 2 - 0.225
    b = G.PV / 2 - 0.225
    t = np.maximum(np.abs(du) / a, np.abs(dv) / b)
    over = np.maximum(np.abs(du) - a, np.abs(dv) - b)
    return np.where(t <= 1, G.RISE * t, G.RISE - 0.03 * np.minimum(1.0, over / 0.225))


def main():
    z = np.load(SCR + "void_dense_heightmap.npz")
    H, N, x0, z0, cell = z["H10"], z["N"], float(z["x0"]), float(z["z0"]), float(z["cell"])
    nz, nx = H.shape
    iz, ix = np.nonzero(N >= 3)
    x = x0 + (ix + 0.5) * cell
    zz = z0 + (iz + 0.5) * cell
    h = H[iz, ix]
    print("cells", len(h))
    # mean plane (least squares), then drop the deck / beam-top cells above plane+0.40
    A = np.stack([x, zz, np.ones_like(x)], 1)
    for it in range(3):
        coef, *_ = np.linalg.lstsq(A, h, rcond=None)
        res = h - A @ coef
        keep = (res > -1.0) & (res < 0.40)
        A, x, zz, h = A[keep], x[keep], zz[keep], h[keep]
    print("plane a,b,c", coef, "kept cells", len(h), "tilt deg", np.degrees(np.arctan(np.hypot(coef[0], coef[1]))))
    d = h - A @ coef  # detrended heights

    # ---- coarse search: theta in [0,90) step 0.25 deg, s in 0.97..1.05
    nb_u, nb_v = 74, 74
    pu_axis = (np.arange(nb_u) + 0.5) * G.PU / nb_u
    pv_axis = (np.arange(nb_v) + 0.5) * G.PV / nb_v
    T = relief_phase(pu_axis[None, :], pv_axis[:, None])  # (nb_v, nb_u), phase (0,0) = vertex at bin 0
    T = T - T.mean()
    best = None
    dd = d - d.mean()
    for s in np.arange(0.97, 1.0501, 0.005):
        for th in np.arange(0, 90, 0.25):
            c, sn = np.cos(np.radians(th)), np.sin(np.radians(th))
            hu = s * (c * x - sn * zz)
            hv = s * (sn * x + c * zz)
            bu = np.floor((hu % G.PU) / G.PU * nb_u).astype(int)
            bv = np.floor((hv % G.PV) / G.PV * nb_v).astype(int)
            key = bv * nb_u + bu
            S = np.bincount(key, weights=dd, minlength=nb_u * nb_v)
            C = np.bincount(key, minlength=nb_u * nb_v)
            M = np.where(C > 0, S / np.maximum(C, 1), 0.0).reshape(nb_v, nb_u)
            W = (C > 0).reshape(nb_v, nb_u).astype(float)
            # circular cross-correlation of M with T over the phase grid
            F = np.fft.ifft2(np.fft.fft2(M) * np.conj(np.fft.fft2(T))).real
            # normalise by template energy over observed bins (approx: use global norm)
            score = F / (np.sqrt((M ** 2).sum() * (T ** 2).sum()) + 1e-9)
            k = np.argmax(score)
            kv, ku = divmod(k, nb_u)
            if best is None or score.flat[k] > best[0]:
                best = (float(score.flat[k]), s, th, ku, kv)
    sc, s, th, ku, kv = best
    # phase: the template vertex (bin 0) matches heightmap phase bin (ku,kv): relief(hu - tu0) with
    # tu0 = ku*PU/nb_u; i.e. vertices sit at hu = tu0 + i*PU. We want hu_lattice = hu - tu0 + HU0.
    tu = G.HU0 - ku * G.PU / nb_u
    tv = G.HV0 - kv * G.PV / nb_v
    print(f"coarse: ncc {sc:.3f} s {s:.3f} theta {th:.2f} tu {tu:.3f} tv {tv:.3f}")

    # ---- refine: least squares on cells, params theta, s, tu, tv, a, b, c
    def model(p, x, zz):
        th, s, tu, tv, a, b, c = p
        cth, sth = np.cos(th), np.sin(th)
        hu = s * (cth * x - sth * zz) + tu
        hv = s * (sth * x + cth * zz) + tv
        return a * x + b * zz + c + G.relief(hu, hv), hu, hv

    def resid(p):
        m, _, _ = model(p, x, zz)
        return m - h

    p0 = np.array([np.radians(th), s, tu, tv, coef[0], coef[1], coef[2]])
    r0 = resid(p0)
    print("initial resid rms", np.sqrt(np.mean(r0 ** 2)), "median abs", np.median(np.abs(r0)))
    fit = least_squares(resid, p0, loss="soft_l1", f_scale=0.05, max_nfev=200)
    p = fit.x
    r = resid(p)
    inl = np.abs(r) < 0.10
    print("refined: theta %.4f deg s %.5f tu %.4f tv %.4f plane %s" % (np.degrees(p[0]), p[1], p[2], p[3], p[4:]))
    print("resid rms all %.4f, median abs %.4f, inlier(<10cm) frac %.3f, inlier rms %.4f" % (
        np.sqrt(np.mean(r ** 2)), np.median(np.abs(r)), inl.mean(), np.sqrt(np.mean(r[inl] ** 2))))
    # second pass on inliers only
    x2, z2, h2 = x[inl], zz[inl], h[inl]

    def resid2(pp):
        m, _, _ = model(pp, x2, z2)
        return m - h2
    fit2 = least_squares(resid2, p, loss="soft_l1", f_scale=0.03, max_nfev=200)
    p = fit2.x
    r2 = resid2(p)
    print("pass2: theta %.4f deg s %.5f tu %.4f tv %.4f plane %s" % (np.degrees(p[0]), p[1], p[2], p[3], p[4:]))
    print("pass2 resid rms %.4f median abs %.4f" % (np.sqrt(np.mean(r2 ** 2)), np.median(np.abs(r2))))
    m, hu, hv = model(p, x, zz)
    # lattice extents covered
    bi, bj = G.bay_index(hu, hv)
    print("hu range", hu.min(), hu.max(), "hv range", hv.min(), hv.max())
    print("vertex index i range", np.round((hu.min() - G.HU0) / G.PU, 2), np.round((hu.max() - G.HU0) / G.PU, 2),
          "j range", np.round((hv.min() - G.HV0) / G.PV, 2), np.round((hv.max() - G.HV0) / G.PV, 2))
    # per-bay cell counts and residuals
    bays = {}
    for i in range(int(bi.min()), int(bi.max()) + 1):
        for j in range(int(bj.min()), int(bj.max()) + 1):
            mk = (bi == i) & (bj == j)
            if mk.sum() > 50:
                rr = (m - h)[mk]
                bays[f"{i},{j}"] = {"cells": int(mk.sum()), "area_m2": float(mk.sum() * cell * cell),
                                    "rms_m": float(np.sqrt(np.mean(rr ** 2))), "medabs_m": float(np.median(np.abs(rr)))}
    for k, v in sorted(bays.items()):
        print("  bay", k, v)
    out = {
        "note": "void frame (x,z) -> lattice-locked huv: hu = s*(cos th*x - sin th*z) + tu, hv = s*(sin th*x + cos th*z) + tv; "
                "vertex plane in void frame y = a*x + b*z + c (relief added above it). Discrete symmetry NOT yet resolved.",
        "theta_rad": float(p[0]), "theta_deg": float(np.degrees(p[0])), "s": float(p[1]), "tu": float(p[2]), "tv": float(p[3]),
        "plane_abc": [float(v) for v in p[4:]],
        "coarse": {"ncc": sc, "s": float(s), "theta_deg": float(th)},
        "resid": {"rms_all": float(np.sqrt(np.mean(r ** 2))), "median_abs": float(np.median(np.abs(r))),
                  "inlier_frac_10cm": float(inl.mean()), "pass2_rms": float(np.sqrt(np.mean(r2 ** 2)))},
        "hu_range": [float(hu.min()), float(hu.max())], "hv_range": [float(hv.min()), float(hv.max())],
        "bays": bays,
    }
    json.dump(out, open(SCR + "lattice_fit.json", "w"), indent=1)
    # residual image for inspection
    from PIL import Image
    R = np.full(H.shape, np.nan)
    ix2 = np.round((x - x0) / cell - 0.5).astype(int)
    iz2 = np.round((zz - z0) / cell - 0.5).astype(int)
    R[iz2, ix2] = m - h
    img = np.where(np.isnan(R), 0, np.clip(R / 0.15 * 127 + 128, 1, 255)).astype(np.uint8)
    Image.fromarray(img).save(SCR + "lattice_fit_resid.png")
    print("wrote", SCR + "lattice_fit.json", "and lattice_fit_resid.png (grey 128 = 0, +-0.15 m full scale)")


if __name__ == "__main__":
    main()
