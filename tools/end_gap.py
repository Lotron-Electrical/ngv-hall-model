# 2026-09-10: A HOLE IN A POINT CLOUD IS A MEASUREMENT, and this tests whether the hole is real.
#
# tools/end_cloud_census.py asked which reconstruction has points inside the end recess and got a blunt
# answer: NONE of the balcony clips' own models has a single one. b1 has 0, b3 0, b4 0 of its 389, b5 0 of
# 644, b6g 0 of 63, b6s 0 of 10, b7s 0 of 110. The hope that standing three metres from the recess would
# reconstruct it is dead, and now measured rather than assumed. Everything in that band comes from the one
# shared site cloud, and it is thin: 15 points west, 36 east.
#
# 36 IS THIN BUT IT IS NOT NOTHING, and thin points can still answer one particular question. Take only
# the points DEEP in the end, more than a metre behind the face, so nothing on the face is in the sample.
# If that band is an open recess with a sill and a head, the points land on the sill below and the head
# above and there is AIR between them, so the heights come back in two clusters with a hole. If the band
# is one flat wall, the heights come back spread.
#
# THE GAP NEEDS A NULL OR IT IS JUST A HISTOGRAM. With n points scattered at random over a height range R,
# the chance that some gap of size g or larger appears anywhere is about n * (1 - g/R)^(n-1). That is the
# number printed beside every gap, so a hole that thin sampling would have produced by itself declares
# itself instead of being read as architecture.
#
# WHAT IT CANNOT DO. It finds a hole between two surfaces; it does not identify either of them, and it
# cannot say the hole is an opening rather than, say, a band of dark stone that failed to match. The
# points' own colour and track length are printed so that guess stays the reader's and not the tool's.
#   python tools/end_gap.py [min depth behind the face, default 1.0]
import sys

import numpy as np

sys.path.insert(0, 'tools')
import colmap_bin as CB

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
SITE = 'E:/sitecapture-captures/ngv-video/balcony2-register/model/points3D.bin'
ENDS = {'west': (4.194, 0.344), 'east': (48.056, 51.906)}
DEEP = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
HLO, HHI = 5.20, 8.10

P = CB.read_points3d(SITE)
q = P['xyz'] - O
u, dd, hv = q @ HU, q @ HD, q[:, 1]

for end, (uF, uB) in ENDS.items():
    s = 1.0 if uB > uF else -1.0
    depth = (u - uF) * s
    sel = np.logical_and.reduce([depth > DEEP, depth < abs(uB - uF) + 0.3,
                                 dd > 1.0, dd < 14.4, hv > HLO, hv < HHI])
    idx = np.nonzero(sel)[0]
    print('')
    print('%s end, points more than %.1f m behind the face: %d' % (end.upper(), DEEP, len(idx)))
    if len(idx) < 6:
        print('   too few to look for a hole')
        continue
    hs = np.sort(hv[idx])
    R = float(hs[-1] - hs[0])
    gaps = np.diff(hs)
    order = np.argsort(gaps)[::-1]
    n = len(hs)
    print('   heights run %.2f to %.2f, median track %d, median error %.2f px'
          % (hs[0], hs[-1], int(np.median(P['track_len'][idx])), float(np.median(P['err'][idx]))))
    print('')
    print('     gap    from      to     chance a random scatter of %d over %.2f m makes one this big' % (n, R))
    for k in order[:3]:
        g = float(gaps[k])
        pr = n * (1.0 - g / R) ** (n - 1) if R > 0 else 1.0
        print('   %6.3f  %6.3f  %6.3f    %.2e %s'
              % (g, hs[k], hs[k + 1], pr, '  <- not sampling noise' if pr < 0.01 else ''))
    k = int(order[0])
    lo = hs[hs <= hs[k]]
    hi = hs[hs >= hs[k + 1]]
    print('')
    print('   below the hole: %d points, h %.2f to %.2f' % (len(lo), lo.min(), lo.max()))
    print('   above the hole: %d points, h %.2f to %.2f' % (len(hi), hi.min(), hi.max()))
    print('   so IF those two are a sill and a head, the opening is %.2f m clear, %.2f to %.2f'
          % (float(hs[k + 1] - hs[k]), float(hs[k]), float(hs[k + 1])))
    print('   the model draws this recess open from 5.30 to 8.08 with nothing inside it.')
