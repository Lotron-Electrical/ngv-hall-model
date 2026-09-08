# The built end gallery (ENDW floors, slab, rails, face) drawn into any posed frame that sees an end
# of the hall, the crop turned upright, so the real tiers can be read against the built ones.
#   python tools/end_overlay2.py <class> <frame> <east|west> [uFace] [scale]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
cls, k, side = sys.argv[1:4]
FLOORS = [3.99, 6.33, 8.34]; SLAB = 0.26; RAILS = [0.89, 0.89, 1.07]; D = 15.364
uB = 51.906 if side == 'east' else 0.344; s = 1 if side == 'east' else -1
uF = float(sys.argv[4]) if len(sys.argv) > 4 else uB - s * 3.85
sc = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
cam, p = U.load_class(cls)[k]; im = cv2.imread(p)
def pt(u, d, h):
    x, y, z = cam.project(np.asarray([world(u, d, h)]))
    return (int(round(x[0])), int(round(y[0]))) if z[0] > 0 else None
def line(a, b, col, w=1):
    if a and b: cv2.line(im, a, b, col, w, cv2.LINE_AA)
for i, hf in enumerate(FLOORS):
    line(pt(uF, 0, hf), pt(uF, D, hf), (0, 255, 255), 2)
    line(pt(uF, 0, hf - SLAB), pt(uF, D, hf - SLAB), (0, 255, 255), 1)
    line(pt(uF, 0, hf + RAILS[i]), pt(uF, D, hf + RAILS[i]), (255, 0, 255), 1)
for dd in (0, D): line(pt(uF, dd, 0), pt(uF, dd, 12), (0, 200, 0), 1)
line(pt(uB, 0, 10.0), pt(uB, D, 10.0), (255, 255, 255), 1)
for hz in (2, 4, 6, 8, 10, 12):   # a height scale on the plate end, every 2 m
    line(pt(uB, 0, hz), pt(uB, D, hz), (200, 200, 200), 1)
    q = pt(uB, D / 2, hz)
    if q: cv2.putText(im, str(hz), q, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
ps = [pt(uB, 0, 0), pt(uB, D, 0), pt(uB, 0, 12.5), pt(uB, D, 12.5), pt(uF, 0, 0), pt(uF, D, 12.5)]
xs = [q[0] for q in ps if q]; ys = [q[1] for q in ps if q]
x0, x1 = max(0, min(xs) - 60), min(im.shape[1], max(xs) + 60); y0, y1 = max(0, min(ys) - 60), min(im.shape[0], max(ys) + 60)
c = im[y0:y1, x0:x1]
down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
if abs(down[1]) < abs(right[1]): c = cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE)
elif down[1] < 0: c = cv2.rotate(c, cv2.ROTATE_180)
c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
out = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/end-%s-%s.jpg' % (side, k)
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, c.shape)
