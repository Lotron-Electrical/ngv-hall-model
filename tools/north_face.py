# 2026-09-09: THE NORTH WALL AND ITS TWELVE OPENINGS MEASURED AS A HOLE PATTERN IN A POINT CLOUD.
#
# Every number in the opening table came from an edge finder that started on the drawn line, and fitting
# the follow gain out of it left the jambs surviving but the head unresolved. The cloud instrument does
# not have that failure mode: it never looks for an edge. Bluestone ashlar carries features, a 0.9 m deep
# unlit reveal carries none, so on the wall plane each opening is a HOLE IN THE POINT DENSITY and its
# edges are the jambs, the sill and the head. Nothing is searched for near a drawn value.
#
# WHAT MADE THIS POSSIBLE TODAY. Matching a clip against ITSELF works where matching between captures
# does not, because consecutive frames share exposure, lens and lighting; that is what gave 134,402 points
# down the hall this afternoon and 68,955 from b4. The one thing the walk clips could not do is look at
# this wall: they gave 35,321 points on the south face and 547 on the north, because the operator walked
# facing south. So frames are now PRESELECTED BY WHERE THEY POINT, and only the ones aimed at the north
# wall are matched, which also cuts the work by most of an order of magnitude.
#
# The drawn opening table is printed beside the answer and is never used to find it. dNorth is used only
# to choose a 0.6 m slab of space to keep points from, so a wall a quarter of a metre out is still caught.
#   python tools/north_face.py [maxframes-per-clip]
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
SLAB = 0.6
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.770, 19.983],
            [22.418, 23.631], [26.066, 27.279], [29.816, 31.028], [33.495, 34.706], [37.177, 38.383],
            [40.906, 42.118], [44.526, 45.739]]
SILL, HEAD = 8.99, 11.35
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b7s', 'b6g')
MINBASE, MAXBASE, MAXMISS = 0.25, 5.0, 0.03
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


maxf = int(sys.argv[1]) if len(sys.argv) > 1 else 90
# THE FIRST RUN TOOK EVERY FRAME AIMED ANYWHERE NORTH and the answer was worthless: quartile spreads of
# 0.2 to 0.3 m against the 0.03 m the same instrument gets on the south wall. The difference is not the
# method, it is the wall. The house rig hangs off this face and points away from it, so a camera walking
# past sees it dark and at a grazing angle, and a feature smeared along the surface triangulates badly in
# depth. So the selection can be tightened to cameras that stand close and look squarely at it.
NEAR = float(os.environ.get('NEAR', 14.0))
SQUARE = float(os.environ.get('SQUARE', -0.30))
looking = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for f, (cam, ip) in frames.items():
        q = cam.center - O
        cd = float(q @ HD)
        if cd < 0.8 or cd > NEAR:
            continue                              # out in the hall, but not so far that the wall is a smear
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
        if n < 1e-6 or float(fwd @ HD) / n > SQUARE:
            continue                              # and aimed squarely at it, not grazing along it
        looking.setdefault(cls + '|' + f.split('_')[0], []).append((f, cam, ip))
print('frames aimed at the north wall, by clip:',
      {k: len(v) for k, v in sorted(looking.items())})

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
            P, miss, s, t = meet(ca.center, va, cb.center, vb)
            keep = np.logical_and(np.logical_and(miss < MAXMISS, s > 0.3), t > 0.3)
            for k in np.where(keep)[0]:
                q = P[k] - O
                pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1])))
            made += 1
    print('  %-16s %3d frames, %3d pairs, %6d new points' % (clip, len(feats), made, len(pts) - before))

if not pts:
    raise SystemExit('no frame in this archive is aimed at the north wall')
A = np.array(pts)
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-north.npy'), A)
print(len(A), 'points in all')

W = A[np.logical_and.reduce((np.abs(A[:, 1] - DN) < SLAB, A[:, 0] > 1.0, A[:, 0] < 51.0,
                             A[:, 2] > 1.0, A[:, 2] < 12.0))]
print(len(W), 'of them in the slab around the north wall')
if len(W) < 500:
    raise SystemExit('too few on this wall to read anything off it')
hist, edges = np.histogram(W[:, 1], bins=np.arange(DN - SLAB, DN + SLAB, 0.01))
k = int(np.argmax(np.convolve(hist, np.ones(9), 'same')))
peak = float(0.5 * (edges[k] + edges[k + 1]))
S = W[np.abs(W[:, 1] - peak) < 0.10]
print('   the densest sheet sits on d %.4f and holds %d points; the sim draws %.3f, a difference of %+.4f'
      % (peak, len(S), DN, peak - DN))

# the openings as holes in the density, read on the band of heights the cloud actually covers
band = S[np.logical_and(S[:, 2] > SILL + 0.3, S[:, 2] < HEAD - 0.3)]
print('   between the drawn sill and head, %d points remain on the face' % len(band))
if len(band) < 300:
    print('   REFUSED: the cloud does not reach the opening band, so it cannot place a jamb.')
    raise SystemExit(0)
step = 0.02
ed = np.arange(0.0, 52.0 + 1e-9, step)
n, _ = np.histogram(band[:, 0], bins=ed)
print('')
print('opening   drawn u0    u1      hole found      west jamb   east jamb')
for oi, (u0, u1) in enumerate(OPENINGS):
    lo = int((u0 - 1.2) / step)
    hi = int((u1 + 1.2) / step)
    seg = n[lo:hi]
    if seg.sum() < 30:
        print('%7d %10.3f %7.3f   no stone measured beside it' % (oi + 1, u0, u1))
        continue
    empty = seg == 0
    best, run, start = None, 0, 0
    for k2 in range(len(empty)):
        if empty[k2]:
            if run == 0:
                start = k2
            run += 1
            if best is None or run > best[1]:
                best = (start, run)
        else:
            run = 0
    if best is None or best[1] < 10:
        print('%7d %10.3f %7.3f   no clear hole' % (oi + 1, u0, u1))
        continue
    a, ln = best
    ha, hb = float(ed[lo + a]), float(ed[lo + a + ln])
    print('%7d %10.3f %7.3f   %6.3f to %6.3f  %+9.3f %+11.3f'
          % (oi + 1, u0, u1, ha, hb, u0 - ha, u1 - hb))
