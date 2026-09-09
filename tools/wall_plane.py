# 2026-09-10: THE HALL'S OWN WIDTH, MEASURED HEIGHT BAND BY HEIGHT BAND, WITH THE NORTH WALL AS CONTROL.
#
# dSouth 15.364 is the south wall of this hall and it has never been moved by a measurement. The reason is
# in index.html and it is a good one: when the tapestries were placed, the only cloud points that could
# test the wall were bare stone, and "at the heights that matter they are both sparse and contaminated by
# the fixtures that hang a metre off this wall". Every balcony d, the end walls' 15.364 span and the whole
# hall width rest on that untested number.
#
# WHAT THE OLD LOOK MISSED. "At the heights that matter" meant the tapestry band, four to eight metres up,
# which is exactly where the lighting truss, the speakers and the hanging fixtures live. The wall does not
# stop there. Above about nine metres it is bare ashlar with nothing hung on it, and nobody has asked that
# part of the cloud where it is. So this reports the wall band by band instead of pooling it: a band full
# of fixtures declares itself as a wide spread and a long tail toward the hall, and a clean band does not.
#
# THE CONTROL IS THE POINT OF THE DESIGN. The north wall face is already measured by instruments that share
# nothing with a point cloud: the near-far V test put it on d -0.030 with 1 to 2 mm of half-to-half
# agreement (tools/depth_v.py). So the same fit is run on the north wall first. If it reproduces a number
# already known by other means, its answer on the south wall is worth something; if it does not, nothing
# here is worth reading and that is the finding.
#
# AND A SPLIT, because a plane fit always returns a plane. The points are halved west against east along
# the hall. A real flat wall gives the same d from both halves; a scatter dominated by hanging objects
# does not, because the objects are not spread evenly.
#   python tools/wall_plane.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import colmap_bin as CB

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
SITE = 'E:/sitecapture-captures/ngv-video/balcony2-register/model/points3D.bin'
WALLS = {'north (control, known d -0.030)': (-0.053, -1.0, 1.0, 1),
         'south (dSouth 15.364, never moved)': (15.364, -1.0, 1.0, -1)}
ULO, UHI = 6.0, 46.0

P = CB.read_points3d(SITE)
q = P['xyz'] - O
u, dd, hv = q @ HU, q @ HD, q[:, 1]
print('site cloud: %d points' % len(u))

for name, (d0, lo, hi, into) in WALLS.items():
    print('')
    print(name)
    print('     h band     pts   median d    spread(MAD)   west half   east half   halves apart')
    rows = []
    for h0 in np.arange(1.0, 13.0, 1.0):
        sel = np.logical_and.reduce([u > ULO, u < UHI, hv >= h0, hv < h0 + 1.0,
                                     dd > d0 + lo, dd < d0 + hi])
        n = int(sel.sum())
        if n < 40:
            print('   %4.1f-%4.1f   %5d   too few' % (h0, h0 + 1, n))
            continue
        ds = dd[sel]
        us = u[sel]
        med = float(np.median(ds))
        mad = float(np.median(np.abs(ds - med)))
        cut = 0.5 * (ULO + UHI)
        w = ds[us < cut]
        e = ds[us >= cut]
        mw = float(np.median(w)) if len(w) > 20 else float('nan')
        me = float(np.median(e)) if len(e) > 20 else float('nan')
        rows.append((h0, n, med, mad, mw, me))
        print('   %4.1f-%4.1f   %5d   %+8.3f      %6.3f     %+8.3f   %+8.3f     %6.3f'
              % (h0, h0 + 1, n, med, mad, mw, me, abs(mw - me)))
    clean = [r for r in rows if r[3] < 0.060 and abs(r[4] - r[5]) < 0.060]
    print('')
    if not clean:
        print('   NO band is both tight and consistent between the halves; this wall is not measured here.')
        continue
    a = np.array([r[2] for r in clean])
    hb = np.array([r[0] + 0.5 for r in clean])
    print('   %d clean bands (spread under 60 mm AND halves within 60 mm): h %s'
          % (len(clean), ', '.join('%.1f' % v for v in hb)))
    print('   they put this wall on d %+.3f, band to band spread %.3f m, drawn %+.3f, so %+.3f m off'
          % (float(np.median(a)), float(a.max() - a.min()), d0, float(np.median(a)) - d0))
    if len(clean) >= 3:
        k, b = np.polyfit(hb, a, 1)
        print('   lean over height: %+.4f m per metre (%.0f mm across the %.0f m of clean band)'
              % (k, 1000 * k * (hb.max() - hb.min()), hb.max() - hb.min()))
