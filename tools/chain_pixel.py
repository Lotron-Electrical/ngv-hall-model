# A pixel of a chain-posed 4K frame (tools/chain_pose.py JSON) met with a plane of the hall: u = const
# (an end face) or h = const. Prints the hit in hall coordinates.
#   python tools/chain_pixel.py <chain.json> <frame> u=48.056|d=-0.09|h=9.4 px,py [px,py ...]
import sys, json, cv2, numpy as np
import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
chain, fr, plane, *pix = sys.argv[1:]
rec = [r for r in json.load(open(chain)) if r['frame'] == fr][0]; R = np.array(rec['R']); C = np.array(rec['C'])
cam, _ = U.load_class('day4k')[json.load(open(chain))[0]['frame']]
fx, fy, cx, cy, k1, k2, p1, p2 = cam.params; K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2])
axis, val = plane.split('='); val = float(val)
NV = HU if axis == 'u' else HD if axis == 'd' else np.array([0, 1.0, 0]); off = O[1] if axis == 'h' else 0.0
print('%s: camera u %.2f d %.2f h %.2f' % (fr, (C - O) @ HU, (C - O) @ HD, C[1] - O[1]))
for pp in pix:
    px, py = map(float, pp.split(','))
    n = cv2.undistortPoints(np.array([[[px, py]]], np.float32), K, dist).reshape(2)
    D = R.T @ np.array([n[0], n[1], 1.0])
    num = val + off - ((C - O) @ NV if axis != 'h' else C[1]); den = D @ NV
    if abs(den) < 1e-6: print(pp, 'parallel'); continue
    t = num / den
    if t <= 0: print(pp, 'plane behind the camera'); continue
    X = C + t * D; q = X - O
    print('%s -> u %.3f d %.3f h %.3f (range %.2f m)' % (pp, q @ HU, q @ HD, q[1], t))
