# 2026-09-09: a lamp is a POINT, and that changes which baseline matters.
#
# Every line in the corridor has slid, and the reason is now a number: seeing a line at constant (d, h)
# through a 1.2 m slot forces every lens 12.6 to 16.7 m back, so the far half of the cameras stands only
# 1.32 times as distant as the near half and the two halves are the same instrument twice.
#
# A POINT IS NOT SEPARATED THAT WAY. Its depth is fixed by the ANGULAR spread of the rays that see it,
# which comes from cameras spread ALONG the hall, and that is the one direction this archive has real
# baseline in. It is why the lamps could be triangulated at all when the ceiling could not. So the split
# that tests a lamp is not near against far, it is WEST OF IT against EAST OF IT: two halves that see the
# same lamp from genuinely different directions, where a wrong depth moves the apparent station one way
# for one half and the other way for the other.
#
# AND THIS NEEDED ASKING TONIGHT, because a shipped bound moved on one of these lamps. The corridor width
# went 2.00 to 2.06 this evening to keep the deepest lamp inside the back wall. If that lamp's depth is
# itself a slid number the bound was resting on nothing.
#
# THE RE-RUN ALREADY SAYS SOMETHING BEFORE ANY OF THIS. The shipped lamp array was computed before the
# openings moved 0.147 m and before the wall face moved to -0.030, and the aperture gate that chooses
# which rays may vote depends on both. Re-run now, the three corridor lamps land on d -2.068, -2.049 and
# -1.824 with heights 10.942, 10.935 and 10.908: a depth spread of 0.244 m and a height spread of 0.034,
# where the shipped array has 1.05 and 0.62. One shipped lamp is a metre out in depth and half a metre out
# in height. That is worth confirming with a test that can refuse before anything is redrawn.
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
LAMPS = {8: (30.524, -2.068, 10.942), 9: (34.139, -2.049, 10.935), 11: (42.043, -1.824, 10.908)}
SHIPPED = {8: (30.642, -1.093, 10.374), 9: (34.139, -2.144, 10.990), 11: (42.043, -1.824, 10.908)}
SPAN, STEP = 1.20, 0.10
BAR = 3.0


def hit_plane(C, V, dfix):
    """where each ray crosses the plane d = dfix, in hall coordinates"""
    cq = C - O
    cd = cq @ HD
    vd = V @ HD
    vd = np.where(np.abs(vd) < 1e-9, 1e-9, vd)
    t = (dfix - cd) / vd
    P = cq + t[:, None] * V
    return P @ HU, P[:, 1], t


def centre(C, V, dfix, seed):
    """the station and height the rays agree on at an assumed depth, by consensus not by average"""
    u, h, t = hit_plane(C, V, dfix)
    ok = np.logical_and(t > 0.5, np.abs(u - seed[0]) < 1.0)
    ok = np.logical_and(ok, np.abs(h - seed[1]) < 1.0)
    if int(ok.sum()) < 4:
        return None, None, 0
    return float(np.median(u[ok])), float(np.median(h[ok])), int(ok.sum())


print('%-5s %6s %8s %9s %9s %9s   %s'
      % ('lamp', 'rays', 'best d', 'near-far', 'worst', 'null', 'what it says'))
verdict = {}
for oi, (lu, ld, lh) in sorted(LAMPS.items()):
    src = os.path.join(WALLS, 'lamp-%d-bundle.npy' % oi)
    if not os.path.exists(src):
        print('%-5d no saved bundle' % oi)
        continue
    B = np.load(src)
    C, V = B[:, :3], B[:, 3:]
    cu = (C - O) @ HU
    # THE FIRST SPLIT TRIED HERE WAS WEST OF THE LAMP AGAINST EAST OF IT, because that is the two-sided
    # parallax a point deserves. It is impossible on this data and finding that out is half the result:
    # every ray that votes for any of these three lamps comes from a camera standing between u 31.3 and
    # 35.3, a four-metre band, whatever opening the lamp was found through. Two of the three lamps are
    # seen entirely from one side. So the split falls back to nearer along the hall against further, which
    # works one-sided, and the LEVERAGE, the ratio of the two halves' distances, is printed because it
    # says before any fitting how much the test can possibly resolve.
    along = np.abs(cu - lu)
    cut = float(np.median(along))
    west, east = along <= cut, along > cut
    lever = float(along.max() / max(along.min(), 1e-6))
    print('%-5d %6d   cameras stand u %.1f to %.1f, %.1f to %.1f m from it along the hall, leverage %.2f'
          % (oi, len(B), cu.min(), cu.max(), along.min(), along.max(), lever))
    if int(west.sum()) < 4 or int(east.sum()) < 4:
        print('        one half has too few cameras to split, so this lamp cannot be tested this way')
        continue
    rows = []
    for k in range(-int(SPAN / STEP), int(SPAN / STEP) + 1):
        dv = ld + k * STEP
        a = centre(C, V, dv, (lu, lh))
        w = centre(C[west], V[west], dv, (lu, lh))
        e = centre(C[east], V[east], dv, (lu, lh))
        o = centre(C[0::2], V[0::2], dv, (lu, lh))
        v = centre(C[1::2], V[1::2], dv, (lu, lh))
        if any(x[0] is None for x in (a, w, e, o, v)):
            continue
        gap = float(np.hypot(w[0] - e[0], w[1] - e[1]))
        null = float(np.hypot(o[0] - v[0], o[1] - v[1]))
        rows.append((float(dv), a[0], a[1], gap, null))
    if len(rows) < 5:
        print('        the sweep does not stay on this lamp')
        continue
    gaps = np.array([r[3] for r in rows])
    nulls = np.array([r[4] for r in rows])
    best = rows[int(np.argmin(gaps))]
    edge = best[0] in (rows[0][0], rows[-1][0])
    ratio = gaps.max() / max(nulls.max(), 1e-6)
    ok = (ratio > BAR) and not edge
    verdict[oi] = (ok, best[0], best[2])
    for dv, u, h, gap, null in rows:
        mark = '  <-- the two halves agree best here' if dv == best[0] else ''
        print('        d %+.3f   u %.3f  h %.3f   near-far %5.0f mm   null %5.0f mm%s'
              % (dv, u, h, 1000 * gap, 1000 * null, mark))
    print('        ratio %.1f against a bar of %.1f on a leverage of %.2f, minimum %s the sweep -> %s'
          % (ratio, BAR, lever, 'on the EDGE of' if edge else 'inside',
             'THE DEPTH IS MEASURED' if ok else 'the depth is NOT measured'))
    print('        shipped d %+.3f h %.3f, re-run d %+.3f h %.3f'
          % (SHIPPED[oi][1], SHIPPED[oi][2], ld, lh))

good = [v for v in verdict.values() if v[0]]
print('')
print('%d of the %d lamps carry a real depth minimum' % (len(good), len(verdict)))
if good:
    ds = [v[1] for v in good]
    hs = [v[2] for v in good]
    print('   they sit on d %s and h %s'
          % (', '.join('%+.3f' % d for d in ds), ', '.join('%.3f' % h for h in hs)))
    print('   the highest of them is %.3f, and a ceiling has to be above it' % max(hs))
    print('   the deepest is %+.3f, and a back wall has to be behind it' % min(ds))
