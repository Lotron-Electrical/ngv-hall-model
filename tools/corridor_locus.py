# 2026-09-09: the corridor, asked the only question this archive can answer about it.
#
# The room behind the brick wall has beaten every attempt today, and the reason was always the same. A
# line at constant (d, h) is separated from its rays only by cameras standing at different distances from
# it, and seeing that line through a 1.2 m slot forces the lens far back, so the usable set collapses and
# the answer slides along the median ray with every subset stopping somewhere else on it.
#
# ANCHORING REMOVES THE NEED FOR A BASELINE ALTOGETHER, which is the thing I did not see this morning.
# Fix the depth and each ray gives the height directly, h = ch + vh*(d - cd)/vd. One unknown per ray,
# independent of every other ray, nothing left to slide. A baseline is what a TWO-unknown fit needs; a
# one-unknown fit has no degenerate direction to slide along. That is how the night walk got to say
# something about the balcony front on 92 rays across 15 m of hall, and the corridor has 215 rays.
#
# SO STOP ASKING FOR A NUMBER AND ASK FOR THE LOCUS. Sweep the assumed depth of the back wall, and for
# each one report the ceiling height the rays agree on, how many agree, and how tightly. That is the
# complete, honest statement of what this archive knows about that room: not a point, a curve, plus
# whatever independent facts can cut across it.
#
# AND THERE ARE TWO SUCH FACTS. The three lamps triangulated inside that room hang on h 10.374, 10.908 and
# 10.990, and a ceiling has to be above the highest of them. The deepest of them sits 2.054 m behind the
# wall face, so the back wall is at least that deep. Neither comes from these rays, so both may cut it.
import os

import numpy as np

OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH, DBACK, CEIL, FLOOR = -0.090, -2.090, 11.4, 8.34
LAMPS = (10.374, 10.908, 10.990)
LAMPDEEP = 2.054
TOL = 0.05

A = np.load(os.path.join(OUT, 'corridor-ceiling-rays.npy'))
R, UU = A[:, :4], A[:, 4]
print('%d rays that crossed the wall plane inside a measured opening, from cameras d %.2f to %.2f'
      % (len(R), R[:, 0].min(), R[:, 0].max()))


def heights(Rr, dfix):
    vd = np.where(np.abs(Rr[:, 2]) < 1e-9, 1e-9, Rr[:, 2])
    return Rr[:, 1] + Rr[:, 3] * (dfix - Rr[:, 0]) / vd


def consensus(h, lo=9.5, hi=13.5):
    h = h[np.logical_and(h > lo, h < hi)]
    if len(h) < 25:
        return None, 0, 0.0
    grid = np.arange(lo, hi, 0.005)
    counts = np.array([int(np.sum(np.abs(h - g) < TOL)) for g in grid])
    g = float(grid[int(np.argmax(counts))])
    near = h[np.abs(h - g) < TOL]
    return float(np.median(near)), int(len(near)), float(len(near)) / float(len(h))


print('')
print('   back wall     ceiling   rays agreeing   share   clears the top lamp by')
rows = []
for dv in np.arange(-3.60, -1.199, 0.10):
    hval, n, frac = consensus(heights(R, float(dv)))
    if hval is None:
        continue
    rows.append((float(dv), hval, n, frac))
    flag = '' if hval > LAMPS[2] else '   IMPOSSIBLE, a lamp hangs above it'
    print('   %+.3f      %7.3f   %5d          %4.0f%%   %+.3f m%s'
          % (dv, hval, n, 100 * frac, hval - LAMPS[2], flag))

if not rows:
    raise SystemExit('no consensus anywhere along the sweep')
best = max(rows, key=lambda r: r[2])
print('')
print('   the sharpest agreement is on d %+.3f, giving a ceiling on h %.3f from %d rays (%.0f per cent)'
      % (best[0], best[1], best[2], 100 * best[3]))
ns = np.array([r[2] for r in rows], float)
dsv = np.array([r[0] for r in rows])
wide = dsv[ns >= 0.95 * ns.max()]
print('   the count stays within 5 per cent of its peak from d %+.3f to %+.3f, a band %.2f m wide'
      % (wide.min(), wide.max(), wide.max() - wide.min()))

ok = [r for r in rows if r[1] > LAMPS[2]]
bad = [r for r in rows if r[1] <= LAMPS[2]]
print('')
print('   THE LAMPS CUT THE CURVE. A ceiling below h %.3f is impossible, because a lamp hangs there.'
      % LAMPS[2])
if bad:
    print('   That rules out every back wall shallower than d %+.3f.' % max(r[0] for r in bad))
else:
    print('   Every depth on this sweep clears it, so the lamps rule nothing out here.')
deep = [r for r in ok if r[0] <= -LAMPDEEP]
if deep:
    print('   The deepest lamp also puts the wall at least %.3f m back, and inside that band the ceiling'
          % LAMPDEEP)
    print('   runs %.3f to %.3f against a drawn %.3f.'
          % (min(r[1] for r in deep), max(r[1] for r in deep), CEIL))

i0 = int(np.argmin(np.abs(np.array([r[0] for r in rows]) - DBACK)))
r0 = rows[i0]
print('')
print('   ON THE DRAWN BACK WALL d %+.3f the rays put the ceiling on h %.3f from %d rays, against a drawn'
      % (r0[0], r0[1], r0[2]))
print('   %.3f, so %+.3f m. That is a conditional answer and it is stated as one: it is the ceiling IF'
      % (CEIL, r0[1] - CEIL))
print('   the back wall is where the plan puts it, and these rays cannot check that.')
hall = heights(R, r0[0])
keep = np.abs(hall - r0[1]) < TOL
Q, QU = R[keep], UU[keep]
if len(Q) >= 30:
    m = float(np.median(QU))
    md = float(np.median(Q[:, 0]))
    for lab, sel in (('west half', QU <= m), ('east half', QU > m),
                     ('nearer', Q[:, 0] <= md), ('further', Q[:, 0] > md)):
        if int(sel.sum()) >= 12:
            hv2 = heights(Q[sel], r0[0])
            print('   %-10s %3d rays -> h %.3f' % (lab, int(sel.sum()), float(np.median(hv2))))
    print('   these splits mean something now that every ray answers on its own, which they did not when')
    print('   two unknowns were being fitted and every subset could stop anywhere along the slide.')
