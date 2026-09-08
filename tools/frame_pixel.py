# A pixel of a register-posed frame (walk, night, day4k) met with a plane of the hall: u=, d= or h= const. Prints the
# hit in hall coordinates. Also 'project u,d,h' prints where a hall point lands in the frame.
#   python tools/frame_pixel.py <class> <frame> u=48.056|d=0|h=10.65 px,py [px,py ...]
#   python tools/frame_pixel.py <class> <frame> project u,d,h [u,d,h ...]
import sys, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
cname, fr, plane, *pix = sys.argv[1:]
cam, ipath = U.load_class(cname)[fr]; C = cam.center; R = cam.R
q = C - O; print('%s %s: camera u %.2f d %.2f h %.2f  image %s' % (cname, fr, q @ HU, q @ HD, q[1], ipath))
if plane == 'project':
    for pp in pix:
        u, d, h = map(float, pp.split(',')); X = O + u * HU + d * HD + np.array([0, h, 0])
        x, y, z = cam.project(np.asarray([X])); print('%s -> px %.0f,%.0f  depth %.2f' % (pp, x[0], y[0], z[0]))
    sys.exit()
fx, fy, cx, cy, *rest = cam.params; k1, k2, p1, p2 = (list(rest) + [0, 0, 0, 0])[:4]
K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2], float)
axis, val = plane.split('='); val = float(val)
NV = HU if axis == 'u' else HD if axis == 'd' else np.array([0, 1.0, 0]); off = O[1] if axis == 'h' else 0.0
for pp in pix:
    px, py = map(float, pp.split(','))
    n = cv2.undistortPoints(np.array([[[px, py]]], np.float32), K, dist).reshape(2)
    D = R.T @ np.array([n[0], n[1], 1.0])
    num = val + off - ((C - O) @ NV if axis != 'h' else C[1]); den = D @ NV
    if abs(den) < 1e-6: print(pp, 'parallel'); continue
    t = num / den
    if t <= 0: print(pp, 'plane behind the camera'); continue
    X = C + t * D; qq = X - O
    print('%s -> u %.3f d %.3f h %.3f (range %.2f m)' % (pp, qq @ HU, qq @ HD, qq[1], t))
