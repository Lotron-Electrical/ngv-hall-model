# The raw pixels inside one north opening, upright and stretched, so what is behind the wall can be SEEN.
# Left: as shot. Right: the same crop with its own levels stretched (2nd..98th percentile) and gamma 0.55.
#   python tools/opening_look.py <class> <frame> <opening 0-11> [out.jpg]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
cname, fr, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/look%d-%s.jpg' % (k, fr)
cam, ip = U.load_class(cname)[fr]; im = cv2.imread(ip)
u0, u1 = OPEN[k]
P = lambda u, d, h: cam.project(np.asarray([O + u * HU + d * HD + np.array([0, h, 0])]))[:2]
xs, ys = [], []
for u in (u0, u1):
    for h in (8.99, 11.35):
        x, y = P(u, -0.09, h); xs.append(float(x[0])); ys.append(float(y[0]))
m = 30; x0, x1i = max(0, int(min(xs)) - m), min(im.shape[1], int(max(xs)) + m); y0, y1i = max(0, int(min(ys)) - m), min(im.shape[0], int(max(ys)) + m)
c = im[y0:y1i, x0:x1i]
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) >= abs(right[1]): rot = None if down[1] < 0 else cv2.ROTATE_180
else: rot = cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE
if rot is not None: c = cv2.rotate(c, rot)
z = max(1, int(560 / max(1, max(c.shape[:2]))) + 3); c = cv2.resize(c, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY); lo, hi = np.percentile(g, 2), np.percentile(g, 98)
s = np.clip((c.astype(np.float32) - lo) / max(1.0, hi - lo), 0, 1) ** 0.55
s = (s * 255).astype(np.uint8)
cv2.putText(c, 'as shot', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
cv2.putText(s, 'levels %.0f-%.0f, gamma 0.55' % (lo, hi), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
q = cam.center - O; pair = np.hstack([c, s])
cv2.putText(pair, '%s opening %d (u %.2f-%.2f)  camera u %.2f d %.2f h %.2f' % (fr, k, u0, u1, q @ HU, q @ HD, q[1]), (8, pair.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
cv2.imwrite(out, pair, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(out, pair.shape, 'levels', round(float(lo)), round(float(hi)))
