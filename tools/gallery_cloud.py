# 2026-09-09: THE END BALCONIES MEASURED AS A POINT CLOUD, on the geometry that instrument actually likes.
#
# Today has established exactly when this works. Matching a clip against ITSELF and triangulating gives a
# usable surface when the surface is lit and the cameras look at it squarely: the south wall came back with
# 31,234 points on one sheet and a 0.03 m interquartile depth spread, while the north wall, seen dark and
# grazing from 13 m, gave 0.43 m and a sheet that moved 0.12 m when the frame selection changed.
#
# The end galleries are the south wall's case, not the north wall's. They face down the length of the hall,
# they are lit by the glass roof above them, and a camera anywhere on the floor sees them square on rather
# than edge on. So this collects the frames aimed at each end, builds the cloud, and reads the gallery's
# own planes and levels straight out of it: the parapet face, the back wall, the two deck levels, the
# parapet top and, if anything is there, the soffit over the top deck.
#
# NOTHING DRAWN IS SEARCHED FOR. The drawn stations are printed beside each answer, and the only place a
# drawn number enters is the box of space the points are collected from, which is the whole gallery plus a
# metre of margin on every side. A plane a half metre out of place would still be inside it.
#   python tools/gallery_cloud.py [west|east] [maxframes-per-clip]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
ENDS = {'west': (0.344, -1.0), 'east': (51.906, 1.0)}
FACE, DSOUTH = 3.85, 15.364
FLOORS, SLAB, UPSTAND_E, HEAD = [6.33, 8.34], 0.26, 0.77, 11.1
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b7s', 'b6g')
MINBASE, MAXBASE, MAXMISS = 0.25, 6.0, 0.03
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
sift = cv2.SIFT_create(nfeatures=3000)


def unit_rays(cam, pts):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pts, np.float64).reshape(-1, 1, 2), K, dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def meet(C1, v1, C2, v2):
    w = C2 - C1
    a = np.einsum('ij,ij->i', v1, v1)
    b = np.einsum('ij,ij->i', v1, v2)
    c = np.einsum('ij,ij->i', v2, v2)
    d = v1 @ w
    e = v2 @ w
    den = a * c - b * b
    ok = np.abs(den) > 1e-9
    den = np.where(ok, den, 1.0)
    s = np.where(ok, (c * d - b * e) / den, 0.0)
    t = np.where(ok, (b * d - a * e) / den, 0.0)
    P1 = C1 + s[:, None] * v1
    P2 = C2 + t[:, None] * v2
    return 0.5 * (P1 + P2), np.linalg.norm(P1 - P2, axis=1), s, t


end = sys.argv[1] if len(sys.argv) > 1 else 'east'
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 110
uB, s = ENDS[end]
uF = uB - s * FACE

looking = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for f, (cam, ip) in frames.items():
        q = cam.center - O
        cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
        if cd < 0.8 or cd > 14.6 or ch > 6.0:
            continue                              # standing on the hall floor
        if s > 0 and (cu > uF - 4.0):
            continue
        if s < 0 and (cu < uF + 4.0):
            continue                              # far enough back to see the whole face
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
        if n < 1e-6 or float(fwd @ HU) / n * s < 0.55:
            continue                              # and pointed at this end
        looking.setdefault(cls + '|' + f.split('_')[0], []).append((f, cam, ip))
print(end, 'end: frames aimed at it, by clip:', {k: len(v) for k, v in sorted(looking.items())})

pts = []
for clip, items in sorted(looking.items()):
    items.sort()
    take = items[:: max(1, len(items) // maxf)][:maxf]
    feats = []
    for f, cam, ip in take:
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        kp, de = sift.detectAndCompute(img, None)
        if de is not None and len(kp) >= 40:
            feats.append((f, cam, kp, de))
    bf = cv2.BFMatcher(cv2.NORM_L2)
    made, before = 0, len(pts)
    for i in range(len(feats)):
        for j in range(i + 1, min(i + 7, len(feats))):
            _fa, ca, ka, da = feats[i]
            _fb, cb, kb, db = feats[j]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < MINBASE or base > MAXBASE:
                continue
            mm = bf.knnMatch(da, db, k=2)
            good = [m for m, n in mm if m.distance < 0.7 * n.distance]
            if len(good) < 15:
                continue
            pa = np.array([ka[m.queryIdx].pt for m in good])
            pb = np.array([kb[m.trainIdx].pt for m in good])
            va, vb = unit_rays(ca, pa), unit_rays(cb, pb)
            P, miss, s2, t2 = meet(ca.center, va, cb.center, vb)
            keep = np.logical_and(np.logical_and(miss < MAXMISS, s2 > 0.3), t2 > 0.3)
            for k in np.where(keep)[0]:
                q = P[k] - O
                pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1])))
            made += 1
    print('  %-16s %3d frames, %3d pairs, %6d new points' % (clip, len(feats), made, len(pts) - before))

if not pts:
    raise SystemExit('nothing in this archive is aimed at that end from the floor')
A = np.array(pts)
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-gallery-%s.npy' % end), A)
print(len(A), 'points in all')

lo_u, hi_u = (min(uB, uF) - 1.0, max(uB, uF) + 1.0)
G = A[np.logical_and.reduce((A[:, 0] > lo_u, A[:, 0] < hi_u, A[:, 1] > 0.4, A[:, 1] < DSOUTH - 0.4,
                             A[:, 2] > 4.5, A[:, 2] < 13.4))]
print(len(G), 'of them inside the gallery box u %.2f to %.2f, h 4.5 to 13.4' % (lo_u, hi_u))
if len(G) < 400:
    raise SystemExit('too few in the gallery to read a plane off it')


def peaks(vals, lo, hi, step, smooth, label, drawn, n=4):
    edges = np.arange(lo, hi + 1e-9, step)
    h, _ = np.histogram(vals, bins=edges)
    hs = np.convolve(h, np.ones(smooth), 'same')
    order = np.argsort(hs)[::-1]
    picked = []
    for k in order:
        c = float(0.5 * (edges[k] + edges[k + 1]))
        if any(abs(c - p[0]) < 0.25 for p in picked):
            continue
        picked.append((c, int(h[max(0, k - smooth // 2): k + smooth // 2 + 1].sum())))
        if len(picked) >= n:
            break
    print('')
    print('   %s: the %d densest levels, and what the sim draws' % (label, len(picked)))
    for c, cnt in picked:
        near = min(drawn, key=lambda dv: abs(dv - c))
        print('      %8.3f  %6d points   nearest drawn %8.3f   %+.3f' % (c, cnt, near, c - near))
    return picked


peaks(G[:, 0], lo_u, hi_u, 0.01, 9, 'ACROSS the hall (u)', [uF, uB, uF + s * 2.1])
peaks(G[:, 2], 4.5, 13.4, 0.01, 9, 'UP (h)', FLOORS + [FLOORS[1] + UPSTAND_E, HEAD, 13.0], n=5)
