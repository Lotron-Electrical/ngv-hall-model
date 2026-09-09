# 2026-09-09: THE CORRIDOR CEILING, FROM THE ONE CAPTURE THAT STOOD IN AN OPENING AND LOOKED UP.
#
# b4 finished registering this afternoon: 47 poses, every one of them standing in north opening 11 at
# h 9.42 to 10.14, and THIRTY-THREE OF THEM PITCHED UP by 10 to 18 degrees. That is the vantage this
# project has never had. Everything said about the room behind this wall so far was said through a 1.2 m
# slot from 15 m away, where the walk frames see under 20 grey levels of signal; b4 is standing in the
# slot with the ceiling a metre and a half over its head.
#
# WHY MATCHING WILL WORK HERE WHEN IT FAILED THIS MORNING. tools/corridor_cloud.py tried to match features
# through the openings between captures shot minutes and metres apart, and across all twelve openings it
# found three frame pairs with four or more matches. These frames are consecutive in one clip: same
# exposure, same lens, same lighting, sub-second apart, and the surface is close enough to fill the frame.
# The baseline is small, 1.18 m across the whole clip, but the ceiling is only about 1.4 m above the
# camera, so the ratio is near one and that is what conditioning actually depends on.
#
# NOTHING DRAWN ENTERS. Features are found on the whole picture, triangulated, and only then filtered to
# what landed behind the wall face, which is a plane measured from the outside long ago. The corridor's
# drawn ceiling 11.4 is never used, so the cloud is free to put it anywhere or nowhere.
#   python tools/corridor_ceiling.py [draw]
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
DRAWN_CEIL, DRAWN_FLOOR = 11.4, 8.34
MINBASE = 0.15
MAXMISS = 0.04
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
print('b4:', len(frames), 'poses')
feats = {}
for f, (cam, ip) in sorted(frames.items()):
    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    kp, de = sift.detectAndCompute(img, None)
    if de is None or len(kp) < 30:
        continue
    feats[f] = (cam, kp, de)
print(len(feats), 'of them carry features')

names = sorted(feats)
bf = cv2.BFMatcher(cv2.NORM_L2)
pts = []
pairs = 0
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        ca, ka, da = feats[names[i]]
        cb, kb, db = feats[names[j]]
        base = float(np.linalg.norm(ca.center - cb.center))
        if base < MINBASE:
            continue
        mm = bf.knnMatch(da, db, k=2)
        good = [m for m, n in mm if m.distance < 0.7 * n.distance]
        if len(good) < 12:
            continue
        pairs += 1
        pa = np.array([ka[m.queryIdx].pt for m in good])
        pb = np.array([kb[m.trainIdx].pt for m in good])
        va, vb = unit_rays(ca, pa), unit_rays(cb, pb)
        P, miss, s, t = meet(ca.center, va, cb.center, vb)
        keep = np.logical_and(np.logical_and(miss < MAXMISS, s > 0.2), t > 0.2)
        for k in np.where(keep)[0]:
            q = P[k] - O
            pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1]), float(miss[k]),
                        base, names[i], names[j], int(pa[k][0]), int(pa[k][1])))

print(pairs, 'pairs matched,', len(pts), 'points triangulated')
ALL = np.array([[p[0], p[1], p[2]] for p in pts])
print('   the whole cloud spans u %.2f to %.2f, d %.3f to %.3f, h %.2f to %.2f'
      % (ALL[:, 0].min(), ALL[:, 0].max(), ALL[:, 1].min(), ALL[:, 1].max(),
         ALL[:, 2].min(), ALL[:, 2].max()))
qd = np.percentile(ALL[:, 1], [1, 5, 25, 50, 75])
print('   its depth quantiles: 1%% %.3f, 5%% %.3f, 25%% %.3f, median %.3f, 75%% %.3f'
      % tuple(qd))
print('   %d points sit north of the wall face %.3f, %d within the 0.9 m reveal behind it'
      % (int((ALL[:, 1] < DN).sum()), DN,
         int(np.logical_and(ALL[:, 1] < DN, ALL[:, 1] > DN - 0.9).sum())))
room = [p for p in pts if p[1] < DN - 0.10]
print(len(room), 'of them landed more than 0.10 m behind the wall face')
if len(room) < 20:
    # THE REFUSAL, and it is about where the camera pointed rather than about the method. 47 poses, 718
    # matched pairs, 68,955 points, and not one of them in the room. b4 stands in the opening and looks
    # UP AND OUT: the pitch is positive but the bearing is into the hall, so what it photographed is the
    # canopy over the hall floor, the same thing b1 and b5 photographed from openings 5 and 6. Three
    # captures have now stood in these openings and none of them turned round.
    print('   REFUSED: this capture never pointed into the room, so it cannot measure it.')
    raise SystemExit(0)

A = np.array([[p[0], p[1], p[2]] for p in room])
print('   they span u %.2f to %.2f, d %.3f to %.3f, h %.2f to %.2f'
      % (A[:, 0].min(), A[:, 0].max(), A[:, 1].min(), A[:, 1].max(), A[:, 2].min(), A[:, 2].max()))
hist, edges = np.histogram(A[:, 2], bins=np.arange(8.0, 13.0, 0.05))
top = np.argsort(hist)[::-1][:8]
print('   the heights they pile up on, tallest first:')
for k in sorted(top, key=lambda z: -hist[z]):
    print('      h %.2f to %.2f  %4d points' % (edges[k], edges[k + 1], hist[k]))

# the highest consistent horizontal band is the candidate ceiling: take the points above the median and
# look for a level that many of them share, refusing if they do not
hi = A[A[:, 2] > np.median(A[:, 2])]
best = None
for c in np.arange(9.5, 12.8, 0.01):
    n = int((np.abs(hi[:, 2] - c) < 0.05).sum())
    if best is None or n > best[1]:
        best = (float(c), n)
print('')
print('   the tightest 0.10 m band in the upper half sits on h %.3f with %d points'
      % (best[0], best[1]))
print('   the sim draws the corridor ceiling on %.3f, a difference of %.3f m'
      % (DRAWN_CEIL, best[0] - DRAWN_CEIL))
band = A[np.abs(A[:, 2] - best[0]) < 0.05]
print('   that band runs u %.2f to %.2f and d %.3f to %.3f, so it is %s'
      % (band[:, 0].min(), band[:, 0].max(), band[:, 1].min(), band[:, 1].max(),
         'a surface across the room' if band[:, 1].max() - band[:, 1].min() > 0.4 else 'too shallow in d to be a ceiling'))

if 'draw' in sys.argv:
    os.makedirs(OUT, exist_ok=True)
    by = {}
    for p in room:
        by.setdefault(p[5], []).append(p)
    stem = max(by, key=lambda k: len(by[k]))
    cam, ip = frames[stem]
    im = cv2.imread(ip)
    for p in by[stem]:
        col = (0, 255, 255) if abs(p[2] - best[0]) < 0.05 else (255, 120, 0)
        cv2.circle(im, (p[7], p[8]), 9, col, 2)
    cv2.putText(im, '%s  yellow = the h %.2f band' % (stem, best[0]), (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
    k = 1500.0 / im.shape[0]
    out = os.path.join(OUT, stem + '-ceiling.jpg')
    cv2.imwrite(out, cv2.resize(im, (int(im.shape[1] * k), 1500)), [cv2.IMWRITE_JPEG_QUALITY, 86])
    print('   drawn back into', out, 'with', len(by[stem]), 'of its own points')
