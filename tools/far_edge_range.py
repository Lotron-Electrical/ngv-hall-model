# 2026-09-09: GIVE THE FAR EDGE A RANGE, which is the one thing that decides whether it is a bound.
#
# The bound written on the far edge was withdrawn within the hour for a specific reason: a crossing height
# is an occlusion bound only if the detected feature lies BEYOND the face plane, because only then did the
# sightline cross it, and tools/west_far.py never tested the range of what it detected. This closes that.
#
# THE FIT ALREADY CONTAINS THE RANGE and it was thrown away. A horizontal edge spanning the hall is a line
# (u*, h*) in the (u, h) plane; every detection is a ray that should pass through it. Fitting the pair is
# therefore a 3D localisation, not just a height: it says WHERE ALONG each ray the feature sits. Compare
# that range with the distance to the face plane along the same ray and the question answers itself.
#
# TWO THINGS ARE FIXED HERE AS WELL, both of which made the earlier estimate softer than it looked.
#   THE RESIDUAL WAS NOT IN METRES. vh*u* - vu*h* - (vh*cu - vu*ch) is the perpendicular distance times
#   sqrt(vu^2 + vh^2), and for a ray tipped well out of the u-h plane that factor is well under one. An
#   80 mm threshold was therefore a different threshold for every ray. Dividing through makes it metres.
#   AND ONE FIT OVER EVERYTHING CANNOT BE CHECKED. The cameras span 37 m of hall, so the near half and the
#   far half are two independent experiments on the same edge. If they agree the line is real; if they do
#   not, the single fit was averaging two things and its inlier count meant nothing.
#   RAYS="west" python tools/far_edge_range.py
import os

import numpy as np

OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
FACE = {'west': 4.194, 'east': 48.056}
DECK = 8.34
THRESH = 0.05
ends = os.environ.get('RAYS', 'west east').split()
TAG = os.environ.get('TAG', '')
# HLO/HHI keep the RANSAC window on the same band the ladder was walked over, so a fit
# for the upstand cannot wander up onto the front edge already measured above it.
HLO = float(os.environ.get('HLO', '8.0'))
HHI = float(os.environ.get('HHI', '12.0'))


def fit(R):
    """least squares (u*, h*) for a horizontal edge, in the two-unknown form"""
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


def perp(R, uval, hval):
    """the true perpendicular distance in metres from each ray to the line (uval, hval)"""
    num = R[:, 3] * (uval - R[:, 0]) - R[:, 2] * (hval - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def ransac(R, uf, tries=20000, seed=11):
    rng = np.random.default_rng(seed)
    bestn, best = -1, None
    ii = rng.integers(0, len(R), tries)
    jj = rng.integers(0, len(R), tries)
    for a, b in zip(ii, jj):
        if a == b:
            continue
        S = R[[a, b]]
        A = np.stack([S[:, 3], -S[:, 2]], 1)
        y = S[:, 3] * S[:, 0] - S[:, 2] * S[:, 1]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        c = np.linalg.solve(A, y)
        if not (uf - 3.0 < c[0] < uf + 3.0 and HLO < c[1] < HHI):
            continue
        n = int((perp(R, c[0], c[1]) < THRESH).sum())
        if n > bestn:
            bestn, best = n, c
    return bestn, best


for end in ends:
    src = os.path.join(OUT, '%s%s-far-rays.npy' % (end, TAG))
    if not os.path.exists(src):
        print('%s: no saved rays; run tools/west_far.py with END=%s first' % (end, end))
        continue
    R = np.load(src)
    uf = FACE[end]
    print('')
    print('%s END: %d rays, cameras from u %.2f to %.2f' % (end.upper(), len(R), R[:, 0].min(),
                                                            R[:, 0].max()))
    n, sol = ransac(R, uf)
    if sol is None:
        print('   no line found')
        continue
    inl = perp(R, sol[0], sol[1]) < THRESH
    ref = fit(R[inl])
    inl = perp(R, ref[0], ref[1]) < THRESH
    ref = fit(R[inl])
    d = perp(R[inl], ref[0], ref[1])
    print('   RANSAC then two refits: the edge sits on u %.3f h %.3f' % (ref[0], ref[1]))
    print('   %d of %d rays (%.0f per cent) pass within %.0f mm of it, median %.0f mm'
          % (int(inl.sum()), len(R), 100.0 * inl.mean(), THRESH * 1000, 1000 * float(np.median(d))))

    # THE RANGE. Where along each inlier ray the closest approach happens, against the distance to the
    # face plane along the same ray. A positive difference means the feature is BEYOND the plane, so the
    # sightline crossed it and nothing solid could have stood there.
    Q = R[inl]
    s = ((ref[0] - Q[:, 0]) * Q[:, 2] + (ref[1] - Q[:, 1]) * Q[:, 3]) / (Q[:, 2] ** 2 + Q[:, 3] ** 2)
    sface = (uf - Q[:, 0]) / np.where(np.abs(Q[:, 2]) < 1e-9, 1e-9, Q[:, 2])
    gap = s - sface
    print('   range to the edge along the ray: median %.2f m, quartiles %.2f to %.2f'
          % (float(np.median(s)), float(np.percentile(s, 25)), float(np.percentile(s, 75))))
    print('   range to the drawn face plane:   median %.2f m' % float(np.median(sface)))
    print('   the edge is %+.2f m along the ray from the plane, and %.0f per cent of the inliers put it'
          % (float(np.median(gap)), 100.0 * float((gap > 0).mean())))
    print('   beyond the plane rather than in front of it')

    # THE SPLIT TEST. Near cameras and far cameras are two independent experiments on the same edge.
    mid = float(np.median(np.abs(R[:, 0] - uf)))
    near = np.abs(Q[:, 0] - uf) <= mid
    for label, sel in (('nearer half', near), ('further half', ~near)):
        if sel.sum() < 30:
            print('   %s: only %d inliers' % (label, int(sel.sum())))
            continue
        f2 = fit(Q[sel])
        print('   %-13s %5d inliers -> u %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
    print('   the drawn face is %.3f and the deck %.3f, so this edge stands %.3f m above the deck'
          % (uf, DECK, ref[1] - DECK))
