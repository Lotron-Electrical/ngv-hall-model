# Hall-frame pose (u, d, h, yaw target, pitch, hfov) of a posed frame, for placing the sim camera on it.
#   python tools/pose_of.py <class> <frame>
import sys, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cls, k = sys.argv[1], sys.argv[2]
cam, p = U.load_class(cls)[k]
C = cam.center; q = C - O; u, d, h = q @ HU, q @ HD, q[1]
f = cam.R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]
pitch = np.degrees(np.arcsin(fh)); horiz = np.hypot(fu, fd)
# focal from the projection of two points on the optical axis offset
x0, y0, _ = cam.project(np.asarray([C + f * 10]))
x1, y1, _ = cam.project(np.asarray([C + f * 10 + (cam.R.T @ np.array([1.0, 0, 0])) * 1]))
fx = np.hypot(x1[0] - x0[0], y1[0] - y0[0]) * 10
print('frame', k, 'u %.2f d %.2f h %.2f' % (u, d, h), 'fwd u %.3f d %.3f' % (fu / horiz, fd / horiz), 'pitch %.1f deg' % pitch, 'w %d h %d fx %.0f hfov %.1f vfov %.1f' % (cam.w, cam.h, fx, 2 * np.degrees(np.arctan(cam.w / 2 / fx)), 2 * np.degrees(np.arctan(cam.h / 2 / fx))), 'file', p)
