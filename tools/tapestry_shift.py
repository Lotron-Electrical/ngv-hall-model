# How far each tapestry sits from where the frames show it: on a pose pair (real | sim on the same pose),
# the saturated blob's centroid in a window round the sim's tapestry, real against sim, converted to
# metres along the wall (u) and up it (h) with the local projection scale.
#   python tools/tapestry_shift.py <position> <prefix> class:frame   (the pair <prefix>-pair.jpg must exist)
import sys, json, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
pos, prefix, spec = sys.argv[1:4]; cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]
T = [t for t in json.load(open('tools/tapestries.json'))['tapestries'] if t['position'] == pos][0]
c = np.array(T['corners']) - O; uu = c @ HU; hh_ = c[:, 1]; dw = -0.09 if 'north' in pos else 15.364
u0, u1, h0, h1 = uu.min(), uu.max(), hh_.min(), hh_.max(); um, hm = (u0 + u1) / 2, (h0 + h1) / 2
pair = cv2.imread('E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/%s-pair.jpg' % prefix); W = pair.shape[1] // 2
real, sim = pair[:, :W], pair[:, W:]
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0]); rot = None
if abs(down[1]) < abs(right[1]): rot = 'cw' if right[1] < 0 else 'ccw'
elif down[1] > 0: rot = '180'
def px(u, d, h):
    x, y, z = cam.project(np.asarray([world(u, d, h)])); x, y = float(x[0]), float(y[0])
    if z[0] <= 0: return None
    if rot == 'cw': return cam.h - 1 - y, x
    if rot == 'ccw': return y, cam.w - 1 - x
    if rot == '180': return cam.w - 1 - x, cam.h - 1 - y
    return x, y
box = [px(u, dw, h) for u in (u0 - 0.8, u1 + 0.8) for h in (h0 - 0.5, h1 + 0.8)]
if any(b is None for b in box): print(pos, k, 'behind the camera'); sys.exit()
xs = [b[0] for b in box]; ys = [b[1] for b in box]
x0, x1 = int(max(0, min(xs))), int(min(real.shape[1], max(xs))); y0, y1 = int(max(0, min(ys))), int(min(real.shape[0], max(ys)))
if x1 - x0 < 40 or y1 - y0 < 40: print(pos, k, 'window off frame'); sys.exit()
# the sim's tapestry: the projected quad itself (exact); the real's: the saturated component overlapping it most
quad = np.array([px(u, dw, h) for u, h in ((u0, h0), (u1, h0), (u1, h1), (u0, h1))], np.int32)
qm = np.zeros(real.shape[:2], np.uint8); cv2.fillPoly(qm, [quad], 1); qm = cv2.dilate(qm, np.ones((41, 41), np.uint8))
def blob(im):
    hsv = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2HSV); m = np.logical_and(hsv[:, :, 1] > 70, hsv[:, :, 2] > 40).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n < 2: return None
    ov = [np.logical_and(lab == i, qm[y0:y1, x0:x1] > 0).sum() for i in range(1, n)]
    i = 1 + int(np.argmax(ov)); return cen[i] + [x0, y0], st[i, cv2.CC_STAT_AREA], st[i]
r = blob(real)
ys_, xs_ = np.where(qm > 0); s = (np.array([xs_.mean(), ys_.mean()]), len(xs_), [0, 0, np.ptp(xs_), np.ptp(ys_)])
if r is None or s is None: print(pos, k, 'no blob'); sys.exit()
pc = np.array(px(um, dw, hm)); pu = np.array(px(um + 1, dw, hm)); ph = np.array(px(um, dw, hm + 1))
A = np.column_stack([pu - pc, ph - pc]); dpx = r[0] - s[0]
du, dh = np.linalg.solve(A, dpx)
print('%s %s: real blob %d px at (%.0f,%.0f) box %dx%d | sim blob %d px at (%.0f,%.0f) box %dx%d | real is %+.2f m in u, %+.2f m in h from the sim' % (
    pos, k, r[1], r[0][0], r[0][1], r[2][2], r[2][3], s[1], s[0][0], s[0][1], s[2][2], s[2][3], du, dh))
