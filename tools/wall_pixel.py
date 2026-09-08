# A pixel of a posed frame -> the point on a long wall's plane it looks at (hall frame u, h).
import sys, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
spec, side = sys.argv[1], sys.argv[2]; pix = sys.argv[3:]
cname, fr = spec.split(':'); cam, ipath = U.load_class(cname)[fr]
dwall = -0.09 if side == 'north' else 15.364
p = cam.params
if cam.model == 'PINHOLE': fx, fy, cx, cy = p; k1 = k2 = p1 = p2 = 0.0
else: fx, fy, cx, cy, k1, k2, p1, p2 = p
def undistort(xd, yd):
    x, y = xd, yd
    for _ in range(30):
        r2 = x * x + y * y; rad = 1 + k1 * r2 + k2 * r2 * r2
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x); dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        x = (xd - dx) / rad; y = (yd - dy) / rad
    return x, y
C = cam.center
print('%s %s: camera u %.2f d %.2f h %.2f; image %dx%d' % (cname, fr, (C - O) @ HU, (C - O) @ HD, C[1] - O[1], cam.w, cam.h))
for pp in pix:
    if pp.startswith('crop:'):
        x0, y0, x1, y1 = map(int, pp[5:].split(',')); im = cv2.imread(ipath)
        out = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/crop-%s.jpg' % fr
        cv2.imwrite(out, im[y0:y1, x0:x1]); print('crop', out, im.shape); continue
    px, py = map(float, pp.split(','))
    xn, yn = undistort((px - cx) / fx, (py - cy) / fy)
    D = cam.R.T @ np.array([xn, yn, 1.0])
    dC = (C - O) @ HD; dD = D @ HD
    if abs(dD) < 1e-6: print(pp, 'parallel'); continue
    t = (dwall - dC) / dD
    if t <= 0: print(pp, 'wall behind the camera'); continue
    X = C + t * D
    print('%s -> u %.2f h %.2f (range %.1f m)' % (pp, (X - O) @ HU, X[1] - O[1], t))
