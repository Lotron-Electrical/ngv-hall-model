# 2026-09-09: HOW WELL EACH CLIP'S POSES AGREE WITH ITS OWN PICTURES, measured in metres.
#
# tools/opening_nearcloud.py matched 700 pairs of b1 frames and kept ZERO points. Not few: none. The same
# code kept 3,888 from b4 and 938 from b5, and 144,419 from b3 on the east deck. A clip whose features
# match but whose rays never meet is telling you about its POSES, and b1's poses carry a live claim: they
# are the frames that stand in north opening 5, and the deck height behind that wall was argued from them.
#
# So this is the audit that was never run. For each clip it matches frames to their neighbours, meets every
# matched pair of rays, and reports the distribution of how far apart the two rays pass. That distance is
# the pose error projected onto the scene: if the poses are right, corresponding rays cross; if a pose is
# out by 100 mm, they miss by about that much whatever the picture looks like. b3, which produced a usable
# cloud, and the accepted classes, which were refined against the site model, are the controls.
#
# It reports on the NEAR field only, under 6 m, because that is where a pose error shows as a miss rather
# than being absorbed by depth.
#   python tools/pose_selfcheck.py [max-pairs-per-clip]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
CLASSES = ('b1', 'b1p', 'b3', 'b3p', 'b4', 'b5', 'b5p', 'b7s', 'b7sp', 'b6g', 'b6gp')
MINBASE, MAXBASE = 0.15, 1.6
RNEAR, RFAR = 0.25, 6.0
sift = cv2.SIFT_create(nfeatures=2000)


def unit_rays(cam, pts):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pts, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
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
    return np.linalg.norm(P1 - P2, axis=1), s, t


maxpairs = int(sys.argv[1]) if len(sys.argv) > 1 else 120
print('HOW FAR APART MATCHED RAYS PASS, per clip, in the near field under %.0f m' % RFAR)
print('%-6s %5s %6s %8s %8s %8s %8s %8s' % ('clip', 'frms', 'pairs', 'matches', 'p10', 'median', 'p90',
                                            'under 15mm'))
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        print('%-6s could not be loaded' % cls)
        continue
    items = sorted(frames.items())
    if len(items) < 4:
        print('%-6s %5d  too few frames' % (cls, len(items)))
        continue
    CEN = np.array([it[1][0].center for it in items])
    cand = []
    for i in range(len(items)):
        for j in range(i + 1, min(i + 12, len(items))):
            base = float(np.linalg.norm(CEN[i] - CEN[j]))
            if MINBASE <= base <= MAXBASE:
                cand.append((i, j))
    cand = cand[:maxpairs]
    if not cand:
        print('%-6s %5d  no pair inside the baseline window' % (cls, len(items)))
        continue
    need = sorted(set([i for i, _j in cand] + [j for _i, j in cand]))
    feats = {}
    for i in need:
        stem, (cam, ip) = items[i]
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        kp, de = sift.detectAndCompute(img, None)
        if de is not None and len(kp) >= 30:
            feats[i] = (cam, np.array([k.pt for k in kp]), de)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    misses = []
    npairs = 0
    for i, j in cand:
        if i not in feats or j not in feats:
            continue
        ca, pa_all, da = feats[i]
        cb, pb_all, db = feats[j]
        mm = bf.knnMatch(da, db, k=2)
        good = [m for m, nn in mm if m.distance < 0.72 * nn.distance]
        if len(good) < 12:
            continue
        pa = pa_all[[m.queryIdx for m in good]]
        pb = pb_all[[m.trainIdx for m in good]]
        va, vb = unit_rays(ca, pa), unit_rays(cb, pb)
        miss, s, t = meet(ca.center, va, cb.center, vb)
        sel = np.logical_and.reduce((s > RNEAR, s < RFAR, t > RNEAR, t < RFAR))
        if sel.any():
            misses.append(miss[sel])
        npairs += 1
    if not misses:
        print('%-6s %5d %6d %8d %8s %8s %8s %8s'
              % (cls, len(items), npairs, 0, '-', '-', '-', 'no near match at all'))
        continue
    m = np.concatenate(misses)
    print('%-6s %5d %6d %8d %8.3f %8.3f %8.3f %7.1f%%'
          % (cls, len(items), npairs, len(m), float(np.percentile(m, 10)), float(np.median(m)),
             float(np.percentile(m, 90)), 100.0 * float((m < 0.015).mean())))
print('')
print('A clip whose median miss is a few centimetres has poses good enough to measure a surface a metre')
print('away. One whose median is a fifth of a metre does not, whatever its frames show.')
