# Project the built end-gallery geometry (ENDW) into the posed 4K balcony frames and draw it over
# the real west end, so the face station, the floors, the fascias and the rails can be read against
# the photograph.   python tools/endwall_overlay.py <frame> [uF ...]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
frame = sys.argv[1] if len(sys.argv) > 1 else 'd4_000049'
faces = [float(a) for a in sys.argv[2:]] or [4.05]
FLOORS = [3.99, 6.33, 8.34]; SLAB = 0.45; RAIL = 1.1; UB = 0.344; D = 15.364
cams = U.load_class('day4k'); cam, fpath = cams[frame]
im = cv2.imread(fpath)
def pt(u, d, h):
    x, y, z = cam.project(np.asarray([world(u, d, h)]))
    return (int(round(x[0])), int(round(y[0]))) if z[0] > 0 else None
def line(a, b, col, w=1):
    if a and b: cv2.line(im, a, b, col, w, cv2.LINE_AA)
cols = [(0, 255, 255), (255, 0, 255), (0, 200, 0), (255, 128, 0)]
for k, uF in enumerate(faces):
    col = cols[k % 4]
    for h in FLOORS:
        line(pt(uF, 0, h), pt(uF, D, h), col, 2)                       # floor edge
        line(pt(uF, 0, h - SLAB), pt(uF, D, h - SLAB), col, 1)         # fascia bottom
        line(pt(uF, 0, h + RAIL), pt(uF, D, h + RAIL), col, 1)         # rail top
    line(pt(uF, 0, 0), pt(uF, 0, 12), col, 1); line(pt(uF, D, 0), pt(uF, D, 12), col, 1)
    cv2.putText(im, 'uF %.2f' % uF, (40, 80 + 50 * k), cv2.FONT_HERSHEY_SIMPLEX, 1.6, col, 3)
# the plate-end wall edge (h 10.0 on u 0.344) and the top-floor back wall
line(pt(UB, 0, 10.0), pt(UB, D, 10.0), (255, 255, 255), 1)
line(pt(UB, 0, 8.34), pt(UB, D, 8.34), (200, 200, 200), 1)
# crop to the far end: the projection of the wall's corners
ps = [pt(UB, 0, 0), pt(UB, D, 0), pt(UB, 0, 12.5), pt(UB, D, 12.5)]
xs = [p[0] for p in ps if p]; ys = [p[1] for p in ps if p]
x0, x1 = max(0, min(xs) - 150), min(im.shape[1], max(xs) + 150); y0, y1 = max(0, min(ys) - 150), min(im.shape[0], max(ys) + 150)
c = im[y0:y1, x0:x1]; c = cv2.resize(c, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
out = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/endwall-overlay-%s.jpg' % frame
q = cam.center - O
cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(out, c.shape, 'cam u %.2f d %.2f h %.2f' % (q @ HU, q @ HD, q[1]))
