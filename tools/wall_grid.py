# A whole posed frame with the north (or south) wall's u grid (1 m, labelled every 2) from carpet to h 12,
# plus the high openings' outlines, upright, downscaled to 1400.   python tools/wall_grid.py north class:frame ...
import sys, os, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
side = sys.argv[1]; dw = -0.09 if side == 'north' else 15.364
OPS = [[4.076, 5.332], [7.676, 8.932], [10.764, 12.020], [15.132, 16.388], [18.628, 19.876], [22.336, 23.592], [26.044, 27.300], [29.948, 31.196], [33.588, 34.836], [37.348, 38.596], [40.884, 42.140], [44.508, 45.756]]
S = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/ref/doors/'; os.makedirs(S, exist_ok=True)
for spec in sys.argv[2:]:
    cls, k = spec.split(':'); cam, p = U.load_class(cls)[k]; im = cv2.imread(p)
    def pt(u, d, h):
        x, y, z = cam.project(np.asarray([world(u, d, h)]))
        if z[0] <= 0 or abs(x[0]) > 4 * cam.w or abs(y[0]) > 4 * cam.h: return None
        return (int(round(x[0])), int(round(y[0])))
    def line(a, b, col, w=1):
        if a and b: cv2.line(im, a, b, col, w, cv2.LINE_AA)
    for uu in range(0, 53):
        line(pt(uu, dw, 0), pt(uu, dw, 12), (255, 0, 255), 2 if uu % 2 == 0 else 1)
        if uu % 2 == 0:
            q = pt(uu, dw, 6)
            if q: cv2.putText(im, str(uu), q, cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 255), 3)
    for hz in (0, 3, 6, 8.99, 11.35): line(pt(0, dw, hz), pt(52, dw, hz), (0, 200, 0), 2)
    if side == 'north':
        for i, (a, b) in enumerate(OPS):
            c4 = [pt(a, dw, 8.99), pt(b, dw, 8.99), pt(b, dw, 11.35), pt(a, dw, 11.35)]
            for j in range(4): line(c4[j], c4[(j + 1) % 4], (0, 255, 255), 2)
            if c4[3]: cv2.putText(im, 'op%d' % i, c4[3], cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    down = cam.R.T @ np.array([0, 1.0, 0]); right = cam.R.T @ np.array([1.0, 0, 0])
    if abs(down[1]) < abs(right[1]): im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE if right[1] < 0 else cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif down[1] > 0: im = cv2.rotate(im, cv2.ROTATE_180)
    sc = min(1.0, 1400 / max(im.shape)); im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    out = S + '%s-%s-grid.jpg' % (k, side); cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(out, im.shape)
