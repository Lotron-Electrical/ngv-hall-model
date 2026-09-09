# 2026-09-09: eight jamb lines agree on a depth to 16 mm while each one's own halves scatter by 500.
# A population tighter than its members is a signature worth chasing, because it is what a shared bias
# looks like as well as what a shared feature looks like.
#
# THE FACT THAT STARTED THIS. The peel finds every north jamb 0.177 m behind the face the sill and the
# head were measured on, and it finds NO vertical edge on the face plane at all. If these openings were
# reveals 0.9 m deep, the face arris is the strongest brightness step on that wall and should be peeled
# first. It is not peeled at any support level. So either the openings are shallow rebates and the model's
# 0.9 m reveal is wrong by 0.7 m, or this depth is not a depth.
#
# THE PEEL'S OWN SIDE SPLIT PREDICTS ITS ANSWER AND GETS IT BACKWARDS. Its header argues, correctly, that
# a recessed opening shows a camera west of it the WEST jamb's face edge and a camera east of it the same
# jamb's reveal edge, so the side that sees the face should read SHALLOWER. Across the four west jambs the
# west cameras read a median 0.240 and the east cameras 0.201, and across the four east jambs the east
# cameras read 0.200 and the west 0.146. Both parities have the face-side reading DEEPER, which is the
# prediction inverted twice. Individual splits scatter to 0.526 on one line. Those splits refit BOTH
# unknowns on half the rays, so they are two-unknown fits on short baselines and they scatter for a reason
# that has nothing to do with the wall.
#
# SO ASK THE ONE-UNKNOWN QUESTION INSTEAD. Fix the station and every ray gives the depth on its own,
# d = cd + vd*(u* - cu)/vu, nothing to slide along, exactly as fixing the depth gave the station this
# afternoon and fixing the plane gave the height in the corridor. Then split the rays the way this
# geometry is actually separated: a vertical line's depth is resolved by cameras spread ALONG the hall,
# because a lens standing square in front of a jamb cannot tell a face arris from a reveal arris and one
# far down the hall can. Near and far here therefore mean near and far ALONG u, and the odd-against-even
# null runs beside it as it has all night.
#
# THE GATE HAS ALREADY BEEN CLEARED. Doubling the peel's depth gate to 0.60 returns the same four west
# lines with the same depths to the millimetre, so the -0.21 is not the gate speaking.
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH, THRESH = -0.030, 0.05
TOL, BAR = 0.02, 3.0


def perp(R, uval, dval):
    num = R[:, 3] * (uval - R[:, 0]) - R[:, 2] * (dval - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def solve_d(R, ufix):
    """one unknown per ray: where the vertical line through ufix must stand for this ray to meet it"""
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (ufix - R[:, 0]) / vu


def consensus(d, centre, win=0.60):
    d = d[np.abs(d - centre) < win]
    if len(d) < 8:
        return None
    grid = np.arange(centre - win, centre + win, 0.002)
    counts = np.array([int(np.sum(np.abs(d - g) < TOL)) for g in grid])
    peak = float(grid[int(np.argmax(counts))])
    return float(np.median(d[np.abs(d - peak) < TOL]))


rows = []
for edge in ('west', 'east'):
    A = np.load(os.path.join(WALLS, 'jamb-%s-rays.npy' % edge))
    L = np.load(os.path.join(WALLS, 'jamb-%s-lines.npy' % edge))
    R = A[:, :4]
    print('')
    print('%s JAMBS, %d rays, %d peeled lines' % (edge.upper(), len(R), len(L)))
    print('   line u    depth    near-u    far-u    they differ by   odd-even   leverage')
    for u0, d0, nsup, med in L:
        sel = perp(R, u0, d0) < THRESH
        S = R[sel]
        if len(S) < 20:
            print('   %7.3f  too few supporting rays to ask' % u0)
            continue
        along = np.abs(S[:, 0] - u0)
        cut = float(np.median(along))
        near, far = S[along <= cut], S[along > cut]
        a = consensus(solve_d(S, u0), d0)
        n = consensus(solve_d(near, u0), d0)
        f = consensus(solve_d(far, u0), d0)
        o = consensus(solve_d(S[0::2], u0), d0)
        e = consensus(solve_d(S[1::2], u0), d0)
        if any(x is None for x in (a, n, f)):
            print('   %7.3f  no consensus in one of the halves' % u0)
            continue
        null = abs(o - e) if (o is not None and e is not None) else float('nan')
        lev = float(along.max()) / max(float(along.min()), 1e-6)
        rows.append((edge, float(u0), a, abs(n - f), null, lev, int(len(S))))
        print('   %7.3f  %+.3f   %+.3f   %+.3f      %6.0f mm    %5.0f mm    %6.1f'
              % (u0, a, n, f, 1000 * abs(n - f), 1000 * null, lev))

if not rows:
    raise SystemExit('nothing had enough support to be asked')
print('')
ds = np.array([r[2] for r in rows])
sp = np.array([r[3] for r in rows])
nu = np.array([r[4] for r in rows])
print('   %d lines answered. Their depths span %.0f mm, from %+.3f to %+.3f, and the population median'
      % (len(rows), 1000 * float(np.ptp(ds)), ds.min(), ds.max()))
print('   is %+.3f, which is %.3f m behind the face on %+.3f.'
      % (float(np.median(ds)), abs(float(np.median(ds)) - DNORTH), DNORTH))
print('   near-far spread per line runs %.0f to %.0f mm, median %.0f; the null runs %.0f to %.0f mm.'
      % (1000 * sp.min(), 1000 * sp.max(), 1000 * float(np.median(sp)),
         1000 * np.nanmin(nu), 1000 * np.nanmax(nu)))
beat = int(np.sum(sp < np.where(np.isnan(nu), np.inf, nu) * BAR))
print('')
if float(np.median(sp)) < BAR * float(np.nanmedian(nu)) and beat >= max(2, len(rows) // 2):
    print('   THE DEPTH IS MEASURED. %d of %d lines keep their near-far spread inside %.0f times their own'
          % (beat, len(rows), BAR))
    print('   null, so cameras at the two ends of the hall agree about where this edge stands, and they')
    print('   agree line by line and not only on average. The north openings really are rebated %.3f m'
          % abs(float(np.median(ds)) - DNORTH))
    print('   behind the plane the sill and the head were measured on.')
else:
    print('   REFUSED, AND THE POPULATION AGREEMENT DOES NOT RESCUE IT. Only %d of %d lines keep their'
          % (beat, len(rows)))
    print('   near-far spread inside %.0f times their own null, so the two ends of the hall do not agree'
          % BAR)
    print('   about where any individual edge stands. Eight lines landing within 16 mm of each other while')
    print('   no single one of them can be located is what a shared bias looks like, not a shared feature,')
    print('   and it is the exact shape the corridor lamps showed before their points were withdrawn.')
    print('   Nothing about the reveal depth is established, and openDepth stays where it is on its own')
    print('   evidence rather than gaining or losing any from this.')
