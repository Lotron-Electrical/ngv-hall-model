# Which posed frames of a class SEE a hall point (in frame, in front, within a range) and how square-on they look
# at the north wall. For picking frames that look into the openings.
#   python tools/find_seers.py <class> u d h [max_range] [min_dot]
import sys, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cname = sys.argv[1]; u, d, h = map(float, sys.argv[2:5])
maxr = float(sys.argv[5]) if len(sys.argv) > 5 else 12.0
mindot = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5
X = O + u * HU + d * HD + np.array([0, h, 0])
rows = []
for fr, (cam, ip) in U.load_class(cname).items():
    x, y, z = cam.project(np.asarray([X]))
    if z[0] <= 0.3 or not (0 <= x[0] < cam.w and 0 <= y[0] < cam.h): continue
    C = cam.center; rng = float(np.linalg.norm(X - C))
    if rng > maxr: continue
    fwd = cam.R.T @ np.array([0, 0, 1.0]); dot = float(-fwd @ HD)   # +1 = looking straight at the north wall
    if dot < mindot: continue
    q = C - O
    rows.append((rng, fr, q @ HU, q @ HD, q[1], dot, x[0], y[0]))
rows.sort()
for r in rows[:25]: print('%-16s range %5.2f  camera u %6.2f d %6.2f h %5.2f  squareness %.2f  px %5.0f,%5.0f' % (r[1], r[0], r[2], r[3], r[4], r[5], r[6], r[7]))
print(len(rows), 'frames')
