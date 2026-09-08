# 2026-09-09: the same opening/wall brightness test as tools/opening_bright.py, but on a sim render,
# using the SIM's own camera rather than the photograph's. Projecting the photograph's camera onto the
# render mis-places the quad by tens of pixels at steep pitches (the yaw is unstable when the camera
# looks nearly straight up), which made the first sim-side numbers untrustworthy. Here the quad is
# built from the very arguments pose-shot.mjs was given, so it lands exactly on the built opening.
#   python tools/sim_openings.py <sim.jpg> <W> <H> <vfov> <u> <d> <h> <fu> <fd> <pitch> <opening 0-11> [marked.jpg]
import sys, cv2, numpy as np
sim, W, H, vfov, u, d, h, fu, fd, pitch, oi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9]), float(sys.argv[10]), int(sys.argv[11])
mark = sys.argv[12] if len(sys.argv) > 12 else None
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.076,5.332],[7.676,8.932],[10.764,12.020],[15.132,16.388],[18.628,19.876],[22.336,23.592],[26.044,27.300],[29.948,31.196],[33.588,34.836],[37.348,38.596],[40.884,42.140],[44.508,45.756]]
cam = O + u * HU + d * HD + np.array([0.0, h, 0.0])          # the eye, exactly where the page put it
fwd_h = fu * HU + fd * HD                                    # the page's yaw comes from this horizontal aim
yaw = np.arctan2(-fwd_h[0], -fwd_h[2]); pr = np.radians(pitch)
F = np.array([-np.sin(yaw) * np.cos(pr), np.sin(pr), -np.cos(yaw) * np.cos(pr)])
R = np.array([np.cos(yaw), 0.0, -np.sin(yaw)]); Uv = np.cross(R, F)
ty = np.tan(np.radians(vfov) / 2); asp = W / H
def project(P):
    v = P - cam; z = v @ F
    return W / 2 * (1 + (v @ R) / z / (ty * asp)), H / 2 * (1 - (v @ Uv) / z / ty), z
def quad_of(hi, lo):
    u0, u1 = OPEN[oi]
    P = np.array([O + uu * HU + (-0.09) * HD + np.array([0, hv, 0]) for uu, hv in ((u0, hi), (u1, hi), (u1, lo), (u0, lo))])
    x, y, z = project(P)
    return np.stack([x, y], 1), z
qo, zo = quad_of(11.35, 8.99)      # the opening
qw, zw = quad_of(8.85, 7.55)       # the stone control right under the sill
img = cv2.imread(sim)
if img is None: raise SystemExit('no render at ' + sim)
sc = img.shape[1] / W
g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
def band(q, name):
    qi = np.round(q * sc).astype(np.int32)
    m = np.zeros(g.shape, np.uint8); cv2.fillPoly(m, [qi], 255); m = cv2.erode(m, np.ones((5, 5), np.uint8))
    v = g[m > 0]
    if v.size < 200: print('%-5s too few pixels (%d)' % (name, v.size)); return None
    a5, a50, a95 = np.percentile(v, [5, 50, 95])
    print('%-5s n %6d  mean %6.1f  p5 %5.1f  p50 %5.1f  p95 %5.1f  spread %5.1f' % (name, v.size, v.mean(), a5, a50, a95, a95 - a5))
    return v.mean(), a95 - a5
if (zo <= 0.3).any() or (zw <= 0.3).any(): raise SystemExit('opening behind the camera')
bo, bw = band(qo, 'open'), band(qw, 'wall')
if bo and bw: print('opening/wall ratio %.2f   spread ratio %.2f' % (bo[0] / max(bw[0], 1e-6), bo[1] / max(bw[1], 1e-6)))
if mark:
    cv2.polylines(img, [np.round(qo * sc).astype(np.int32)], True, (0, 255, 255), 2)
    cv2.polylines(img, [np.round(qw * sc).astype(np.int32)], True, (255, 128, 0), 2)
    cv2.imwrite(mark, img); print('wrote', mark)
