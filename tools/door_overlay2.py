# Like door_overlay.py but a half-metre u scale, an h scale, a tighter crop upscaled x2.
#   python tools/door_overlay2.py <north|south> <u0> <u1> <h> <class:frame> [class:frame ...]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
side, u0, u1, hz0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
dw = -0.09 if side == 'north' else 15.364
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/ref/doors/'
import os; os.makedirs(S, exist_ok=True)
for spec in sys.argv[5:]:
    cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]; im = cv2.imread(p)
    def pt(u, d, h):
        x, y, z = cam.project(np.asarray([world(u, d, h)])); return (int(round(x[0])), int(round(y[0]))) if z[0] > 0 else None
    def line(a, b, col, w=1):
        if a and b: cv2.line(im, a, b, col, w, cv2.LINE_AA)
    box = [pt(u0, dw, 0), pt(u1, dw, 0), pt(u1, dw, hz0), pt(u0, dw, hz0)]
    for i in range(4): line(box[i], box[(i + 1) % 4], (0, 255, 255), 2)
    for uu in np.arange(u0 - 3, u1 + 3.01, 0.5):
        a, b = pt(uu, dw, 0), pt(uu, dw, 3.5); line(a, b, (255, 0, 255), 1)
        if b and abs(uu - round(uu)) < 0.01: cv2.putText(im, '%g' % uu, b, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1)
    for hz in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        line(pt(u0 - 3, dw, hz), pt(u1 + 3, dw, hz), (0, 200, 0), 1)
    ps = [pt(u0 - 3, dw, 0), pt(u1 + 3, dw, 0), pt(u0 - 3, dw, 3.5), pt(u1 + 3, dw, 3.5)]
    xs = [q[0] for q in ps if q]; ys = [q[1] for q in ps if q]
    x0, x1 = max(0, min(xs) - 30), min(im.shape[1], max(xs) + 30); y0, y1 = max(0, min(ys) - 30), min(im.shape[0], max(ys) + 30)
    c = im[y0:y1, x0:x1]
    down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
    if abs(down[1]) < abs(right[1]): c = cv2.rotate(c, cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif down[1] > 0: c = cv2.rotate(c, cv2.ROTATE_180)
    sc = min(2.0, 1400 / max(c.shape)); c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    out = S + '%s-%s-2.jpg' % (k, side); cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(out, c.shape, 'crop', x0, y0, x1, y1)
