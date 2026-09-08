# Which posed cameras (walk, night, day4k) can see a point behind a north opening: the ray from the camera to the
# point must cross the wall face (d 0) inside the opening's box. Prints frame, pixel, camera.
#   python tools/lamp_seers.py u d h u0 u1 h0 h1
import sys, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
u, d, h, u0, u1, h0, h1 = map(float, sys.argv[1:8])
X = O + u * HU + d * HD + np.array([0, h, 0])
for cname in ('walk', 'night', 'day4k'):
    for k, (cam, _) in sorted(U.load_class(cname).items()):
        C = cam.center; q = C - O; dc = q @ HD
        if dc <= 0.2: continue
        t = dc / (dc - d); P = C + t * (X - C); pq = P - O
        if not (u0 < pq @ HU < u1 and h0 < pq[1] < h1): continue
        x, y, z = cam.project(np.asarray([X]))
        if z[0] <= 0 or not (0 <= x[0] < cam.w and 0 <= y[0] < cam.h): continue
        print('%s %s px %.0f,%.0f  camera u %.2f d %.2f h %.2f  range %.1f' % (cname, k, x[0], y[0], q @ HU, dc, q[1], np.linalg.norm(X - C)))
