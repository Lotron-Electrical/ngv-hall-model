# The sharpest posed frames (walk, night, day4k) that hold a target point of the hall near the
# middle of the frame from at least a given distance, with the pose line tools/pose-shot.mjs takes.
#   python tools/pose_frames_for.py <u> <d> <h> [min_dist] [n]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
tu, td, th = map(float, sys.argv[1:4]); mind = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0; n = int(sys.argv[5]) if len(sys.argv) > 5 else 4
T = world(tu, td, th); rows = []
for cls in ('walk', 'night', 'day4k'):
    for k, (cam, p) in U.load_class(cls).items():
        C = cam.center; v = T - C; dist = np.linalg.norm(v)
        if dist < mind: continue
        x, y, z = cam.project(np.asarray([T]))
        if z[0] <= 0 or x[0] < cam.w * 0.3 or x[0] > cam.w * 0.7 or y[0] < cam.h * 0.25 or y[0] > cam.h * 0.75: continue
        g = cv2.imread(p, 0)
        if g is None: continue
        sharp = cv2.Laplacian(cv2.resize(g, None, fx=0.3, fy=0.3), cv2.CV_32F).var()
        q = C - O; u, d, h = q @ HU, q @ HD, q[1]
        f = cam.R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]; hor = np.hypot(fu, fd)
        x0, y0, _ = cam.project(np.asarray([C + f * 10])); x1, y1, _ = cam.project(np.asarray([C + f * 10 + (cam.R.T @ np.array([1.0, 0, 0]))]))
        fx = np.hypot(x1[0] - x0[0], y1[0] - y0[0]) * 10
        rows.append((sharp, cls, k, dist, u, d, h, fu / hor, fd / hor, np.degrees(np.arcsin(fh)), 2 * np.degrees(np.arctan(cam.h / 2 / fx)), cam.w, cam.h, p))
rows.sort(reverse=True)
print(len(rows), 'frames hold the target; sharpest:')
for r in rows[:n]:
    print('%s %s sharp %.0f dist %.1f | %d %d %.1f %.2f %.2f %.2f %.3f %.3f %.1f | %s' % (r[1], r[2], r[0], r[3], r[11], r[12], r[10], r[4], r[5], r[6], r[7], r[8], r[9], r[13]))
