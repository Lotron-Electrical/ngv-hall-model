# 2026-09-09: does an opening in the north wall LOOK like the real one, from the hall?
# The room behind that wall is only ever seen through these twelve holes, so from the hall its accuracy
# IS the pixel statistics inside them. This projects the opening rectangle (u0..u1 by h 8.99..11.35 on
# the wall face d -0.09) into a posed frame and into a sim render taken from that same pose, and
# compares what is inside the two quads. Mode "pose" prints the pose-shot arguments; "cmp" compares.
#   python tools/opening_stats.py pose <class> <frame>
#   python tools/opening_stats.py cmp  <class> <frame> <opening 0-11> <sim.jpg> [out.jpg]
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.076,5.332],[7.676,8.932],[10.764,12.020],[15.132,16.388],[18.628,19.876],[22.336,23.592],[26.044,27.300],[29.948,31.196],[33.588,34.836],[37.348,38.596],[40.884,42.140],[44.508,45.756]]
mode, cls, k = sys.argv[1], sys.argv[2], sys.argv[3]
cam, p = U.load_class(cls)[k]
C = cam.center; q = C - O; u, d, h = q @ HU, q @ HD, q[1]
f = cam.R.T @ np.array([0, 0, 1.0]); fu, fd, fh = f @ HU, f @ HD, f[1]; hor = np.hypot(fu, fd); pitch = np.degrees(np.arcsin(fh))
x0, y0, _ = cam.project(np.asarray([C + f * 10])); x1, y1, _ = cam.project(np.asarray([C + f * 10 + (cam.R.T @ np.array([1.0, 0, 0]))]))
fx = np.hypot(x1[0] - x0[0], y1[0] - y0[0]) * 10
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) >= abs(right[1]): rot = None if down[1] < 0 else cv2.ROTATE_180; W, H = cam.w, cam.h
else: rot = cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE; W, H = cam.h, cam.w
vfov = 2 * np.degrees(np.arctan(H / 2 / fx)); RW, RH = W, H
while RW > 1080 or RH > 1920: RW, RH = RW // 2, RH // 2      # the page renders 1080 wide at most
if mode == 'pose':
    print('%d %d %.2f %.3f %.3f %.3f %.4f %.4f %.2f' % (RW, RH, vfov, u, d, h, fu / hor, fd / hor, pitch)); raise SystemExit
oi = int(sys.argv[4]); simp = sys.argv[5]; out = sys.argv[6] if len(sys.argv) > 6 else None
u0, u1 = OPEN[oi]
pts = np.array([O + uu * HU + (-0.09) * HD + np.array([0, hv, 0]) for uu, hv in ((u0, 11.35), (u1, 11.35), (u1, 8.99), (u0, 8.99))])
px, py, pz = cam.project(pts)
def turn(x, y):
    if rot is None: return x, y
    if rot == cv2.ROTATE_180: return cam.w - 1 - x, cam.h - 1 - y
    if rot == cv2.ROTATE_90_CLOCKWISE: return cam.h - 1 - y, x
    return y, cam.w - 1 - x
quad = np.array([turn(a, b) for a, b in zip(px, py)], np.float32)
A = cv2.imread(p); A = cv2.rotate(A, rot) if rot is not None else A
B = cv2.imread(simp)
if B is None: raise SystemExit('no sim render at ' + simp)
sc = B.shape[1] / float(A.shape[1])
def stats(img, qd, name):
    qi = np.round(qd).astype(np.int32)
    m = np.zeros(img.shape[:2], np.uint8); cv2.fillPoly(m, [qi], 255)
    m = cv2.erode(m, np.ones((5, 5), np.uint8))          # stay off the reveal edges
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[m > 0]
    if g.size < 30: print('%-5s too few pixels (%d)' % (name, g.size)); return None
    a5, a50, a95 = np.percentile(g, [5, 50, 95])
    print('%-5s n %6d  mean %6.1f  p5 %5.1f  p50 %5.1f  p95 %5.1f  spread %5.1f' % (name, g.size, g.mean(), a5, a50, a95, a95 - a5))
    return g.mean(), a50, a95 - a5
ra = stats(A, quad, 'real'); rb = stats(B, quad * sc, 'sim')
if ra and rb: print('sim/real mean %.2fx   median %+.1f levels   spread %.2fx' % (rb[0] / max(ra[0], 1e-6), rb[1] - ra[1], rb[2] / max(ra[2], 1e-6)))
# the control: the stone wall face right under the sill, same u band. If the sim matches the real
# stone here, the exposure is comparable and the difference inside the opening is the room, not the light.
cpts = np.array([O + uu * HU + (-0.09) * HD + np.array([0, hv, 0]) for uu, hv in ((u0, 8.85), (u1, 8.85), (u1, 7.55), (u0, 7.55))])
cx, cy, cz = cam.project(cpts)
cq = np.array([turn(a, b) for a, b in zip(cx, cy)], np.float32)
ca_ = stats(A, cq, 'wallR'); cb_ = stats(B, cq * sc, 'wallS')
if ra and rb and ca_ and cb_:
    print('opening/wall ratio: real %.2f   sim %.2f' % (ra[0] / max(ca_[0], 1e-6), rb[0] / max(cb_[0], 1e-6)))
if out:
    def crop(img, qd, w):
        qi = np.round(qd).astype(np.int32)
        xa, ya = qi[:, 0].min(), qi[:, 1].min(); xb, yb = qi[:, 0].max(), qi[:, 1].max()
        pad = int(0.6 * max(xb - xa, yb - ya))
        xa, ya = max(0, xa - pad), max(0, ya - pad); xb, yb = min(img.shape[1], xb + pad), min(img.shape[0], yb + pad)
        c = img[ya:yb, xa:xb].copy(); cv2.polylines(c, [qi - [xa, ya]], True, (0, 255, 255), 2)
        return cv2.resize(c, (w, max(1, int(c.shape[0] * w / max(c.shape[1], 1)))))
    ca, cb = crop(A, quad, 520), crop(B, quad * sc, 520)
    top = max(ca.shape[0], cb.shape[0]); pair = np.zeros((top + 32, 1060, 3), np.uint8)
    pair[32:32 + ca.shape[0], :520] = ca; pair[32:32 + cb.shape[0], 540:] = cb
    cv2.putText(pair, 'REAL ' + k, (6, 22), 0, 0.6, (255, 255, 255), 1); cv2.putText(pair, 'SIM, same pose', (546, 22), 0, 0.6, (255, 255, 255), 1)
    cv2.imwrite(out, pair); print('wrote', out)
