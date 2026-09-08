# Every posed camera of a class: frame, u, d, h, forward (u,d,pitch deg).  python tools/cams_list.py <class> [h_min]
import sys, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cls = sys.argv[1]; hmin = float(sys.argv[2]) if len(sys.argv) > 2 else -9
for k, (cam, p) in sorted(U.load_class(cls).items()):
    C = cam.center; q = C - O; u, d, h = q @ HU, q @ HD, q[1]
    if h < hmin: continue
    f = cam.R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]
    print('%s u %.2f d %.2f h %.2f fwd %.2f %.2f pitch %.0f' % (k, u, d, h, fu, fd, np.degrees(np.arcsin(fh))))
