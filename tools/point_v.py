# 2026-09-09: the lamp finder produced EIGHT points behind that wall and only three were ever kept.
#
# The corridor search runs one blob hunt per opening and returns the strongest point the rays agree on.
# Three of those were called lamps because they sat about two metres back at about eleven metres up. The
# other five were passed over without a word, which was a mistake of attention rather than of method: a
# point that triangulates is a measurement whatever it turns out to be, and one of the discarded ones has
# the largest camera baseline of anything in the whole run by a factor of ten.
#
# WHAT WAS DISCARDED, with the baseline the cameras gave each one:
#   opening  3   u 11.443  d  0.006  h  8.819    6 rays,  1.0 m apart, 10 mm rms
#   opening  4   u 15.793  d -0.125  h  9.175    8 rays,  9.8 m apart, 41 mm
#   opening  6   u 24.572  d  0.185  h  8.311    9 rays,  2.3 m apart, 35 mm
#   opening  7   u 26.745  d -0.459  h 11.315   23 rays, 38.6 m apart, 63 mm
#   opening 12   u 45.142  d -0.088  h 11.288    5 rays,  6.5 m apart, 11 mm
# Thirty-eight metres of baseline on a point 0.46 m behind the wall face is better conditioning than
# anything else in this room has ever had, and it was thrown away for not looking like a lamp.
#
# SO TEST THEM ALL THE SAME WAY THE LAMPS WERE TESTED. Sweep the assumed depth, and at each one let every
# ray say where the point would be, one unknown removed. Split the rays by how far the camera stood from
# the point ALONG the hall, which is the direction a point's depth is actually resolved in, and run the
# odd-against-even null beside it. A minimum inside the sweep that beats the null is a depth measurement.
# Anything else is a refusal, and refusals here are as useful as answers because they say which of these
# five are worth chasing with new imagery and which are not.
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH, SILL, HEAD, REVEAL = -0.030, 8.740, 11.165, 0.9
# every point the finder returned, kept or discarded: opening -> (u, d, h, rays, baseline, rms)
POINTS = {3: (11.443, 0.006, 8.819, 6, 1.0, 0.010), 4: (15.793, -0.125, 9.175, 8, 9.8, 0.041),
          6: (24.572, 0.185, 8.311, 9, 2.3, 0.035), 7: (26.745, -0.459, 11.315, 23, 38.6, 0.063),
          8: (30.524, -2.068, 10.942, 15, 3.7, 0.049), 9: (34.139, -2.049, 10.935, 11, 3.5, 0.060),
          11: (42.043, -1.824, 10.908, 8, 3.8, 0.023), 12: (45.142, -0.088, 11.288, 5, 6.5, 0.011)}
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


def where(d, h):
    """say plainly what part of the building a point at this depth and height would be in"""
    if d > DNORTH + 0.05:
        return 'out in the hall, in front of the wall face'
    if d > DNORTH - REVEAL:
        band = 'inside the reveal'
        if h > HEAD + 0.02:
            return band + ', ABOVE the opening head'
        if h < SILL - 0.02:
            return band + ', below the opening sill'
        return band + ', within the opening'
    return 'through the reveal, in the corridor itself'


print('%-4s %5s %7s %8s %9s %8s %8s   %s'
      % ('open', 'rays', 'lever', 'best d', 'near-far', 'worst', 'null', 'verdict'))
kept = []
for oi in sorted(POINTS):
    pu, pd, ph, nr, base, rms = POINTS[oi]
    src = os.path.join(WALLS, 'lamp-%d-bundle.npy' % oi)
    if not os.path.exists(src):
        print('%-4d no saved bundle' % oi)
        continue
    B = np.load(src)
    C, V = B[:, :3], B[:, 3:]
    along = np.abs((C - O) @ HU - pu)
    cut = float(np.median(along))
    near, far = along <= cut, along > cut
    lever = float(along.max() / max(along.min(), 1e-6))
    if int(near.sum()) < 4 or int(far.sum()) < 4:
        print('%-4d %5d %7.2f   only %d and %d rays either side of the split, cannot be tested'
              % (oi, len(B), lever, int(near.sum()), int(far.sum())))
        continue
    rows = []
    for k in range(-int(SPAN / STEP), int(SPAN / STEP) + 1):
        dv = pd + k * STEP
        a, n, f, o, e = (centre(C, V, dv, (pu, ph)), centre(C[near], V[near], dv, (pu, ph)),
                         centre(C[far], V[far], dv, (pu, ph)), centre(C[0::2], V[0::2], dv, (pu, ph)),
                         centre(C[1::2], V[1::2], dv, (pu, ph)))
        if any(x[0] is None for x in (a, n, f, o, e)):
            continue
        rows.append((float(dv), a[0], a[1], float(np.hypot(n[0] - f[0], n[1] - f[1])),
                     float(np.hypot(o[0] - e[0], o[1] - e[1]))))
    if len(rows) < 5:
        print('%-4d %5d %7.2f   the sweep does not stay on this point' % (oi, len(B), lever))
        continue
    gaps = np.array([r[3] for r in rows])
    nulls = np.array([r[4] for r in rows])
    best = rows[int(np.argmin(gaps))]
    edge = best[0] in (rows[0][0], rows[-1][0])
    ratio = gaps.max() / max(nulls.max(), 1e-6)
    ok = (ratio > BAR) and not edge
    print('%-4d %5d %7.2f %8.3f %7.0f mm %7.0f mm %6.0f mm   %s'
          % (oi, len(B), lever, best[0], 1000 * gaps.min(), 1000 * gaps.max(), 1000 * nulls.max(),
             'MEASURED, ratio %.1f' % ratio if ok
             else ('minimum on the sweep edge' if edge else 'not measured, ratio %.1f' % ratio)))
    print('     the finder put it on d %+.3f h %.3f; the split puts it on d %+.3f h %.3f, which is %s'
          % (pd, ph, best[0], best[2], where(best[0], best[2])))
    if ok:
        kept.append((oi, best[0], best[1], best[2], lever, ratio))

print('')
print('%d of the %d points behind or on that wall carry a real depth minimum' % (len(kept), len(POINTS)))
for oi, d, u, h, lever, ratio in kept:
    print('   opening %2d: u %.3f  d %+.3f  h %.3f  (leverage %.2f, ratio %.1f) -- %s'
          % (oi, u, d, h, lever, ratio, where(d, h)))
inside = [k for k in kept if k[1] < DNORTH - REVEAL]
reveal = [k for k in kept if DNORTH - REVEAL <= k[1] <= DNORTH + 0.05]
print('')
if inside:
    print('   %d of them are in the CORRIDOR itself. The deepest sits on %+.3f, so the back wall stands'
          % (len(inside), min(k[1] for k in inside)))
    print('   behind that, and the highest on %.3f, so the ceiling stands above that.'
          % max(k[3] for k in inside))
if reveal:
    print('   %d are INSIDE THE REVEAL, which is a part of this wall nothing had ever measured a point in.'
          % len(reveal))
    for oi, d, u, h, lever, ratio in reveal:
        print('      opening %2d puts one on d %+.3f, %.3f m behind the face, and h %.3f, %+.3f m relative'
              % (oi, d, DNORTH - d, h, h - HEAD))
        print('      to the opening head. The reveal is drawn %.2f m deep.' % REVEAL)
if not kept:
    print('   none of them. Every point in this room is under-conditioned, and the reason is the same one')
    print('   the lines died of: the slot puts every camera in a narrow band and no point is seen from')
    print('   both sides of itself.')
