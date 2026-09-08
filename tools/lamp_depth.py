# The corridor downlight's position from several accepted day4k frames: the brightest blob near the predicted pixel
# in each frame gives a ray; the rays' least-squares intersection is the lamp. Prints per-frame blob and the fix.
#   python tools/lamp_depth.py u d h win frame [frame ...]
import sys, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
u, d, h, win = map(float, sys.argv[1:5]); win = int(win); frames = sys.argv[5:]
X0 = O + u * HU + d * HD + np.array([0, h, 0])
cams = U.load_class('day4k'); IM = 'E:/sitecapture-captures/ngv-video/day4k/images/'
A = []; B = []
for k in frames:
    cam, _ = cams[k]; x, y, z = cam.project(np.asarray([X0])); px, py = int(x[0]), int(y[0])
    im = cv2.imread(IM + k + '.png', cv2.IMREAD_GRAYSCALE); c = im[py - win:py + win, px - win:px + win].astype(float)
    c = cv2.GaussianBlur(c, (5, 5), 0); iy, ix = np.unravel_index(np.argmax(c), c.shape)
    thr = c.max() * 0.7; m = c >= thr; ys, xs = np.nonzero(m); w = c[m] - thr * 0.99
    bx, by = px - win + (xs * w).sum() / w.sum(), py - win + (ys * w).sum() / w.sum()
    fx, fy, cx, cy, k1, k2, p1, p2 = cam.params; K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
    n = cv2.undistortPoints(np.array([[[bx, by]]], np.float32), K, np.array([k1, k2, p1, p2])).reshape(2)
    D = cam.R.T @ np.array([n[0], n[1], 1.0]); D /= np.linalg.norm(D); C = cam.center
    print('%s predicted %d,%d blob %.1f,%.1f peak %.0f (%d px)' % (k, px, py, bx, by, c.max(), m.sum()))
    P = np.eye(3) - np.outer(D, D); A.append(P); B.append(P @ C)
X = np.linalg.lstsq(np.sum(A, 0), np.sum(B, 0), rcond=None)[0]; q = X - O
res = [np.linalg.norm(P @ (X - C)) for P, C in zip(A, [cams[k][0].center for k in frames])]
print('lamp u %.3f d %.3f h %.3f  ray misses %s m' % (q @ HU, q @ HD, q[1], ' '.join('%.3f' % r for r in res)))
