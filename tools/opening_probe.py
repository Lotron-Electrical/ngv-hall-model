# Zooms one north opening in a posed frame and draws, in the frame's own projection, the sim's opening rectangle
# (yellow) and a ladder of heights on the corridor's back wall (cyan, labelled), so what is really behind the wall
# can be read off against the built numbers.
#   python tools/opening_probe.py <class> <frame> <opening 0-11> [back_d] [out.jpg]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
cname, fr, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
backd = float(sys.argv[4]) if len(sys.argv) > 4 else -2.99   # openDepth 0.9 + corridor width 2.0 behind the face
out = sys.argv[5] if len(sys.argv) > 5 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/open%d-%s.jpg' % (k, fr)
cam, ip = U.load_class(cname)[fr]; im = cv2.imread(ip)
u0, u1 = OPEN[k]; H0, H1 = 8.99, 11.35
def p(u, d, h):
    x, y, z = cam.project(np.asarray([O + u * HU + d * HD + np.array([0, h, 0])]))
    return None if z[0] <= 0.3 else (float(x[0]), float(y[0]))
def line(a, b, col, w=2):
    if a and b: cv2.line(im, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), col, w, cv2.LINE_AA)
pts = []
for h in (H0, H1):
    for u in (u0, u1): pts.append(p(u, -0.09, h))
line(pts[0], pts[1], (0, 255, 255)); line(pts[2], pts[3], (0, 255, 255)); line(pts[0], pts[2], (0, 255, 255)); line(pts[1], pts[3], (0, 255, 255))
for h in [9.5, 10.0, 10.5, 11.0, 11.4, 12.0, 12.6, 13.2]:
    a, b = p(u0, backd, h), p(u1, backd, h)
    if a and b:
        col = (0, 200, 255) if abs(h - 11.4) < 0.01 else (255, 255, 0)
        line(a, b, col, 3 if abs(h - 11.4) < 0.01 else 2)
        cv2.putText(im, '%.1f' % h, (int(b[0]) + 6, int(b[1]) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
xs = [q[0] for q in pts if q] + [p(u, backd, 13.2)[0] for u in (u0, u1) if p(u, backd, 13.2)]
ys = [q[1] for q in pts if q] + [p(u, backd, 13.2)[1] for u in (u0, u1) if p(u, backd, 13.2)]
m = 90; x0, x1i = max(0, int(min(xs)) - m), min(im.shape[1], int(max(xs)) + m); y0, y1i = max(0, int(min(ys)) - m), min(im.shape[0], int(max(ys)) + m)
c = im[y0:y1i, x0:x1i]; s = max(1, int(700 / max(1, max(c.shape[:2]) / 3)))
c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
q = cam.center - O
cv2.putText(c, '%s opening %d  camera u %.2f d %.2f h %.2f  back wall d %.2f' % (fr, k, q @ HU, q @ HD, q[1], backd), (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(out, c.shape, 'zoom', s)
