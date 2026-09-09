# 2026-09-09: THE ROOM BEHIND THE WALL, SAMPLED AS A POINT CLOUD THROUGH ITS OWN OPENINGS.
#
# The lamp triangulation worked because it stopped asking a picture to resolve a SURFACE through a 1.2 m
# slot and asked it to resolve a POINT instead. Three lamps came out and they fixed the room's depth. The
# same principle generalises: any feature the room shows through an opening is a point, and two cameras
# that both see it fix it. What killed the earlier attempt at this (tools/pan_points.py, 3,611 points that
# all landed on the hall floor) was that nothing forced the points to be in the room. Here the aperture
# does exactly that, twice over: features are only detected inside the drawn opening rectangle in BOTH
# pictures, and a triangulated point is only kept if it lands behind the wall face.
#
# The drawn rectangle chooses where to look and the wall face is a plane this project measured long ago
# from the outside; neither the corridor width, its floor nor its ceiling enters anywhere, so all three
# are free to be refuted. A pair contributes nothing unless its two cameras stand at least 1.5 m apart,
# which is the conditioning test the balcony soffit failed.
#   python tools/corridor_cloud.py [opening]
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
SILL, HEAD = 8.99, 11.35
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b5', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp')
MINPX = int(__import__('os').environ.get('MINPX', 60))          # an aperture narrower than this holds no repeatable feature
MINBASE = float(__import__('os').environ.get('MINBASE', 1.5))       # metres between the two cameras, the conditioning the soffit could not meet
MAXMISS = float(__import__('os').environ.get('MAXMISS', 0.05))      # metres: how close the two rays must come to count as the same point
sift = cv2.SIFT_create(nfeatures=1200)


def aperture(cam, u0, u1):
    corners = np.array([O + uu * HU + DN * HD + np.array([0, vv, 0])
                        for uu, vv in ((u0, SILL), (u1, SILL), (u1, HEAD), (u0, HEAD))])
    x, y, z = cam.project(corners)
    if np.any(z <= 0.3):
        return None
    q = np.stack([x, y], 1)
    # THE WHOLE RECTANGLE USED TO HAVE TO BE ON THE SENSOR, which threw away most of the archive: a
    # camera close enough to resolve anything inside an opening usually has that opening running off the
    # edge of the picture. A generous margin is enough, and the mask does the rest.
    if q[:, 0].max() < 30 or q[:, 1].max() < 30 or q[:, 0].min() > cam.w - 30 or q[:, 1].min() > cam.h - 30:
        return None
    if q[:, 0].max() - q[:, 0].min() < MINPX or q[:, 1].max() - q[:, 1].min() < MINPX:
        return None
    return q


def features(cam, ip, q):
    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    mask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, np.round(q).astype(np.int32), 255)
    mask = cv2.erode(mask, np.ones((7, 7), np.uint8))
    if int(mask.sum()) // 255 < 400:
        return None
    # the aperture is a dark slot in a bright wall, so its own contrast is a few grey levels: stretch it
    vals = img[mask > 0]
    lo, hi = float(np.percentile(vals, 2)), float(np.percentile(vals, 98))
    if hi - lo < 4:
        return None
    st = np.clip((img.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)
    kp, de = sift.detectAndCompute(st, mask)
    if de is None or len(kp) < 8:
        return None
    return kp, de


def rays(cam, pts):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pts, np.float64).reshape(-1, 1, 2), K, dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def meet(C1, v1, C2, v2):
    """closest approach of two matched ray bundles: midpoints, miss distances and both depths"""
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


which = int(sys.argv[1]) if len(sys.argv) > 1 else None
todo = [which - 1] if which else range(len(OPENINGS))
seen, cams = set(), {}
for cls in CLASSES:
    try:
        fr = U.load_class(cls)
    except Exception:
        continue
    for f, v in fr.items():
        if f not in seen:
            seen.add(f)
            cams[f] = (cls, v[0], v[1])
print(len(cams), 'distinct posed frames offered to the search')

allpts = []
for oi in todo:
    u0, u1 = OPENINGS[oi]
    cand = []
    for f, (cls, cam, ip) in cams.items():
        qc = cam.center - O
        if float(qc @ HD) < 0.5 or abs(float(qc @ HU) - 0.5 * (u0 + u1)) > 20.0:
            continue
        q = aperture(cam, u0, u1)
        if q is None:
            continue
        cand.append((f, cam, ip, q))
    if len(cand) < 2:
        continue
    cand.sort(key=lambda t: -(t[3][:, 0].max() - t[3][:, 0].min()))
    cand = cand[:26]
    feats = {}
    for f, cam, ip, q in cand:
        got = features(cam, ip, q)
        if got is not None:
            feats[f] = (cam, got[0], got[1])
    names = sorted(feats)
    pts = []
    bf = cv2.BFMatcher(cv2.NORM_L2)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ca, ka, da = feats[names[i]]
            cb, kb, db = feats[names[j]]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < MINBASE:
                continue
            mm = bf.knnMatch(da, db, k=2)
            good = [m for m, n in mm if m.distance < 0.75 * n.distance]
            if len(good) < 4:
                continue
            if os.environ.get('LOUD'):
                print('   %-12s %-12s base %.2f  %3d matches' % (names[i], names[j], base, len(good)))
            pa = np.array([ka[m.queryIdx].pt for m in good])
            pb = np.array([kb[m.trainIdx].pt for m in good])
            va, vb = rays(ca, pa), rays(cb, pb)
            P, miss, s, t = meet(ca.center, va, cb.center, vb)
            keep = np.logical_and(np.logical_and(miss < MAXMISS, s > 0.5), t > 0.5)
            if os.environ.get('LOUD'):
                print('        miss median %.3f min %.3f, %d in front of both, %d kept'
                      % (float(np.median(miss)), float(miss.min()),
                         int(np.logical_and(s > 0.5, t > 0.5).sum()), int(keep.sum())))
            for k in np.where(keep)[0]:
                qq = P[k] - O
                pts.append((float(qq @ HU), float(qq @ HD), float(P[k][1] - O[1]), float(miss[k]), base))
    inroom = [p for p in pts if p[1] < DN - 0.06]
    print('opening %2d: %2d frames with features, %5d triangulated, %4d of them behind the wall face'
          % (oi + 1, len(feats), len(pts), len(inroom)))
    if len(inroom) >= 20:
        a = np.array(inroom)
        print('        d %.3f to %.3f (median %.3f), h %.3f to %.3f (median %.3f)'
              % (a[:, 1].min(), a[:, 1].max(), np.median(a[:, 1]),
                 a[:, 2].min(), a[:, 2].max(), np.median(a[:, 2])))
        print('        the deepest tenth sit past d %.3f, so the room is at least %.3f m deep'
              % (np.percentile(a[:, 1], 10), DN - np.percentile(a[:, 1], 10)))
    allpts.extend((oi + 1,) + tuple(p) for p in inroom)

if allpts:
    A = np.array([[p[2], p[3]] for p in allpts])
    print('')
    print('ACROSS EVERY OPENING:', len(allpts), 'points behind the wall face')
    hist, edges = np.histogram(A[:, 1], bins=np.arange(7.5, 13.0, 0.1))
    top = np.argsort(hist)[::-1][:6]
    print('   the heights they pile up on, tallest first:')
    for k in sorted(top, key=lambda z: -hist[z]):
        print('      h %.2f to %.2f  %4d points' % (edges[k], edges[k + 1], hist[k]))
    outd = 'E:/sitecapture-captures/ngv-site/agent-ref-walls'
    os.makedirs(outd, exist_ok=True)
    np.save(os.path.join(outd, 'corridor-cloud.npy'),
            np.array([[p[0], p[1], p[2], p[3], p[4]] for p in allpts]))
    print('   written to', os.path.join(outd, 'corridor-cloud.npy'))
