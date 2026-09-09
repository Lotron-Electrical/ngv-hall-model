# 2026-09-09: the openings' drawn sill and head (yellow) against the edge the fixed-point finder settles on
# (green), on one real frame. Proof for the reading rather than an argument about it.
#   python tools/open_levels_draw.py <class> <frame> <out.jpg>
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U; import edge_refine as ER
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
DN = -0.090
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
cls, k, out = sys.argv[1], sys.argv[2], sys.argv[3]
cam, ip = U.load_class(cls)[k]
img = cv2.imread(ip); g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
for name, hv in (('sill 8.99', 8.99), ('head 11.35', 11.35)):
    for oi, (u0, u1) in enumerate(OPENINGS):
        us = np.linspace(u0 + 0.15, u1 - 0.15, 13)
        pts = np.array([O + uu * HU + DN * HD + np.array([0, hv, 0]) for uu in us])
        up = np.array([O + uu * HU + DN * HD + np.array([0, hv + 0.25, 0]) for uu in us])
        x, y, z = cam.project(pts); xu, yu, zu = cam.project(up)
        ok = (z > 0.5) * (zu > 0.5) * (x > 20) * (x < cam.w - 20) * (y > 20) * (y < cam.h - 20)
        idx = np.flatnonzero(ok)
        if idx.size < 4: continue
        cv2.polylines(img, [np.round(np.stack([x[idx], y[idx]], 1)).astype(np.int32)], False, (0, 235, 255), 2)
        if oi == 0 or idx.size > 8:
            cv2.putText(img, name, (int(x[idx[0]]) + 4, int(y[idx[0]]) - 5), 0, 0.5, (0, 235, 255), 1)
        fx, fy = [], []
        for i in idx:
            vx, vy = xu[i] - x[i], yu[i] - y[i]; L = np.hypot(vx, vy)
            if L < 4: continue
            e = ER.find_edge(g, x[i], y[i], vx / L, vy / L, 0.25 / L, 0.14, min_contrast=10.0)
            if e is None: continue
            fx.append(x[i] + vx / L * e / (0.25 / L)); fy.append(y[i] + vy / L * e / (0.25 / L))
        if len(fx) >= 4:
            cv2.polylines(img, [np.round(np.stack([fx, fy], 1)).astype(np.int32)], False, (80, 255, 80), 2)
# these clips are hand-held and often sideways or inverted. Rather than reason about the pose, ask the
# projection itself which way is up IN THIS IMAGE: project a point and the point 1 m above it, and see
# which way the pair runs across the pixels.
a = np.array([O + 20.0 * HU + DN * HD + np.array([0, 6.0, 0])])
b = np.array([O + 20.0 * HU + DN * HD + np.array([0, 7.0, 0])])
ax, ay, _ = cam.project(a); bx, by, _ = cam.project(b)
dx, dy = float(bx[0] - ax[0]), float(by[0] - ay[0])
if abs(dy) >= abs(dx): rot = None if dy < 0 else cv2.ROTATE_180
else: rot = cv2.ROTATE_90_CLOCKWISE if dx > 0 else cv2.ROTATE_90_COUNTERCLOCKWISE
if rot is not None: img = cv2.rotate(img, rot)
cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 88]); print('wrote', out, img.shape)
