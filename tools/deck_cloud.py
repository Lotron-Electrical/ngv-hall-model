# 2026-09-09: THE EAST GALLERY MEASURED FROM ON TOP OF IT, by matching the deck clips against themselves.
#
# The last thing written about this gallery was that what would settle it is a capture standing on the
# deck rather than another instrument. That capture exists and has not been used this way. b3, b7s and b6g
# all stand ON the east deck: b3 at the north end near d 4.0, b7s and b6g at the south end near d 13.5,
# spanning ten metres of the gallery's own length and a metre of its depth.
#
# Every previous attempt on this gallery looked at it from the hall, 20 to 50 m away, where it is a dark
# recess: the cloud instrument got 114,449 points at that end and only 1,307 of them inside the gallery.
# From the deck the surfaces are one to four metres away and fill the frame, which is the condition that
# gave the south wall 31,234 points on one sheet and b4 68,955 points in a clip 47 frames long.
#
# WHAT IT CAN REACH. The deck under the camera, the back wall behind it, the parapet in front, and the
# soffit overhead if anything up there carries texture. Points are triangulated first and sorted into
# surfaces afterwards, so nothing is searched for near a drawn value; the drawn numbers are printed
# beside the peaks the cloud actually has.
#   python tools/deck_cloud.py [maxframes-per-clip]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UB, UF = 51.906, 48.056
DECK, LOWER, PARAPET_TOP, SOFFIT = 8.34, 6.33, 9.11, 11.1
CLASSES = ('b3p', 'b7sp', 'b6gp', 'b3', 'b7s', 'b6g')
MINBASE, MAXBASE, MAXMISS = 0.05, 4.0, 0.02
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
sift = cv2.SIFT_create(nfeatures=3000)


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
    return 0.5 * (P1 + P2), np.linalg.norm(P1 - P2, axis=1), s, t


maxf = int(sys.argv[1]) if len(sys.argv) > 1 else 140
onDeck = {}
seen = set()
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for f, (cam, ip) in frames.items():
        if f in seen:
            continue
        q = cam.center - O
        cu, ch = float(q @ HU), float(cam.center[1] - O[1])
        if not (UF - 0.4 < cu < UB + 0.2 and ch > DECK + 0.4):
            continue
        seen.add(f)
        onDeck.setdefault(cls.rstrip('p') + '|' + f.split('_')[0], []).append((f, cam, ip))
print('frames standing on the east deck, by clip:', {k: len(v) for k, v in sorted(onDeck.items())})

pts = []
for clip, items in sorted(onDeck.items()):
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
        for j in range(i + 1, min(i + 9, len(feats))):
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
            keep = np.logical_and(np.logical_and(miss < MAXMISS, s > 0.2), t > 0.2)
            for k in np.where(keep)[0]:
                q = P[k] - O
                pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1])))
            made += 1
    print('  %-12s %3d frames, %4d pairs, %7d new points' % (clip, len(feats), made, len(pts) - before))

if not pts:
    raise SystemExit('no deck clip produced a matched pair')
A = np.array(pts)
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-deck-east.npy'), A)
print(len(A), 'points triangulated')

G = A[np.logical_and.reduce((A[:, 0] > UF - 1.0, A[:, 0] < UB + 0.6,
                             A[:, 1] > 0.3, A[:, 1] < 15.1,
                             A[:, 2] > 5.5, A[:, 2] < 13.4))]
print(len(G), 'of them inside the gallery box')
if len(G) < 500:
    raise SystemExit('too few inside the gallery to read a surface')


def peaks(vals, lo, hi, step, label, drawn, n=5):
    edges = np.arange(lo, hi + 1e-9, step)
    h, _ = np.histogram(vals, bins=edges)
    hs = np.convolve(h, np.ones(5), 'same')
    picked = []
    for k in np.argsort(hs)[::-1]:
        c = float(0.5 * (edges[k] + edges[k + 1]))
        if any(abs(c - p[0]) < 0.20 for p in picked):
            continue
        picked.append((c, int(h[max(0, k - 2):k + 3].sum())))
        if len(picked) >= n:
            break
    print('')
    print('   %s: the densest levels the cloud actually has' % label)
    for c, cnt in picked:
        near = min(drawn, key=lambda dv: abs(dv - c))
        print('      %8.3f  %6d points   nearest drawn %8.3f   %+.3f' % (c, cnt, near, c - near))


peaks(G[:, 0], UF - 1.0, UB + 0.6, 0.02, 'ACROSS the gallery (u)', [UF, UB, UF + 2.1])
peaks(G[:, 2], 5.5, 13.4, 0.02, 'UP (h)', [LOWER, DECK, PARAPET_TOP, SOFFIT, 13.0])
