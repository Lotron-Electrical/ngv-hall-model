# Posed frames that see a whole north opening (all four corners in frame, in front, margin from the edges), ranked
# by how much of the corridor behind it the sightline reaches. For measuring what is behind the wall.
#   python tools/find_openseers.py <class> <opening index 0-11 | all> [margin_px]
# THE FOLD (2026-09-10): the OpenCV radial polynomial, extrapolated far outside the calibrated field, folds a point
# 60 degrees off axis back into the frame (night w6_000085, opening 9: the four corners land at (941,507) to
# (1004,597) with a radial factor of 0.02 to -0.02, while the undistorted pinhole puts them at (-418,-1878)). The
# first run of this tool ranked that fold first for night. Every corner is now also required to sit inside the frame
# under the plain pinhole (no distortion), and the folds are counted.
import sys, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
cname = sys.argv[1]; ks = range(12) if sys.argv[2] == 'all' else [int(sys.argv[2])]; m = float(sys.argv[3]) if len(sys.argv) > 3 else 40
H0, H1 = 8.99, 11.35
CAMS = U.load_class(cname)
for k in ks:
  u0, u1 = OPEN[k]
  pts = np.array([O + u * HU + (-0.09) * HD + np.array([0, h, 0]) for u in (u0, u1) for h in (H0, H1)])
  rows = []; folds = 0
  for fr, (cam, ip) in CAMS.items():
    x, y, z = cam.project(pts)
    if (z <= 0.3).any() or (x < m).any() or (x > cam.w - m).any() or (y < m).any() or (y > cam.h - m).any(): continue
    D = pts - cam.center; zz = D @ cam.R[2]; px = cam.params[0] * (D @ cam.R[0]) / zz + cam.params[2]; py = cam.params[1] * (D @ cam.R[1]) / zz + cam.params[3]
    if (px < m).any() or (px > cam.w - m).any() or (py < m).any() or (py > cam.h - m).any(): folds += 1; continue
    C = cam.center; q = C - O
    # how high up the corridor back wall (d = -2.99) the ray through the OUTER head edge reaches
    slope = (H1 - q[1]) / (q @ HD + 0.99)
    reach = H1 + slope * 2.0
    span = float(np.hypot(x[0] - x[2], y[0] - y[2]))   # the opening's width in pixels
    rows.append((-span, fr, q @ HU, q @ HD, q[1], reach, span, ip))
  rows.sort()
  for r in rows[:12]: print('%-14s camera u %6.2f d %6.2f h %5.2f  head ray reaches h %5.2f at the back wall  opening %4.0f px wide' % (r[1], r[2], r[3], r[4], r[5], r[6]))
  print('opening %d: %d frames see the whole opening, %d folds rejected' % (k, len(rows), folds))
  if rows: print('best image:', rows[0][7])
