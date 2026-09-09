"""Previews, registration check and sharpness comparison for the underside orthophoto.

Three jobs, all read-only against what underside_ortho.py wrote:
  1. previews: ortho-small.jpg (2000 px wide), coverage-small.jpg (green observed / red not,
     over a dimmed ortho), and three 1000 px 1:1 crops with the drawn lattice overlaid, so any
     misregistration between the MODELLED steel and the PHOTOGRAPHED steel is visible at a glance.
  2. registration, measured two independent ways: per 2 m run of every ridge and cross member,
     the offset in mm between the drawn centreline and the photographed member (averaged profiles,
     boxcar of the member's own width); and per bay, the (hu, hv) shift that best lands the drawn
     ridge beams on the photographed dark steel. Both report how flat the objective is, because a
     flat one means the test cannot resolve the offset and its answer is noise.
  3. sharpness: Laplacian variance of this ortho against trackB/bottom-ortho-v29.png on the same
     huv rectangles, both resampled to the same 5 mm grid so the number compares like with like.

  python underside_preview.py [--source all] [--out <underside dir>]
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import underside_geom as U

V29 = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-ortho-v29.png"
V29_META = "E:/sitecapture-captures/ngv-site/agent-ref-ceiling/trackB/bottom-meta-v29.json"


def px_of(hu, hv, mm):
    return (hu - U.HU0_RASTER) * 1000.0 / mm - 0.5, (hv - U.HV0_RASTER) * 1000.0 / mm - 0.5


def huv_of(px, py, mm):
    return U.HU0_RASTER + (px + 0.5) * mm / 1000.0, U.HV0_RASTER + (py + 0.5) * mm / 1000.0


# --------------------------------------------------------------------------- lattice overlay
def draw_lattice(img, x0, y0, mm, surf, thick=1):
    """Draw the four rib families of the MODEL over a crop whose top-left pixel is (x0,y0).

    Drawn as the member's own soffit edges (two lines a half-width apart), not a centreline:
    a band that brackets the photographed member is far easier to judge than a single stripe.
    """
    h, w = img.shape[:2]
    py, px = np.mgrid[y0:y0 + h, x0:x0 + w]
    hu, hv = huv_of(px, py, mm)
    ridge, cross, hip, diag = surf.rib_dists(hu, hv)
    du, dv = surf.cell_local(hu, hv)
    tol = mm / 1000.0 * thick
    fams = [(ridge, U.RIDGE_HALF, (0, 255, 255)),    # ridge beam, yellow
            (cross, U.CROSS_HALF, (0, 255, 0)),      # cross member, green
            (hip, U.HIP_HALF, (255, 0, 255)),        # main X, magenta
            (diag, U.DIAG_HALF, (255, 128, 0))]      # edge-midpoint diamond, blue
    for d, half, col in fams:
        img[np.abs(d - half) < tol] = col
    img[np.abs(np.maximum(np.abs(du), np.abs(dv)) - U.HUB_HALF) < tol] = (255, 255, 255)
    return img


# ------------------------------------------------------------------------ registration probe
def rib_offsets(gray, mask, surf, mm, half_reach=0.6, seg_m=2.0, sample_m=0.05):
    """Signed offset (mm) of the PHOTOGRAPHED member from the DRAWN one, per rib family.

    A single profile across a member is noisy: the matrix between the slabs is nearly as dark as
    the steel, so one profile can pick the wrong dark run. This averages every profile over a 2 m
    RUN of the member first (40 profiles at 50 mm spacing, columns with any unobserved pixel
    dropped), then reads the mean profile: smooth it with a boxcar the width of the member and
    take the minimum. That is the position at which a member of the known width best explains the
    darkness, and averaging 40 profiles is what makes it a millimetre-scale reading instead of a
    guess. A member sitting exactly on the drawn line reads 0.

    The hub nodes would be the sharpest target of all, but they cannot be used: each one sits on
    a column head, and the column stands between the node and every camera on the floor.
    """
    H, W = gray.shape
    reach = int(round(half_reach * 1000 / mm))
    off = np.arange(-reach, reach + 1)
    A, B = surf.PU / 2, surf.PV / 2
    fams = {
        "ridge_across_hu": ([("hu", surf.ou + A + k * surf.PU) for k in range(-12, 12)], 2 * U.RIDGE_HALF),
        "ridge_across_hv": ([("hv", surf.ov + B + k * surf.PV) for k in range(-4, 4)], 2 * U.RIDGE_HALF),
        "cross_across_hu": ([("hu", surf.ou + k * surf.PU) for k in range(-12, 12)], 2 * U.CROSS_HALF),
        "cross_across_hv": ([("hv", surf.ov + k * surf.PV) for k in range(-4, 4)], 2 * U.CROSS_HALF),
    }
    res = {}
    for fam, (lines, width_m) in fams.items():
        wpx = max(3, int(round(width_m * 1000.0 / mm)))
        vals, where, segs = [], [], []
        for axis, c in lines:
            lo, hi = (surf.sv0 + 0.4, surf.sv1 - 0.4) if axis == "hu" else (surf.su0 + 0.4, surf.su1 - 0.4)
            if axis == "hu" and not (surf.su0 + 0.4 < c < surf.su1 - 0.4):
                continue
            if axis == "hv" and not (surf.sv0 + 0.4 < c < surf.sv1 - 0.4):
                continue
            for s0 in np.arange(lo, hi - seg_m, seg_m):
                walk = np.arange(s0, s0 + seg_m, sample_m)
                if axis == "hu":
                    hu_c, hv_c, dhu, dhv = np.full_like(walk, c), walk, 1.0, 0.0
                else:
                    hu_c, hv_c, dhu, dhv = walk, np.full_like(walk, c), 0.0, 1.0
                cx, cy = px_of(hu_c, hv_c, mm)
                # accumulate per profile COLUMN, not per whole profile: at 90 % coverage a fully
                # observed 1.4 m profile is rare, but every column of the mean profile still gets
                # plenty of real samples. A column short of samples voids the segment.
                acc = np.zeros(len(off))
                cnt = np.zeros(len(off))
                for k in range(len(walk)):
                    xs = np.round(cx[k] + off * dhu).astype(int)
                    ys = np.round(cy[k] + off * dhv).astype(int)
                    if xs.min() < 0 or xs.max() >= W or ys.min() < 0 or ys.max() >= H:
                        continue
                    m = mask[ys, xs]
                    acc[m] += gray[ys[m], xs[m]].astype(np.float64)
                    cnt[m] += 1
                if cnt.min() < 0.3 * len(walk):
                    continue
                prof = acc / cnt
                bg = float(np.percentile(prof, 85))
                if bg < 25:
                    continue
                # darkness centroid, over the reach the member could plausibly have moved to and
                # only over pixels dark enough to BE steel. On a 40-profile mean this is stable,
                # and unlike a boxcar minimum it degrades gracefully when the member is faint.
                lim = reach - wpx / 2
                sel = (np.abs(off) <= lim) & (prof < 0.72 * bg)
                if sel.sum() < 0.4 * wpx or sel.sum() > 3.0 * wpx:
                    continue                 # no member-sized dark band here, or dark everywhere
                wgt = np.clip(bg - prof, 0, None) * sel
                if wgt.sum() <= 0:
                    continue
                centre = float((wgt * off).sum() / wgt.sum())
                vals.append(centre * mm)
                where.append(float(np.mean(hu_c)))
                segs.append((float(np.mean(hu_c)), float(np.mean(hv_c)), centre * mm,
                             float(1.0 - prof[sel].mean() / bg)))
        if vals:
            vals, wh = np.array(vals), np.array(where)
            res[fam] = {"n_segments": int(len(vals)), "segment_m": seg_m,
                        "expected_width_mm": width_m * 1000,
                        "median_mm": float(np.median(vals)),
                        "mad_mm": float(np.median(np.abs(vals - np.median(vals)))),
                        "p10_mm": float(np.percentile(vals, 10)), "p90_mm": float(np.percentile(vals, 90)),
                        "by_bay_hu": {}, "examples": [{"hu": round(a, 2), "hv": round(b, 2),
                                                       "offset_mm": round(o, 0), "contrast": round(k, 2)}
                                                      for a, b, o, k in segs[:8]]}
            for i in range(int(round((surf.su1 - surf.su0) / surf.PU))):
                sel = (wh >= surf.su0 + i * surf.PU) & (wh < surf.su0 + (i + 1) * surf.PU)
                if sel.sum() >= 3:
                    res[fam]["by_bay_hu"]["i%d" % i] = {"n": int(sel.sum()),
                                                        "median_mm": float(np.median(vals[sel])),
                                                        "mad_mm": float(np.median(np.abs(vals[sel] - np.median(vals[sel]))))}
    return res


# ---------------------------------------------------------------- per-bay registration shift
def bay_shifts(gray, mask, surf, mm, search_mm=280):
    """Per bay: the (hu, hv) shift in mm that best lands the DRAWN steel on the PHOTOGRAPHED steel.

    Profile probes are fragile here because the glass matrix between the slabs is nearly as dark
    as the members. This instead asks one question of the whole bay at once: over every shift in
    a +/- search_mm window, what is the MEAN darkness of the pixels the model calls steel? The
    peak of that surface is where the drawn lattice actually sits on the photograph, and it is a
    plain weighted cross-correlation, so an FFT evaluates every shift at once.
    """
    R = int(round(search_mm / mm))
    out = {}
    nI = int(round((surf.su1 - surf.su0) / surf.PU))
    nJ = int(round((surf.sv1 - surf.sv0) / surf.PV))
    for j in range(nJ):
        for i in range(nI):
            x0, y0 = px_of(surf.su0 + i * surf.PU, surf.sv0 + j * surf.PV, mm)
            x1, y1 = px_of(surf.su0 + (i + 1) * surf.PU, surf.sv0 + (j + 1) * surf.PV, mm)
            x0, y0 = int(max(0, round(x0))), int(max(0, round(y0)))
            x1, y1 = int(min(gray.shape[1], round(x1))), int(min(gray.shape[0], round(y1)))
            if x1 - x0 < 4 * R or y1 - y0 < 4 * R:
                continue
            g = gray[y0:y1, x0:x1].astype(np.float32)
            mk = mask[y0:y1, x0:x1].astype(np.float32)
            if mk.mean() < 0.5:
                continue
            py, px = np.mgrid[y0:y1, x0:x1]
            hu, hv = huv_of(px, py, mm)
            # The whole matrix between the slabs is dark, so "darkness under the drawn steel" alone
            # is nearly flat against shift. The ridge beam is the one member wide enough (477 mm)
            # and dark enough to give a peak, and only against its own surroundings: the objective
            # is CONTRAST, mean darkness on the beam less mean darkness in the glass 0.35-0.60 m
            # to either side of it.
            ridge, _, _, _ = surf.rib_dists(hu, hv)
            Mp = (ridge < U.RIDGE_HALF).astype(np.float32)
            Mn = ((ridge > 0.35) & (ridge < 0.60)).astype(np.float32)
            bg = float(np.percentile(g[mk > 0], 85)) or 1.0
            D = np.clip(1.0 - g / max(bg, 1.0), 0, 1) * mk
            FD, FM = np.fft.rfft2(D), np.fft.rfft2(mk)
            # only the +/- R corner of the circular correlation is a small shift
            sl = (np.r_[0:R + 1, g.shape[0] - R:g.shape[0]], np.r_[0:R + 1, g.shape[1] - R:g.shape[1]])

            def corr(Mask):
                n = np.fft.irfft2(FD * np.conj(np.fft.rfft2(Mask)), s=g.shape)[np.ix_(*sl)]
                dd = np.fft.irfft2(FM * np.conj(np.fft.rfft2(Mask)), s=g.shape)[np.ix_(*sl)]
                return n, dd
            np_, dp = corr(Mp)
            nn_, dn = corr(Mn)
            ok = (dp > 0.5 * dp.max()) & (dn > 0.5 * dn.max())
            score = np.where(ok, np_ / np.maximum(dp, 1e-6) - nn_ / np.maximum(dn, 1e-6), -9)
            d2 = dp
            ky, kx = np.unravel_index(int(np.argmax(score)), score.shape)
            dv = (sl[0][ky] if sl[0][ky] <= R else sl[0][ky] - g.shape[0]) * mm
            du = (sl[1][kx] if sl[1][kx] <= R else sl[1][kx] - g.shape[1]) * mm
            zero = float(score[np.where(sl[0] == 0)[0][0], np.where(sl[1] == 0)[0][0]])
            # how much the peak beats no shift at all: a flat surface means the test cannot
            # resolve the offset, and the shift it reports is noise. Reported, not hidden.
            out["i%d_j%d" % (i, j)] = {"dhu_mm": float(du), "dhv_mm": float(dv),
                                       "peak_contrast": float(score.max()),
                                       "contrast_at_zero_shift": zero,
                                       "gain_over_zero": float(score.max() - zero),
                                       "coverage": float(mk.mean())}
    if out:
        du = np.array([v["dhu_mm"] for v in out.values()])
        dv = np.array([v["dhv_mm"] for v in out.values()])
        out["_summary"] = {"n_bays": len(du),
                           "dhu_median_mm": float(np.median(du)), "dhu_p10_p90_mm": [float(np.percentile(du, 10)), float(np.percentile(du, 90))],
                           "dhv_median_mm": float(np.median(dv)), "dhv_p10_p90_mm": [float(np.percentile(dv, 10)), float(np.percentile(dv, 90))],
                           "radial_median_mm": float(np.median(np.hypot(du, dv))),
                           "search_window_mm": search_mm}
    return out


# ------------------------------------------------------------------------------- sharpness
def lapvar(g):
    g = g.astype(np.float32)
    m = float(g.mean())
    return float(cv2.Laplacian(g, cv2.CV_32F).var() / (m * m)) if m > 1e-3 else 0.0


def v29_crop(hu0, hv0, hu1, hv1):
    meta = json.load(open(V29_META))
    im = cv2.imread(V29, cv2.IMREAD_COLOR)
    mmv = meta["mm_per_px"]
    x0 = int(round((hu0 - meta["hu0"]) * 1000 / mmv))
    x1 = int(round((hu1 - meta["hu0"]) * 1000 / mmv))
    y0 = int(round((hv0 - meta["hv0"]) * 1000 / mmv))
    y1 = int(round((hv1 - meta["hv0"]) * 1000 / mmv))
    if x0 < 0 or y0 < 0 or x1 > im.shape[1] or y1 > im.shape[0]:
        return None
    return im[y0:y1, x0:x1], mmv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="all")
    ap.add_argument("--out", default=U.OUT_ROOT)
    ap.add_argument("--crop", type=int, default=1000)
    a = ap.parse_args()
    d = os.path.join(a.out, a.source)
    prev = os.path.join(a.out, "preview", a.source)
    os.makedirs(prev, exist_ok=True)
    meta = json.load(open(os.path.join(d, "meta.json")))
    mm = meta["raster"]["mm_per_px"]
    lat = U.lattice(os.path.join(a.out, "lattice.json"))
    surf = U.Surface(lat, meta["slab_below_plate_face_m"])
    ortho = cv2.imread(os.path.join(d, "ortho.png"), cv2.IMREAD_COLOR)
    mask = cv2.imread(os.path.join(d, "mask.png"), cv2.IMREAD_GRAYSCALE) > 0
    H, W = mask.shape
    gray = cv2.cvtColor(ortho, cv2.COLOR_BGR2GRAY)
    out = {"source": a.source, "raster": meta["raster"]}

    # 1. the two small sheets
    sc = 2000.0 / W
    small = cv2.resize(ortho, (2000, int(round(H * sc))), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(prev, "ortho-small.jpg"), small, [cv2.IMWRITE_JPEG_QUALITY, 92])
    cov = (small * 0.45).astype(np.uint8)
    ms = cv2.resize(mask.astype(np.uint8) * 255, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
    py, px = np.mgrid[0:small.shape[0], 0:small.shape[1]]
    hu, hv = huv_of(px / sc, py / sc, mm)
    plate = surf.in_plate(hu, hv)
    cov[..., 1] = np.where(plate, np.maximum(cov[..., 1], ms), cov[..., 1])
    cov[..., 2] = np.where(plate & (ms < 128), 190, cov[..., 2])
    cv2.imwrite(os.path.join(prev, "coverage-small.jpg"), cov, [cv2.IMWRITE_JPEG_QUALITY, 92])

    # 2. three 1:1 crops on funnel vertices, west / middle / east, with the lattice drawn
    c = a.crop
    picks = []
    for i in (1, 3, 6):
        # centre each crop on a funnel vertex: the cross members, the main X, the diamond and the
        # hub node all meet there, so one look tells you whether the model sits on the photograph
        hu_c = surf.ou + surf.PU * round((surf.su0 + surf.PU * (i + 0.5) - surf.ou) / surf.PU)
        hv_c = surf.ov + surf.PV * round((surf.sv0 + surf.PV * 0.5 - surf.ov) / surf.PV)
        x, y = px_of(hu_c, hv_c, mm)
        x0 = int(np.clip(x - c / 2, 0, W - c))
        y0 = int(np.clip(y - c / 2, 0, H - c))
        picks.append((("west", "middle", "east")[len(picks)], x0, y0))
    out["crops"] = []
    for name, x0, y0 in picks:
        crop = ortho[y0:y0 + c, x0:x0 + c].copy()
        cv2.imwrite(os.path.join(prev, "crop-%s.jpg" % name), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(prev, "crop-%s-lattice.jpg" % name),
                    draw_lattice(crop.copy(), x0, y0, mm, surf), [cv2.IMWRITE_JPEG_QUALITY, 95])
        hu0, hv0 = huv_of(x0, y0, mm)
        hu1, hv1 = huv_of(x0 + c, y0 + c, mm)
        rec = {"name": name, "px": [x0, y0, c, c], "huv": [hu0, hv0, hu1, hv1],
               "coverage": float(mask[y0:y0 + c, x0:x0 + c].mean()),
               "lapvar_underside_at_5mm": None, "lapvar_v29_at_5mm": None}
        v = v29_crop(hu0, hv0, hu1, hv1)
        if v is not None:
            vim, mmv = v
            cv2.imwrite(os.path.join(prev, "crop-%s-v29.jpg" % name), vim, [cv2.IMWRITE_JPEG_QUALITY, 95])
            # compare on the SAME grid: bring this ortho down to the v29 sampling, not the reverse
            un = cv2.resize(crop, (vim.shape[1], vim.shape[0]), interpolation=cv2.INTER_AREA)
            mk = cv2.resize(mask[y0:y0 + c, x0:x0 + c].astype(np.uint8), (vim.shape[1], vim.shape[0]),
                            interpolation=cv2.INTER_AREA) > 0
            if mk.mean() > 0.85:
                rec["lapvar_underside_at_5mm"] = lapvar(cv2.cvtColor(un, cv2.COLOR_BGR2GRAY))
                rec["lapvar_v29_at_5mm"] = lapvar(cv2.cvtColor(vim, cv2.COLOR_BGR2GRAY))
                rec["sharper_by"] = (rec["lapvar_underside_at_5mm"] / rec["lapvar_v29_at_5mm"]
                                     if rec["lapvar_v29_at_5mm"] else None)
        out["crops"].append(rec)

    # 3. the registration numbers
    out["bay_shift_mm"] = bay_shifts(gray, mask, surf, mm, search_mm=160)
    out["registration_mm"] = rib_offsets(gray, mask, surf, mm)
    json.dump(out, open(os.path.join(prev, "report-%s.json" % a.source), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("crops", "registration_mm")}, indent=1))


if __name__ == "__main__":
    main()
