# Height lines on an end face plane (u = face), d 0..15.36, drawn into a posed frame, upright crop.
#   python tools/end_lines.py <class> <frame> <east|west> <h_csv> [uFace] [hmin,hmax] [dmin,dmax]
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
cls, k, side = sys.argv[1:4]; hs = [float(a) for a in sys.argv[4].split(',')]
uF = float(sys.argv[5]) if len(sys.argv) > 5 else (48.056 if side == 'east' else 4.194)
zoom = len(sys.argv) > 6
hc = [float(a) for a in sys.argv[6].split(',')] if zoom else [0, 13.5]
dc = [float(a) for a in sys.argv[7].split(',')] if len(sys.argv) > 7 else [0, 15.364]
cam, p = U.load_class(cls)[k]; im = cv2.imread(p)
def pt(u, d, h):
    x, y, z = cam.project(np.asarray([world(u, d, h)]))
    if z[0] <= 0 or abs(x[0]) > 3 * cam.w or abs(y[0]) > 3 * cam.h: return None
    return (int(round(x[0])), int(round(y[0])))
def line(a, b, col, w=1):
    if a and b: cv2.line(im, a, b, col, w, cv2.LINE_AA)
for hz in hs:
    line(pt(uF, dc[0], hz), pt(uF, dc[1], hz), (0, 255, 255), 1 if zoom else 2)
    q = pt(uF, dc[0] + 0.3, hz)
    if q: cv2.putText(im, '%g' % hz, q, cv2.FONT_HERSHEY_SIMPLEX, 0.5 if zoom else 0.7, (0, 255, 255), 1 if zoom else 2)
for dd in (np.arange(0, 15.5, 0.5) if zoom else range(0, 16)):
    line(pt(uF, dd, hc[0]), pt(uF, dd, hc[1]), (255, 0, 255), 2 if dd % 5 == 0 else 1)
    q = pt(uF, dd, hc[0] + 0.15 if zoom else 12.5)
    if q and dd % (1 if zoom else 5) == 0: cv2.putText(im, 'd%g' % dd, q, cv2.FONT_HERSHEY_SIMPLEX, 0.5 if zoom else 0.7, (255, 0, 255), 1 if zoom else 2)
ps = [pt(uF, d, h) for d in dc for h in hc]
xs = [q[0] for q in ps if q]; ys = [q[1] for q in ps if q]
m = 20 if zoom else 60
x0, x1 = max(0, min(xs) - m), min(im.shape[1], max(xs) + m); y0, y1 = max(0, min(ys) - m), min(im.shape[0], max(ys) + m)
c = im[y0:y1, x0:x1]
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) < abs(right[1]): c = cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE)
elif down[1] > 0: c = cv2.rotate(c, cv2.ROTATE_180)
sc = min(3.0 if zoom else 2.0, 1300 / max(c.shape)); c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/'
out = S + 'lines-%s-%s%s.jpg' % (side, k, '-zoom' if zoom else ''); cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, c.shape)
