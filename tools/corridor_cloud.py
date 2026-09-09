# 2026-09-09: the search behind this wall has only ever been allowed to find ONE thing per opening.
#
# tools/corridor_lamp.py gathers every bright blob visible through an aperture, then keeps the single
# point the most rays agree on and stops. That is why the archive's whole knowledge of the room behind the
# brick wall is eight points: one per opening that answered at all. Nothing was wrong with the method; it
# was simply never asked for a second answer.
#
# AND THE LAST TWO NIGHTS OF WORK SAY THE SECOND ANSWER IS WORTH ASKING FOR. Every LINE in that room has
# died the same death, because a line at constant (d, h) is separated only by cameras at different
# distances and the slot collapses that to a leverage of 1.32. A POINT is separated by the angular spread
# of the rays that see it, which is the one direction this archive has baseline in. Points are the only
# instrument that works in there, and the finder has been returning one eighth of them.
#
# SO PEEL. Find the strongest point, record it, remove the rays that voted for it, and search what is
# left. Exactly the peel that took nine jamb lines off the north wall this afternoon, applied to points
# instead of lines. Keep going until nothing left has enough rays to be a point.
#
# THEN MAKE EVERY PEELED POINT EARN ITS PLACE. A peel produces weak answers as well as strong ones by
# construction: each round works with fewer rays than the last. So every point goes through the parallax
# split with its own odd-against-even null, and only the ones with a real minimum inside their sweep are
# kept. The rest are counted and named as refusals, because a refused point still says where the archive
# cannot see.
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import corridor_lamp as CL  # noqa: E402
import underside_geom as U  # noqa: E402

O = CL.O
HU, HD = CL.HU, CL.HD
WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH, SILL, HEAD, REVEAL, CBACK = -0.030, 8.740, 11.165, 0.9, -2.090
MAXPTS = int(os.environ.get('MAXPTS', '6'))     # how many points to peel from one opening
MINR = int(os.environ.get('MINR', '5'))         # a point needs this many rays to be a point at all
RAD = 0.12                                      # the inlier radius the lamp search already uses
SPAN, STEP, BAR = 1.20, 0.10, 3.0


def at_depth(C, V, dfix):
    cq = C - O
    vd = V @ HD
    vd = np.where(np.abs(vd) < 1e-9, 1e-9, vd)
    t = (dfix - cq @ HD) / vd
    P = cq + t[:, None] * V
    return P @ HU, P[:, 1], t


def centre(C, V, dfix, seed):
    u, h, t = at_depth(C, V, dfix)
    ok = np.logical_and(t > 0.5, np.abs(u - seed[0]) < 1.2)
    ok = np.logical_and(ok, np.abs(h - seed[1]) < 1.2)
    if int(ok.sum()) < 4:
        return None, None
    return float(np.median(u[ok])), float(np.median(h[ok]))


def parallax(C, V, seed):
    """does this point's depth carry a real minimum, or is it riding on one camera cluster?"""
    along = np.abs((C - O) @ HU - seed[0])
    cut = float(np.median(along))
    near, far = along <= cut, along > cut
    lever = float(along.max() / max(along.min(), 1e-6))
    if int(near.sum()) < 4 or int(far.sum()) < 4:
        return None, lever, 0.0
    rows = []
    for k in range(-int(SPAN / STEP), int(SPAN / STEP) + 1):
        dv = seed[2] + k * STEP
        a, n, f = (centre(C, V, dv, seed), centre(C[near], V[near], dv, seed),
                   centre(C[far], V[far], dv, seed))
        o, e = centre(C[0::2], V[0::2], dv, seed), centre(C[1::2], V[1::2], dv, seed)
        if any(x[0] is None for x in (a, n, f, o, e)):
            continue
        rows.append((float(dv), a[0], a[1], float(np.hypot(n[0] - f[0], n[1] - f[1])),
                     float(np.hypot(o[0] - e[0], o[1] - e[1]))))
    if len(rows) < 5:
        return None, lever, 0.0
    gaps = np.array([r[3] for r in rows])
    nulls = np.array([r[4] for r in rows])
    best = rows[int(np.argmin(gaps))]
    if best[0] in (rows[0][0], rows[-1][0]):
        return None, lever, gaps.max() / max(nulls.max(), 1e-6)
    ratio = gaps.max() / max(nulls.max(), 1e-6)
    return (best[0], best[1], best[2]) if ratio > BAR else None, lever, ratio


def where(d, h):
    if d > DNORTH + 0.05:
        return 'in front of the wall face'
    if d > DNORTH - REVEAL:
        if h > HEAD + 0.02:
            return 'in the reveal, ABOVE the head'
        if h < SILL - 0.02:
            return 'in the reveal, below the sill'
        return 'in the reveal'
    if d < CBACK - 0.05:
        return 'BEHIND the drawn back wall'
    return 'in the corridor'


cams = {}
for cls in CL.CLASSES if hasattr(CL, 'CLASSES') else ['walk', 'night', 'day4k', 'b1', 'b1p']:
    try:
        for f, v in U.load_class(cls).items():
            cams.setdefault(f, (cls, v[0], v[1]))
    except Exception:
        continue
print('%d distinct posed frames offered to the peel' % len(cams))

kept, refused = [], []
for oi, (u0, u1) in enumerate(CL.OPENINGS):
    rays = []
    for f, (cls, cam, ip) in cams.items():
        qc = cam.center - O
        if float(qc @ HD) < 0.5 or abs(float(qc @ HU) - 0.5 * (u0 + u1)) > 22.0:
            continue
        q = CL.aperture(cam, u0, u1)
        if q is None or q[:, 0].min() < 0 or q[:, 0].max() > cam.w \
                or q[:, 1].min() < 0 or q[:, 1].max() > cam.h:
            continue
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        for r in CL.rays_for(cam, cv2.GaussianBlur(img, (3, 3), 0), u0, u1):
            rays.append(r)
    if len(rays) < MINR:
        continue
    print('')
    print('OPENING %2d, u %.3f to %.3f: %d blobs to peel' % (oi + 1, u0, u1, len(rays)))
    pool = list(rays)
    for round_ in range(MAXPTS):
        if len(pool) < MINR:
            break
        best = None
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                if np.linalg.norm(pool[i][0] - pool[j][0]) < 1.0:
                    continue
                P = CL.closest_point([pool[i], pool[j]])
                inl = [r for r in pool if CL.dist_to(P, r[0], r[1]) < RAD]
                if best is None or len(inl) > len(best[1]):
                    best = (P, inl)
        if best is None or len(best[1]) < MINR:
            break
        P = CL.closest_point(best[1])
        for _ in range(3):
            inl = [r for r in pool if CL.dist_to(P, r[0], r[1]) < RAD]
            if len(inl) < MINR:
                break
            P = CL.closest_point(inl)
        inl = [r for r in pool if CL.dist_to(P, r[0], r[1]) < RAD]
        if len(inl) < MINR:
            break
        qq = P - O
        pu, pd, ph = float(qq @ HU), float(qq @ HD), float(P[1] - O[1])
        C = np.array([r[0] for r in inl])
        V = np.array([r[1] for r in inl])
        res, lever, ratio = parallax(C, V, (pu, ph, pd))
        rms = float(np.sqrt(np.mean([CL.dist_to(P, r[0], r[1]) ** 2 for r in inl])))
        if res is None:
            print('   peel %d: u %.3f d %+.3f h %.3f, %2d rays, %.0f mm rms -- REFUSED '
                  '(leverage %.2f, ratio %.1f)' % (round_ + 1, pu, pd, ph, len(inl), 1000 * rms,
                                                   lever, ratio))
            refused.append((oi + 1, pu, pd, ph, len(inl), lever, ratio))
        else:
            print('   peel %d: u %.3f d %+.3f h %.3f, %2d rays, %.0f mm rms -- MEASURED, the split puts '
                  'it on d %+.3f h %.3f (leverage %.2f, ratio %.1f), %s'
                  % (round_ + 1, pu, pd, ph, len(inl), 1000 * rms, res[0], res[2], lever, ratio,
                     where(res[0], res[2])))
            kept.append((oi + 1, res[1], res[0], res[2], len(inl), lever, ratio))
            np.save(os.path.join(WALLS, 'cloud-%d-%d.npy' % (oi + 1, round_ + 1)),
                    np.column_stack([C, V]))
        ids = set(id(r) for r in inl)
        pool = [r for r in pool if id(r) not in ids]

print('')
print('THE CLOUD: %d points survive the parallax test, %d are refused' % (len(kept), len(refused)))
if kept:
    print('   opening   u        d        h       rays  leverage  ratio   where')
    for oi, u, d, h, n, lever, ratio in sorted(kept, key=lambda z: z[1]):
        print('   %5d   %7.3f  %+7.3f  %7.3f  %4d  %7.2f  %6.1f   %s'
              % (oi, u, d, h, n, lever, ratio, where(d, h)))
    deep = [k for k in kept if k[2] < DNORTH - REVEAL]
    rev = [k for k in kept if DNORTH - REVEAL <= k[2] <= DNORTH + 0.05]
    print('')
    print('   %d in the corridor, %d in the reveals, %d in front of the face'
          % (len(deep), len(rev), len(kept) - len(deep) - len(rev)))
    if rev:
        hs = [k[3] for k in rev]
        print('   the reveal points run h %.3f to %.3f and d %+.3f to %+.3f'
              % (min(hs), max(hs), max(k[2] for k in rev), min(k[2] for k in rev)))
    if deep:
        print('   the corridor points run h %.3f to %.3f, deepest %+.3f'
              % (min(k[3] for k in deep), max(k[3] for k in deep), min(k[2] for k in deep)))
