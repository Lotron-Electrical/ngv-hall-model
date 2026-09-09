# Draws the sim's wall geometry over a register-posed frame: the north openings (WALLF), the south glazing fins, the
# end walls' levels (ENDW floors, ground top, head) and the doors, so a real frame can be read against the numbers
# without a render. Yellow = north openings, cyan = fins, green = end levels, magenta = doors.
#   python tools/overlay_walls.py <class> <frame> [out.jpg] [scale]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cname, fr = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/overlay-%s.jpg' % fr
scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
cam, ipath = U.load_class(cname)[fr]; im = cv2.imread(ipath)
def P(u, d, h):
    X = O + u * HU + d * HD + np.array([0, h, 0]); x, y, z = cam.project(np.asarray([X]))
    return (float(x[0]), float(y[0])) if z[0] > 0.3 else None
def poly(pts, col, w=3, closed=True):
    q = [P(*p) for p in pts]
    if any(v is None for v in q): return
    # A camera standing IN a wall opening sees geometry almost edge-on, and a point a few degrees off the
    # principal plane projects millions of pixels away. That overflows the int32 conversion below. Anything
    # that far outside the frame carries no information anyway, so the whole shape is dropped.
    if any(abs(a) > 20000 or abs(b) > 20000 for a, b in q): return
    q = np.int32([[round(a), round(b)] for a, b in q]).reshape(-1, 1, 2); cv2.polylines(im, [q], closed, col, w, cv2.LINE_AA)
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
OY = [8.99, 11.35]; DN = -0.09; DS = 15.364
for u0, u1 in OPEN: poly([(u0, DN, OY[0]), (u1, DN, OY[0]), (u1, DN, OY[1]), (u0, DN, OY[1])], (0, 255, 255))
for uf in [18.12, 22.02, 25.92, 29.83, 33.73]:   # the glazing fins' hall-side edges (glazing-fins.mjs)
    poly([(uf, 15.24, 0.13), (uf, 15.24, 13.6), (uf + 0.4, 15.24, 13.6), (uf + 0.4, 15.24, 0.13)], (255, 255, 0), 2)
for uE in [4.194, 48.056]:   # the end faces: ground top, the two floors, the head, the top
    for h in [5.3, 6.33, 8.34, 11.1, 13.5]: poly([(uE, 0, h), (uE, DS, h)], (0, 255, 0), 2, False)
for u0, u1, h, north in [(45.970, 47.786, 2.970, True), (23.10, 29.40, 2.3, True), (37.962, 39.662, 2.906, False), (45.698, 48.218, 2.522, False)]:
    d = DN if north else DS; poly([(u0, d, 0), (u1, d, 0), (u1, d, h), (u0, d, h)], (255, 0, 255))
for u in range(0, 52, 4): poly([(u, DN, 0), (u, DN, 0.3)], (0, 165, 255), 2, False); poly([(u, DS, 0), (u, DS, 0.3)], (0, 165, 255), 2, False)   # u ticks every 4 m at the wall feet
q = cam.center - O; cv2.putText(im, '%s %s  camera u %.2f d %.2f h %.2f' % (cname, fr, q @ HU, q @ HD, q[1]), (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 3)
im = cv2.resize(im, None, fx=scale, fy=scale); cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 86]); print(out, im.shape)
