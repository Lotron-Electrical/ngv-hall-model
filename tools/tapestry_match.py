# Where the real frame holds a tapestry against where the sim draws it: the sim half's tapestry crop
# (the NGV image in the pose's own perspective) template-matched in the real half of a pose pair, the
# best offset converted to metres along and up the wall.   python tools/tapestry_match.py <position> <prefix> class:frame
import sys, json, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
pos, prefix, spec = sys.argv[1:4]; cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]
T = [t for t in json.load(open('tools/tapestries.json'))['tapestries'] if t['position'] == pos][0]
c = np.array(T['corners']) - O; uu = c @ HU; hv = c[:, 1]; dw = -0.09 if 'north' in pos else 15.364
u0, u1, h0, h1 = uu.min(), uu.max(), hv.min(), hv.max(); um, hm = (u0 + u1) / 2, (h0 + h1) / 2
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
quad = [px(u, dw, h) for u, h in ((u0, h0), (u1, h0), (u1, h1), (u0, h1))]
if any(q is None for q in quad): print(pos, k, 'behind the camera'); sys.exit()
xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
x0, x1 = int(min(xs)), int(max(xs)); y0, y1 = int(min(ys)), int(max(ys))
Hr, Wr = real.shape[:2]
if x0 < 0 or y0 < 0 or x1 > Wr or y1 > Hr or x1 - x0 < 30 or y1 - y0 < 30: print(pos, k, 'tapestry not wholly in frame'); sys.exit()
tpl = sim[y0:y1, x0:x1]; m = 320
sx0, sy0 = max(0, x0 - m), max(0, y0 - m); sx1, sy1 = min(Wr, x1 + m), min(Hr, y1 + m)
search = real[sy0:sy1, sx0:sx1]
g = lambda im: cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (0, 0), 3)
res = cv2.matchTemplate(g(search), g(tpl), cv2.TM_CCOEFF_NORMED)
_, best, _, loc = cv2.minMaxLoc(res); dx, dy = loc[0] + sx0 - x0, loc[1] + sy0 - y0
res2 = cv2.matchTemplate(search, tpl, cv2.TM_CCOEFF_NORMED); _, best2, _, loc2 = cv2.minMaxLoc(res2); dx2, dy2 = loc2[0] + sx0 - x0, loc2[1] + sy0 - y0
pc = np.array(px(um, dw, hm)); pu = np.array(px(um + 1, dw, hm)); ph = np.array(px(um, dw, hm + 1))
A = np.column_stack([pu - pc, ph - pc])
du, dh = np.linalg.solve(A, [dx, dy]); du2, dh2 = np.linalg.solve(A, [dx2, dy2])
print('%s %s: template %dx%d; grey match %.2f at (%+d,%+d) px = real %+.2f m in u, %+.2f m in h | colour match %.2f at (%+d,%+d) = %+.2f, %+.2f' % (
    pos, k, x1 - x0, y1 - y0, best, dx, dy, du, dh, best2, dx2, dy2, du2, dh2))
