# 2026-09-09: THE END GALLERIES' LIGHT FITTINGS TRIANGULATED, and with them the height of whatever
# they are mounted in.
#
# The corridor gave up its geometry to a lamp when it would give up nothing to a surface, and the reason
# generalises: a bright point survives a bad exposure, a small image and a steep angle, and two rays fix
# it outright. The end galleries have the same problem the corridor had. Nothing on them is measured from
# a camera standing on the deck, because the 179 deck frames all point out at the hall, and the soffit
# over them refused three separate instruments this afternoon. But their fittings are visible from the
# HALL FLOOR, thirty metres back, where the whole gallery opening is in frame and the baseline between
# frames is tens of metres.
#
# WHAT THIS CAN SETTLE THAT THE SOFFIT INSTRUMENTS COULD NOT. A downlight recessed in a soffit sits AT
# the soffit. So a lamp that triangulates under the gallery ceiling measures the ceiling, without ever
# looking for the ceiling. The gallery's open face is used only to decide where in each picture to look;
# nothing about the deck, the soffit or the back wall enters the arithmetic, and every point is free to
# land outside the drawn gallery, which is how the result can refuse itself.
#
# Points are found one at a time: the best-supported cluster of rays is taken, its rays are removed, and
# the search repeats until fewer than four rays agree on anything. The alternative, one point per opening,
# would report the brightest fitting and silently hide the rest.
#   python tools/gallery_lamp.py [west|east|both]
import io
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FACE, DECK, TOP, DSOUTH, SOFFIT = 3.85, 8.34, 13.5, 15.364, 2.1
ENDS = {'west': (0.344, -1.0), 'east': (51.906, 1.0)}
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b5', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp')
TOL = 0.12          # metres: how close a ray must pass to count as seeing the same fitting
MINRAYS = 4
MINBASE = 1.0


def face_quad(cam, uF, hlo, hhi):
    """the gallery's open face projected into this picture, or None if it is not usefully in frame"""
    corners = np.array([O + uF * HU + dd * HD + np.array([0, vv, 0])
                        for dd, vv in ((0.2, hlo), (DSOUTH - 0.2, hlo), (DSOUTH - 0.2, hhi), (0.2, hhi))])
    x, y, z = cam.project(corners)
    if np.any(z <= 0.5):
        return None
    q = np.stack([x, y], 1)
    if q[:, 0].max() - q[:, 0].min() < 60 or q[:, 1].max() - q[:, 1].min() < 25:
        return None
    if q[:, 0].max() < 20 or q[:, 1].max() < 20 or q[:, 0].min() > cam.w - 20 or q[:, 1].min() > cam.h - 20:
        return None
    return q


def blobs(cam, img, q):
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, np.round(q).astype(np.int32), 255)
    mask = cv2.erode(mask, np.ones((5, 5), np.uint8))
    if int(mask.sum()) // 255 < 400:
        return []
    vals = img[mask > 0].astype(np.float32)
    thr = float(vals.mean() + 4.0 * vals.std())
    if thr > 250 or float(vals.max()) < thr:
        return []
    hot = np.logical_and(img.astype(np.float32) > thr, mask > 0).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(hot, 8)
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    out = []
    for k in range(1, n):
        area = int(stats[k, cv2.CC_STAT_AREA])
        if area < 3 or area > 3000:
            continue
        cx, cy = float(cent[k, 0]), float(cent[k, 1])
        un = cv2.undistortPoints(np.array([[[cx, cy]]], np.float64), K, dist.reshape(1, -1))[0, 0]
        v = cam.R.T @ np.array([float(un[0]), float(un[1]), 1.0])
        out.append((cam.center.copy(), v / np.linalg.norm(v)))
    return out


def closest_point(bundle):
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for C, v in bundle:
        M = np.eye(3) - np.outer(v, v)
        A += M
        b += M @ C
    return np.linalg.solve(A, b)


def miss(P, C, v):
    w = P - C
    return float(np.linalg.norm(w - (w @ v) * v))


def run(end, cams):
    uB, s = ENDS[end]
    uF = uB - s * FACE
    # THE BAND IS A PARAMETER NOW, and it used to be the upper gallery and nothing else (2026-09-10).
    # DECK to TOP is the upper gallery's open face. The LOWER tier, which the clips read as a deep unlit
    # recess set back behind the parapet, was never searched by this instrument at all, and a recess is
    # exactly what a triangulated point can measure when a plane cannot: a lamp fixes u, d and h at once
    # with no assumption about which surface it sits on. HLO and HHI aim the same audited search at it.
    hlo = float(os.environ.get('HLO', DECK))
    hhi = float(os.environ.get('HHI', TOP))
    rays = []
    for f, (cls, cam, ip) in cams.items():
        qc = cam.center - O
        cu, cd = float(qc @ HU), float(qc @ HD)
        if cd < 1.0:
            continue
        if abs(cu - uB) > 34.0 or (s > 0 and cu > uF) or (s < 0 and cu < uF):
            continue                       # out in the hall, on the hall side of this gallery's face
        q = face_quad(cam, uF, hlo, hhi)
        if q is None:
            continue
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        for r in blobs(cam, cv2.GaussianBlur(img, (3, 3), 0), q):
            rays.append((f,) + r)
    print('')
    print(end.upper(), 'gallery: face on u %.3f, back wall on u %.3f' % (uF, uB))
    print('   %d blobs from %d frames inside the gallery face' % (len(rays), len(set(r[0] for r in rays))))
    if len(rays) < MINRAYS:
        return []
    found = []
    pool = list(rays)
    rng = np.random.default_rng(20260909)
    # A LIT GALLERY FACE IS FULL OF BRIGHT SPOTS, thousands of them across the archive, and every pair of
    # them was being tried against every ray: the first run of this was still going after ten minutes with
    # nothing printed. The pair list is therefore SAMPLED, with a fixed seed so the run is repeatable, and
    # the inlier test is vectorised. Sampling costs recall on a fitting only a couple of rays ever saw,
    # which is a fitting that would have been refused anyway.
    TRIES = 6000
    for _ in range(12):
        if len(pool) < MINRAYS:
            break
        C = np.array([r[1] for r in pool])
        V = np.array([r[2] for r in pool])
        best = None
        ii = rng.integers(0, len(pool), TRIES)
        jj = rng.integers(0, len(pool), TRIES)
        for a, b in zip(ii, jj):
            if a == b or np.linalg.norm(C[a] - C[b]) < MINBASE:
                continue
            P = closest_point([pool[a][1:], pool[b][1:]])
            W = P - C
            dd = np.linalg.norm(W - (np.einsum('ij,ij->i', W, V))[:, None] * V, axis=1)
            k = int((dd < TOL).sum())
            if best is None or k > len(best[1]):
                best = (P, [pool[m] for m in np.where(dd < TOL)[0]])
        if best is None or len(best[1]) < MINRAYS:
            break
        P = closest_point([r[1:] for r in best[1]])
        for _ in range(3):
            inl = [r for r in pool if miss(P, r[1], r[2]) < TOL]
            if len(inl) < MINRAYS:
                break
            P = closest_point([r[1:] for r in inl])
        inl = [r for r in pool if miss(P, r[1], r[2]) < TOL]
        if len(inl) < MINRAYS:
            break
        qq = P - O
        pu, pd, ph = float(qq @ HU), float(qq @ HD), float(P[1] - O[1])
        cs = np.array([r[1] for r in inl])
        spread = float(np.linalg.norm(cs.max(0) - cs.min(0)))
        rms = float(np.sqrt(np.mean([miss(P, r[1], r[2]) ** 2 for r in inl])))
        inside = (min(uF, uB) - 0.15 <= pu <= max(uF, uB) + 0.15) and (hlo - 0.2 < ph < hhi)
        print('   u %7.3f  d %6.3f  h %6.3f   %2d rays, %.3f m rms, cameras %5.1f m apart   %s'
              % (pu, pd, ph, len(inl), rms, spread, 'in the gallery' if inside else 'OUTSIDE it, dropped'))
        # THE SPLIT THAT TESTS A POINT IS NOT NEAR AGAINST FAR (tools/lamp_v.py, 2026-09-09). A point's
        # DEPTH is fixed by the angular spread of the rays, so the halves that disagree about a wrong depth
        # are the cameras WEST of it against the cameras EAST of it: a depth error moves the apparent
        # station one way for one half and the other way for the other. Two halves that land together have
        # agreed about the depth from genuinely different directions.
        # AN END LAMP CANNOT BE SPLIT WEST AGAINST EAST, and that had to be found rather than assumed
        # (2026-09-10). lamp_v.py established that a point's depth is tested by the halves that see it
        # from opposite directions ALONG the depth axis. At an end, the depth axis is u and every camera
        # in the archive stands on the hall side of it: the first run of this split reported "0 rays west
        # of it" for every end fitting. The axis that does have two sides here is d, the hall's own width,
        # 15.4 m of it, so the halves are the cameras SOUTH of the point against those NORTH of it. A
        # wrong u swings the apparent point across d in opposite senses for the two halves, so the test
        # still bites; it is simply run on the baseline this archive actually has.
        cd_in = np.array([float((r[1] - O) @ HD) for r in inl])
        cut = float(np.median(cd_in))
        lo = [r for r, v in zip(inl, cd_in) if v < cut]
        hi2 = [r for r, v in zip(inl, cd_in) if v >= cut]
        if len(lo) >= 2 and len(hi2) >= 2:
            Pl, Ph = closest_point([r[1:] for r in lo]), closest_point([r[1:] for r in hi2])
            ql, qh = Pl - O, Ph - O
            print('        south half (%d rays) u %.3f d %.3f h %.3f   north half (%d rays) u %.3f d %.3f'
                  ' h %.3f   apart by %.3f in u, %.3f in h'
                  % (len(lo), ql @ HU, ql @ HD, ql[1], len(hi2), qh @ HU, qh @ HD, qh[1],
                     abs(float(ql @ HU) - float(qh @ HU)), abs(float(ql[1]) - float(qh[1]))))
        else:
            print('        one-sided in d as well (%d against %d), so its depth is not tested'
                  % (len(lo), len(hi2)))
        if inside and os.environ.get('DUMP'):
            # the kept fitting AND the rays that found it, so a second tool can sweep the space those rays
            # crossed. A bound that lives only in a printout cannot be checked by the suite.
            import json
            rec = {'end': end, 'u': pu, 'd': pd, 'h': ph, 'rms': rms, 'spread': spread, 'uF': uF,
                   'uB': uB, 'rays': [[list(r[1]), list(r[2]), r[0]] for r in inl]}
            with io.open(os.environ['DUMP'], 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(rec) + '\n')
        if inside:
            # AND THE OCCLUSION BOUND, which is the part that finally constrains the soffit. Every one of
            # these rays reached a fitting standing INSIDE the gallery, so nothing blocked it, so the
            # ceiling over the deck cannot hang below the height where that ray crossed the gallery's own
            # face plane. A soffit lower or deeper than that would have hidden the lamp from the hall
            # floor, and it plainly did not. This is a bound rather than a reading, and unlike the three
            # instruments that failed on this edge it needs no boundary to be found in any picture.
            cross = []
            for r in inl:
                Cc, vv = r[1], r[2]
                du = float(vv @ HU)
                if abs(du) < 1e-6:
                    continue
                tt = (uF - float((Cc - O) @ HU)) / du
                if tt <= 0:
                    continue
                cross.append(float((Cc + tt * vv)[1] - O[1]))
            uS = uF + s * SOFFIT
            # the soffit bound only means anything for the band it was reasoned about, the upper gallery
            under = (min(uF, uS) <= pu <= max(uF, uS)) and abs(hlo - DECK) < 1e-6
            if cross:
                # WHERE THE RAYS CROSSED THE FACE, printed for every kept fitting rather than only for the
                # ones under the drawn soffit (2026-09-10). This is the assumption-free half of the result:
                # each of these rays reached a lamp standing behind the face, so NOTHING on the face
                # blocked it, so whatever the model draws on the face between these two heights is not
                # solid. It needs no view of the thing it constrains and no identification of the lamp.
                print('        its %d rays crossed the face plane u %.3f between h %.3f and %.3f, so the'
                      ' face carries no solid there' % (len(cross), uF, min(cross), max(cross)))
            if cross and under:
                # THE SENSE OF THE BOUND, stated because the first version of this had it backwards. The
                # slab is horizontal and the ray is rising, so if the ray is already ABOVE the slab where
                # it crosses the gallery face it stays above it and reaches the lamp. If the slab were
                # HIGHER than that crossing, the same ray would run into its underside before it got
                # there. So each lamp standing under the drawn soffit gives an UPPER bound on the soffit,
                # not a lower one, and the tightest ray wins.
                print('        under the drawn soffit; its rays cross the gallery face on h %.3f to %.3f,'
                      ' so a ceiling here cannot sit above %.3f' % (min(cross), max(cross), min(cross)))
                found.append((pu, pd, ph, len(inl), rms, spread, min(cross)))
            else:
                if cross:
                    print('        clear of the drawn soffit in u, so it bounds nothing about the ceiling')
                found.append((pu, pd, ph, len(inl), rms, spread, float('nan')))
        ids = set(id(r) for r in inl)
        pool = [r for r in pool if id(r) not in ids]
        if len(pool) < MINRAYS:
            break
    if found:
        a = np.array([f[2] for f in found])
        print('   %d fittings kept, heights %.3f to %.3f, median %.3f'
              % (len(found), a.min(), a.max(), float(np.median(a))))
        cr = np.array([f[6] for f in found])
        cr = cr[np.isfinite(cr)]
        if cr.size:
            print('   THE OCCLUSION BOUND for this gallery, from %d fittings standing under the drawn'
                  ' soffit: it cannot sit above h %.3f. The sim draws it on 11.100.' % (cr.size, cr.min()))
    return found


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    seen, cams = set(), {}
    for cls in CLASSES:
        try:
            fr = U.load_class(cls)
        except Exception:
            continue
        for f, v in fr.items():
            if f not in seen:
                seen.add(f)
                cams[f] = (cls, v[0], v[1])
    print('%d distinct posed frames offered to the search, band h %s to %s'
          % (len(cams), os.environ.get('HLO', DECK), os.environ.get('HHI', TOP)))
    for e in (('west', 'east') if which == 'both' else (which,)):
        run(e, cams)
