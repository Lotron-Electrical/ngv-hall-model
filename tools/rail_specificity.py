# 2026-09-09: is the new line on the BALCONY, or on a long wall behind it?
#
# The rail band peel turned up a third edge at both ends that nothing in the model accounts for: west
# h 10.002 from 347 inliers with an 18 mm median and its near and far camera halves agreeing to 15 mm in
# height and 16 mm in station, east h 10.020 with its halves agreeing exactly. Those are strong lines.
#
# BUT THE TWO ENDS ARE ELEVEN MILLIMETRES APART AND THE TWO BALCONY FRONTS ARE SIXTY-SIX. If this were a
# feature of each parapet it ought to differ between the ends by about as much as the parapets do. A
# feature at the same absolute height at BOTH ends is what a line running the length of the building looks
# like, and a line on the north or south wall, seen by a camera looking down the hall, projects almost
# where a line on the end would. The fit cannot tell those apart; it will happily put a long-wall line at
# the end station, because that is where the rays cross.
#
# THE DETECTIONS THEMSELVES CAN TELL THEM APART. The ladder was walked ACROSS the hall, d 1.0 to 14.0, and
# every detection carries the d station it came from. A line on the end spans the hall, so its inliers
# should be spread over the whole width. A line on the north wall lives near d 0 and one on the south wall
# near d 15.4, so its inliers would pile up at one edge. This asks the question the fit cannot.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
FACE = {'west': 4.194, 'east': 48.056}
FRONT = {'west': 9.799, 'east': 9.865}
QUARTERS = ((1.0, 4.25), (4.25, 7.5), (7.5, 10.75), (10.75, 14.0))
THRESH = 0.05


def share(d, lo, hi):
    return 100.0 * float(np.mean(np.logical_and(d >= lo, d < hi)))


def perp(R, uv, hv):
    num = R[:, 3] * (uv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


def ransac(R, uf, hlo, hhi, seed=41):
    rng = np.random.default_rng(seed)
    ii = rng.integers(0, len(R), 30000)
    jj = rng.integers(0, len(R), 30000)
    bestn, best = -1, None
    for a, b in zip(ii, jj):
        if a == b:
            continue
        S = R[[a, b]]
        A = np.stack([S[:, 3], -S[:, 2]], 1)
        y = S[:, 3] * S[:, 0] - S[:, 2] * S[:, 1]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        c = np.linalg.solve(A, y)
        if not (uf - 1.5 < c[0] < uf + 1.5 and hlo < c[1] < hhi):
            continue
        n = int((perp(R, c[0], c[1]) < THRESH).sum())
        if n > bestn:
            bestn, best = n, c
    return best


for end in ('west', 'east'):
    src = os.path.join(POSEDIR, '%s-rail-far-rays.npy' % end)
    if not os.path.exists(src):
        print('%s: no saved rays' % end)
        continue
    A = np.load(src)
    R, DD = A[:, :4], A[:, 4]
    uf, ft = FACE[end], FRONT[end]
    print('')
    print('%s END: %d detections, spread over d %.2f to %.2f' % (end.upper(), len(R), DD.min(), DD.max()))
    print('   all detections by quarter of the hall width: %s'
          % ' '.join('%.0f%%' % share(DD, lo, hi) for lo, hi in QUARTERS))
    for label, hlo, hhi in (('the front top already measured', ft - 0.06, ft + 0.06),
                            ('the new line above it', 9.93, 10.12)):
        sol = ransac(R, uf, hlo, hhi)
        if sol is None:
            print('   %-32s no line in that window' % label)
            continue
        inl = perp(R, sol[0], sol[1]) < THRESH
        ref = fit(R[inl])
        inl = perp(R, ref[0], ref[1]) < THRESH
        if int(inl.sum()) < 40:
            print('   %-32s only %d inliers' % (label, int(inl.sum())))
            continue
        ref = fit(R[inl])
        d = DD[inl]
        q = [share(d, lo, hi) for lo, hi in QUARTERS]
        print('   %-32s u %.3f h %.3f, %d inliers, %.0f mm median'
              % (label, ref[0], ref[1], int(inl.sum()),
                 1000 * float(np.median(perp(R[inl], ref[0], ref[1])))))
        print('        its inliers by quarter of the hall: %s   (d %.2f to %.2f, median %.2f)'
              % (' '.join('%.0f%%' % t for t in q), d.min(), d.max(), float(np.median(d))))
        wide = sum(1 for t in q if t >= 10.0)
        print('        %d of the 4 quarters carry at least a tenth of them, so this line %s'
              % (wide, 'spans the hall the way an end feature must'
                 if wide >= 3 else 'is bunched at one side and is NOT an end feature'))
