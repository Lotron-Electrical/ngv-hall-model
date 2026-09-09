# 2026-09-09: OPENING 11 MEASURED FROM 0.9 m AWAY, which nothing in this project had ever done.
#
# b4 registered this afternoon and turned out to be 47 poses standing IN north opening 11, h 9.42 to
# 10.14, d -0.19 to 0.78. It cannot see the room behind the wall, and that is now settled three times
# over: 718 matched pairs give 68,955 triangulated points and the deepest sits on d -0.029, so the whole
# clip looked up and OUT at the hall (tools/corridor_ceiling.py). But those 68,955 points are standing on
# the wall itself at arm's length, and every previous reading of this opening came from 15 m away through
# an instrument that started at the drawn line.
#
# HOW A HOLE IS MEASURED BY WHAT IS NOT IN IT. Bluestone ashlar is textured and carries features; the
# opening is a dark void 0.9 m deep and carries none. So on the wall plane the aperture appears as a GAP
# in the point density, and its edges are the jambs, the sill and the head. Nothing is searched for near
# a drawn value: the occupancy is built over the whole span from u 39.9 to 43.1 and h 8.2 to 12.2, the
# drawn numbers are printed beside the answer and never used to find it.
#
# THE ONE THING THIS CANNOT DO is prove a level it cannot see. The clip stands inside the opening, so the
# head is nearly overhead and the sill nearly underfoot; each is reported with the count of points that
# actually define it and refused when that count is thin, rather than being extrapolated.
#   python tools/opening_nearfield.py [draw]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.090
OPEN11 = (40.906, 42.118)
DRAWN_SILL, DRAWN_HEAD = 8.99, 11.35
FACE_TOL = 0.14                  # metres either side of the wall plane counted as on the face
MINBASE, MAXMISS = 0.15, 0.03
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/corridor'
sift = cv2.SIFT_create(nfeatures=4000)


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


frames = U.load_class('b4')
feats = {}
for f, (cam, ip) in sorted(frames.items()):
    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    kp, de = sift.detectAndCompute(img, None)
    if de is not None and len(kp) >= 30:
        feats[f] = (cam, kp, de)
print('b4:', len(frames), 'poses,', len(feats), 'with features')

names = sorted(feats)
bf = cv2.BFMatcher(cv2.NORM_L2)
pts = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        ca, ka, da = feats[names[i]]
        cb, kb, db = feats[names[j]]
        if float(np.linalg.norm(ca.center - cb.center)) < MINBASE:
            continue
        mm = bf.knnMatch(da, db, k=2)
        good = [m for m, n in mm if m.distance < 0.7 * n.distance]
        if len(good) < 12:
            continue
        pa = np.array([ka[m.queryIdx].pt for m in good])
        pb = np.array([kb[m.trainIdx].pt for m in good])
        va, vb = unit_rays(ca, pa), unit_rays(cb, pb)
        P, miss, s, t = meet(ca.center, va, cb.center, vb)
        keep = np.logical_and(np.logical_and(miss < MAXMISS, s > 0.2), t > 0.2)
        for k in np.where(keep)[0]:
            q = P[k] - O
            pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1]),
                        names[i], int(pa[k][0]), int(pa[k][1])))

A = np.array([[p[0], p[1], p[2]] for p in pts])
print(len(pts), 'points triangulated')
near = np.logical_and(np.logical_and(A[:, 0] > 39.9, A[:, 0] < 43.1),
                      np.logical_and(A[:, 2] > 8.2, A[:, 2] < 12.2))
face = np.logical_and(near, np.abs(A[:, 1] - DN) < FACE_TOL)
W = A[face]
print(int(near.sum()), 'of them are in front of this bay,', len(W), 'of those lie on the wall plane')
if len(W) < 200:
    raise SystemExit('too few on the face to read a hole in it')

print('   the wall plane they define sits on d %.3f (median), quartiles %.3f and %.3f. The sim draws %.3f.'
      % (float(np.median(W[:, 1])), float(np.percentile(W[:, 1], 25)),
         float(np.percentile(W[:, 1], 75)), DN))


def gap(vals, lo, hi, step, minrun):
    """the widest stretch between lo and hi that carries no points, and its edges"""
    edges = np.arange(lo, hi + 1e-9, step)
    n, _ = np.histogram(vals, bins=edges)
    empty = n == 0
    best, run, start = None, 0, 0
    for k in range(len(empty)):
        if empty[k]:
            if run == 0:
                start = k
            run += 1
            if best is None or run > best[1]:
                best = (start, run)
        else:
            run = 0
    if best is None or best[1] < minrun:
        return None
    a, ln = best
    return float(edges[a]), float(edges[a + ln]), int(ln)


band = W[np.logical_and(W[:, 2] > 9.4, W[:, 2] < 10.9)]      # the height range this clip actually covers
g = gap(band[:, 0], 39.9, 43.1, 0.02, 8)
print('')
if g is None:
    print('   NO CLEAR GAP IN u, so this cloud cannot place the jambs')
else:
    print('   the wall carries no points between u %.3f and %.3f, a %.3f m hole'
          % (g[0], g[1], g[1] - g[0]))
    print('   the sim draws opening 11 from u %.3f to %.3f, so its jambs stand %+.3f and %+.3f from the hole'
          % (OPEN11[0], OPEN11[1], OPEN11[0] - g[0], OPEN11[1] - g[1]))
    print('   %d points define the west side of it and %d the east'
          % (int(np.logical_and(band[:, 0] > g[0] - 0.30, band[:, 0] < g[0]).sum()),
             int(np.logical_and(band[:, 0] > g[1], band[:, 0] < g[1] + 0.30).sum())))

col = W[np.logical_and(W[:, 0] > OPEN11[0] + 0.1, W[:, 0] < OPEN11[1] - 0.1)]
print('')
print('   inside the hole in u, %d points remain on the face; they run h %.3f to %.3f'
      % (len(col), float(col[:, 2].min()) if len(col) else float('nan'),
         float(col[:, 2].max()) if len(col) else float('nan')))
gv = gap(col[:, 2], 8.2, 12.2, 0.02, 8) if len(col) > 20 else None
if gv is None:
    print('   the sill and head cannot be read this way from this clip: it stands inside the opening, so')
    print('   the head is nearly overhead and the sill nearly underfoot, and neither is covered.')
else:
    print('   no points between h %.3f and %.3f, against the drawn sill %.3f and head %.3f'
          % (gv[0], gv[1], DRAWN_SILL, DRAWN_HEAD))

if 'draw' in sys.argv and g is not None:
    os.makedirs(OUT, exist_ok=True)
    by = {}
    for p in pts:
        if 39.9 < p[0] < 43.1 and abs(p[1] - DN) < FACE_TOL and 8.2 < p[2] < 12.2:
            by.setdefault(p[3], []).append(p)
    if by:
        stem = max(by, key=lambda k: len(by[k]))
        im = cv2.imread(frames[stem][1])
        for p in by[stem]:
            c = (0, 255, 255) if (p[0] < g[0] or p[0] > g[1]) else (0, 120, 255)
            cv2.circle(im, (p[4], p[5]), 8, c, 2)
        cv2.putText(im, '%s  %d wall-plane points' % (stem, len(by[stem])), (40, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
        k = 1500.0 / im.shape[0]
        outp = os.path.join(OUT, stem + '-face.jpg')
        cv2.imwrite(outp, cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 86])
        print('   drawn back into', outp)
