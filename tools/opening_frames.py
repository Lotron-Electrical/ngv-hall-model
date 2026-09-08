# The posed frames that look INTO a north-wall opening: closest and most head-on first, and a crop
# of the opening from each of the best, upright.   python tools/opening_frames.py [n]
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/ref/openings/'; os.makedirs(S, exist_ok=True)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OPS = [[4.076, 5.332], [7.676, 8.932], [10.764, 12.020], [15.132, 16.388], [18.628, 19.876], [22.336, 23.592], [26.044, 27.300], [29.948, 31.196], [33.588, 34.836], [37.348, 38.596], [40.884, 42.140]]
best = []
for cls in ('walk', 'night'):
    for k, (cam, p) in U.load_class(cls).items():
        C = cam.center; f = cam.R.T @ np.array([0, 0, 1.0])
        for i, (a, b) in enumerate(OPS):
            T = world((a + b) / 2, -0.09, 10.2); v = T - C; dist = np.linalg.norm(v); v = v / dist
            if v @ f < np.cos(np.radians(30)): continue
            x, y, z = cam.project(np.asarray([T]))
            if z[0] <= 0 or x[0] < cam.w * 0.15 or x[0] > cam.w * 0.85 or y[0] < cam.h * 0.1 or y[0] > cam.h * 0.9: continue
            headon = abs(float(v @ HD))
            best.append((headon / dist, cls, k, i, dist, headon, p, cam))
best.sort(key=lambda r: -r[0])
seen = set()
for r in best:
    if len(seen) >= n: break
    sc, cls, k, i, dist, headon, p, cam = r
    if k in seen: continue
    seen.add(k)
    im = cv2.imread(p); a, b = OPS[i]
    pts = [world(uu, dd, hz) for uu in (a - 0.6, b + 0.6) for dd in (-0.09, 1.5) for hz in (8.4, 12.0)]
    x, y, z = cam.project(np.asarray(pts))
    x0, x1 = int(max(0, x.min())), int(min(cam.w, x.max())); y0, y1 = int(max(0, y.min())), int(min(cam.h, y.max()))
    c = im[y0:y1, x0:x1]
    down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
    if abs(down[1]) < abs(right[1]): c = cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif down[1] > 0: c = cv2.rotate(c, cv2.ROTATE_180)
    sc2 = 500 / max(c.shape[0], 1)
    c = cv2.resize(c, None, fx=sc2, fy=sc2, interpolation=cv2.INTER_CUBIC)
    out = S + '%s-op%d.jpg' % (k, i); cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print('%s %s opening %d dist %.1f headon %.2f -> %s %s' % (cls, k, i, dist, headon, out, c.shape))
