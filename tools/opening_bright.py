# 2026-09-09: how bright is a north opening, in the REAL hall, measured against the stone beside it?
# From the hall the room behind the wall is only ever seen through the twelve openings, so this ratio
# (opening mean / wall mean, same frame, same exposure) is the one thing about that room the floor
# imagery CAN measure. No renders, no poses beyond the ones already solved: it reads the frames only.
# Frames are dropped when the control stone is clipped (p95 = 255) or the opening is tiny.
#   python tools/opening_bright.py <class> [min_px]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
cls = sys.argv[1]; minpx = float(sys.argv[2]) if len(sys.argv) > 2 else 60
frames = U.load_class(cls)
rows = []
for fr, (cam, ip) in frames.items():
    img = None
    for oi, (u0, u1) in enumerate(OPEN):
        pts = np.array([O + uu * HU + (-0.09) * HD + np.array([0, hv, 0]) for uu, hv in ((u0, 11.35), (u1, 11.35), (u1, 8.99), (u0, 8.99))])
        cpt = np.array([O + uu * HU + (-0.09) * HD + np.array([0, hv, 0]) for uu, hv in ((u0, 8.85), (u1, 8.85), (u1, 7.55), (u0, 7.55))])
        x, y, z = cam.project(pts); cx, cy, cz = cam.project(cpt)
        if (z <= 0.3).any() or (cz <= 0.3).any(): continue
        if (x < 30).any() or (x > cam.w - 30).any() or (y < 30).any() or (y > cam.h - 30).any(): continue
        if (cx < 5).any() or (cx > cam.w - 5).any() or (cy < 5).any() or (cy > cam.h - 5).any(): continue
        span = float(np.hypot(x[0] - x[1], y[0] - y[1]))
        if span < minpx: continue
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None: break
        def band(px, py):
            qi = np.round(np.stack([px, py], 1)).astype(np.int32)
            m = np.zeros(img.shape[:2], np.uint8); cv2.fillPoly(m, [qi], 255)
            m = cv2.erode(m, np.ones((5, 5), np.uint8))
            g = img[m > 0]
            return g if g.size >= 200 else None
        go, gw = band(x, y), band(cx, cy)
        if go is None or gw is None: continue
        if np.percentile(gw, 95) >= 254 or np.percentile(go, 95) >= 254: continue    # clipped highlights
        if gw.mean() < 12: continue                                                  # control in the dark
        rows.append((fr, oi, span, go.mean(), gw.mean(), go.mean() / gw.mean(), float(np.percentile(go, 95) - np.percentile(go, 5)), float(np.percentile(gw, 95) - np.percentile(gw, 5))))
if not rows: raise SystemExit('no usable frame/opening pair in class ' + cls)
r = np.array([[a[2], a[3], a[4], a[5], a[6], a[7]] for a in rows])
print('%s: %d usable frame/opening pairs, %d frames' % (cls, len(rows), len({a[0] for a in rows})))
print('opening/wall brightness ratio: median %.2f   p25 %.2f   p75 %.2f' % tuple(np.percentile(r[:, 3], [50, 25, 75])))
print('opening internal spread (p95-p5): median %.1f levels; the stone control: median %.1f' % (np.median(r[:, 4]), np.median(r[:, 5])))
print('opening spread / wall spread: median %.2f' % np.median(r[:, 4] / np.maximum(r[:, 5], 1e-6)))
w = np.argsort(-r[:, 0])[:8]
for i in w: a = rows[i]; print('  %-14s opening %2d  %4.0f px  opening mean %5.1f  wall mean %5.1f  ratio %.2f  spread %4.1f' % (a[0], a[1], a[2], a[3], a[4], a[5], a[6]))
