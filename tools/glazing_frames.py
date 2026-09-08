# Which posed frames see the pleated glazing obliquely, and where would the declared sawtooth's
# vertical edges (fin faces, near vertices, apexes) fall in them? Writes overlay images so the
# declared fold depth can be checked against the real mullions and fins.
#   python tools/glazing_frames.py [depthScale ...]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/glaz/'
import os; os.makedirs(OUT, exist_ok=True)
# the declared sawtooth (glazing.json, GLB frame at h 1 m, d already less the 0.223 correction)
poly = [[18.127, 15.578], [18.127, 17.678], [18.527, 17.678], [18.527, 16.118], [20.278, 17.668], [22.028, 16.118], [22.028, 17.678], [22.428, 17.678], [22.428, 16.118], [24.179, 17.668], [25.93, 16.118], [25.93, 17.678], [26.33, 17.678], [26.33, 16.118], [28.081, 17.668], [29.832, 16.118], [29.832, 17.678], [30.232, 17.678], [30.232, 16.118], [31.983, 17.668], [33.734, 16.118], [33.734, 17.678], [34.134, 17.678], [34.134, 15.578]]
FACE = 15.364
scales = [float(a) for a in sys.argv[1:]] or [1.0]
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
rows = []
for cls in ('walk', 'night'):
    for k, (cam, p) in U.load_class(cls).items():
        C = cam.center; q = C - O; u = q @ HU; d = q @ HD
        f = cam.R.T @ np.array([0, 0, 1.0]); fu = f @ HU; fd = f @ HD
        # the glazing centre (u 26.2, d 15.36, h 5) must be in front and within 45 deg of the axis
        v = world(26.2, 15.36, 5.0) - C; v = v / np.linalg.norm(v)
        if v @ f < np.cos(np.radians(45)): continue
        obl = abs(u - 26.2) / max(1e-3, 15.36 - d)   # oblique ratio
        if d > 12: continue
        rows.append((obl, cls, k, u, d, q[1], p, cam))
rows.sort(reverse=True)
print(len(rows), 'frames see the glazing;', 'most oblique:')
for r in rows[:12]: print('  %s %s obl %.2f u %.1f d %.1f h %.1f' % (r[1], r[2], r[0], r[3], r[4], r[5]))
def project(cam, X):
    u, v, z = cam.project(np.asarray([X]))
    if z[0] <= 0.05: return None
    return (float(u[0]), float(v[0]))
chosen = []
def centred(r):
    cam = r[7]; u, v, z = cam.project(np.asarray([world(26.2, 15.36, 4.0), world(20.0, 15.36, 4.0), world(32.0, 15.36, 4.0)]))
    return bool(np.all(z > 0) and np.all(u > cam.w * 0.1) and np.all(u < cam.w * 0.9) and np.all(v > cam.h * 0.1) and np.all(v < cam.h * 0.9))
for lo, hi in ((0.25, 0.6), (0.6, 1.1), (1.1, 2.0), (2.0, 3.5)):
    band = [r for r in rows if lo <= r[0] < hi and r[4] < 9 and centred(r)]
    band.sort(key=lambda r: -cv2.Laplacian(cv2.resize(cv2.imread(r[6], 0), None, fx=0.3, fy=0.3), cv2.CV_32F).var())
    chosen += band[:2]
for r in chosen:
    obl, cls, k, u, d, h, p, cam = r
    im = cv2.imread(p)
    for s in scales:
        col = {1.0: (0, 255, 255)}.get(s, (0, 128, 255) if s < 1 else (255, 0, 255))
        for (pu, pd) in poly:
            pd2 = FACE + (pd - 0.223 - FACE) * s   # scale the depth about the corrected face
            a = project(cam, world(pu, pd2, 0.2)); b = project(cam, world(pu, pd2, 11.5))
            if a is None or b is None: continue
            cv2.line(im, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), col, 1)
    small = cv2.resize(im, None, fx=0.75, fy=0.75)
    cv2.putText(small, '%s obl %.2f u %.1f d %.1f' % (k, obl, u, d), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.imwrite(OUT + '%s.jpg' % k, small, [cv2.IMWRITE_JPEG_QUALITY, 88])
print('wrote', OUT)
