# 2026-09-09: TRIANGULATE THE CORRIDOR'S LAMPS, which is the one way left to measure the room behind the
# north wall. The pose census settled that no camera has ever stood in there, and photometry from the floor
# is hopeless because an opening is 100-150 px wide with under 20 grey levels of signal in it. But a LAMP is
# not signal in that sense: it is a specular blob far brighter than anything around it, and it is a POINT.
# A point seen through the same opening from two camera positions triangulates in three dimensions, and the
# two dimensions that come out of it are exactly the two the model cannot justify: the depth of the room
# (C.width 2.0, from a 1968 plan) and the height of its ceiling (C.ceil 11.4, inferred from a single
# downlight in one frame with its depth ASSUMED mid-corridor).
# The method: for every frame that sees an opening, find bright blobs inside that opening's aperture; each
# blob is a ray from that camera centre. Rays from different cameras through the same lamp meet. Cluster
# them, take the least-squares closest point, and keep only points that land BEHIND the wall.
#   python tools/corridor_lamps.py <class> [max_frames] [threshold]
import sys, os, json, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
DN = -0.090
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
OY = (8.99, 11.35)
cls = sys.argv[1]
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 60
THR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.80   # a blob must beat this quantile of the aperture

frames = U.load_class(cls)
rays = []          # (opening, camera centre, unit direction, brightness)
used = 0
for fr, (cam, ip) in sorted(frames.items()):
    if used >= maxf: break
    img = None
    for oi, (u0, u1) in enumerate(OPEN):
        corners = np.array([O + uu * HU + DN * HD + np.array([0, hv, 0])
                            for uu, hv in ((u0, OY[0]), (u1, OY[0]), (u1, OY[1]), (u0, OY[1]))])
        x, y, z = cam.project(corners)
        if (z <= 0.5).any(): continue
        if x.min() < 4 or x.max() > cam.w - 4 or y.min() < 4 or y.max() > cam.h - 4: continue
        w = x.max() - x.min(); h = y.max() - y.min()
        if w < 12 or h < 12: continue                 # too small on the sensor to hold a blob
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None: break
            used += 1
        poly = np.round(np.stack([x, y], 1)).astype(np.int32)
        mask = np.zeros(img.shape, np.uint8); cv2.fillConvexPoly(mask, poly, 255)
        inside = mask > 0
        vals = img[inside]
        if vals.size < 60: continue
        hi = float(np.quantile(vals, THR))
        # a lamp has to be bright in ABSOLUTE terms too, or every dark opening finds its brightest noise
        cut = max(hi, float(np.median(vals)) + 25.0, 60.0)
        blob = np.logical_and(img >= cut, inside).astype(np.uint8)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(blob, 8)
        for k in range(1, n):
            area = stats[k, cv2.CC_STAT_AREA]
            if area < 3 or area > 0.25 * (w * h): continue
            px, py = cent[k]
            K = np.array([[cam.params[0], 0, cam.params[2]], [0, cam.params[1], cam.params[3]], [0, 0, 1.0]])
            v = np.linalg.inv(K) @ np.array([px, py, 1.0])
            d = cam.R.T @ (v / np.linalg.norm(v))
            d = d / np.linalg.norm(d)
            rays.append((oi, np.asarray(cam.center, float), d, float(img[int(py), int(px)])))
print('%s: %d frames read, %d bright blobs inside openings' % (cls, used, len(rays)))

def meet(group):
    """least-squares point closest to a bundle of rays"""
    A = np.zeros((3, 3)); b = np.zeros(3)
    for _, C, d, _ in group:
        P = np.eye(3) - np.outer(d, d)
        A += P; b += P @ C
    if np.linalg.matrix_rank(A) < 3: return None, None
    X = np.linalg.solve(A, b)
    res = float(np.mean([np.linalg.norm(np.cross(d, X - C)) for _, C, d, _ in group]))
    return X, res

out = []
for oi in sorted({r[0] for r in rays}):
    g = [r for r in rays if r[0] == oi]
    if len(g) < 3: continue
    Cs = np.array([r[1] for r in g])
    base = float(np.linalg.norm(Cs.max(0) - Cs.min(0)))
    if base < 1.5: continue          # rays from one spot cannot triangulate anything
    X, res = meet(g)
    if X is None: continue
    q = X - O
    out.append((oi + 1, len(g), base, float(q @ HU), float(q @ HD), float(q[1]), res))
print('')
print('%-8s %5s %8s %8s %8s %8s %8s' % ('opening', 'rays', 'baseline', 'u', 'd', 'h', 'miss'))
for oi, n, bl, u, d, h, res in out:
    print('%-8d %5d %8.2f %8.2f %8.2f %8.2f %8.3f' % (oi, n, bl, u, d, h, res))
behind = [r for r in out if r[4] < DN and r[6] < 0.6]
print('')
if behind:
    ds = [r[4] for r in behind]; hs = [r[5] for r in behind]
    print('%d openings put a light BEHIND the wall face:' % len(behind))
    print('  depth  d %.2f to %.2f   (the model draws the corridor d -0.99 to -2.99)' % (min(ds), max(ds)))
    print('  height h %.2f to %.2f   (the model draws the ceiling 11.4)' % (min(hs), max(hs)))
else:
    print('nothing triangulates behind the wall with a miss under 0.6 m: no lamp is resolved this way')
if os.environ.get('LAMP_JSON'):
    json.dump({'class': cls, 'frames': used,
               'lamps': [{'opening': o, 'rays': n, 'baseline': bl, 'u': u, 'd': d, 'h': h, 'miss': r}
                         for o, n, bl, u, d, h, r in out]},
              open(os.environ['LAMP_JSON'], 'w'), indent=1)
    print('wrote', os.environ['LAMP_JSON'])
