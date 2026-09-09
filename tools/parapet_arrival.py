# 2026-09-09: THE EAST PARAPET SETTLED BY WHERE LLOYD WALKED AND WHAT HE COULD SEE PAST IT.
#
# The disagreement that has stood all day: 449 silhouette rays fit a face on u 48.702 with a top on h 9.391
# about 1.8 times better than the drawn (48.056, 9.110), and no instrument aimed at the edge could separate
# the two, because every camera sat within 0.68 m of one u and the two unknowns trade off along the sightline.
#
# Lloyd: "in one of the videos I referenced I walk along the balcony." That walk is b3, and it does not need
# to see the parapet to rule on it. It needs only two facts that do not depend on reading an edge:
#
#   1. NOBODY WALKS IN MID-AIR. The parapet's face is the west limit of the deck. A camera carried along that
#      deck stands behind it, give or take a lean over the coping. So the deepest excursion west of a
#      candidate face is a cost that candidate has to pay, and it is measured, not argued.
#   2. LIGHT THAT ARRIVED WAS NOT BLOCKED. Every point triangulated in the hall from a deck camera sent a ray
#      over the parapet. Where that ray crosses the candidate face, its height is a CEILING on the parapet
#      top: a top any higher would have caught it. The lowest arriving ray wins, and one camera is enough,
#      so this has no conditioning problem at all.
#
# Both tests are one-sided and neither invents a measurement of the stone. Together they say which of the two
# candidate pairs the walk can live with.
#   python tools/parapet_arrival.py [max-pairs-per-clip]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK = 8.34
DRAWN = (48.056, 9.110)
RIVAL = (48.702, 9.391)                      # tools/parapet_silhouette.py, the line that fit 1.8x better
CLASSES = ('b3p', 'b3', 'b7sp', 'b7s', 'b6gp', 'b6g')
MINBASE, MAXBASE, MAXMISS = 0.15, 3.0, 0.02
FAR_MIN, FAR_MAX = 8.0, 60.0                 # a point in the hall, not something on the deck
BOTTOM = 0.60                                # the low half of the frame carries the low, binding sightlines
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


maxpairs = int(sys.argv[1]) if len(sys.argv) > 1 else 300
byclip = {}
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
        if not (47.5 < cu < 52.2 and ch > 8.7):
            continue
        seen.add(f)
        byclip.setdefault(f.split('_')[0], []).append((f, cam, ip))

# ---------------------------------------------------------------- 1. nobody walks in mid-air
print('TEST ONE: HOW FAR WEST OF EACH CANDIDATE FACE THE OPERATOR HAD TO BE STANDING')
print('a lean over a coping puts the lens a little past the face; walking a gallery does not put it a lot.')
allcam = [(f, cam) for items in byclip.values() for f, cam, _ip in items]
CU = np.array([float((cam.center - O) @ HU) for _f, cam in allcam])
for name, (uf, _tp) in (('drawn 48.056', DRAWN), ('rival 48.702', RIVAL)):
    out = uf - CU                                     # positive = the lens is west of the face, in the void
    n = int((out > 0).sum())
    worst = int(np.argmax(out))
    print('   %-13s %3d of %3d cameras stand west of it; deepest %s at %.3f m past the face'
          % (name, n, len(CU), allcam[worst][0], float(out[worst])))
    print('                 median excursion of those %d: %.3f m'
          % (n, float(np.median(out[out > 0])) if n else 0.0))

# ---------------------------------------------------------------- 2. light that arrived was not blocked
print('')
print('TEST TWO: HOW MANY ARRIVALS EACH CANDIDATE PARAPET WOULD HAVE HAD TO BLOCK')
# THE FIRST RUN TOOK THE SINGLE LOWEST RAY AND REFUTED BOTH CANDIDATES, which is how a one-sided bound
# tells you it has found an outlier rather than a fact. Over 8,685 far points, matched across baselines of
# 0.15 to 3 m at ranges of 8 to 60 m, a handful of pairs of near-parallel rays will agree to 20 mm on a
# point that is not there, and the MINIMUM is exactly the statistic a single bad point owns. The honest
# question is not "is there one ray below the candidate" but "how much of the light this camera actually
# received would that candidate have stopped", so every crossing is kept and counted.
stations = np.arange(47.60, 49.31, 0.05)
RAYS = []
nrays = 0
for clip, items in sorted(byclip.items()):
    items.sort()
    feats = []
    for f, cam, ip in items:
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        mask = np.zeros(img.shape, np.uint8)
        mask[int(img.shape[0] * (1.0 - BOTTOM)):, :] = 255
        kp, de = sift.detectAndCompute(img, mask)
        if de is not None and len(kp) >= 30:
            feats.append((f, cam, np.array([k.pt for k in kp]), de))
    bf = cv2.BFMatcher(cv2.NORM_L2)
    made = 0
    for i in range(len(feats)):
        for j in range(i + 1, min(i + 9, len(feats))):
            if made >= maxpairs:
                break
            fa, ca, pa_all, da = feats[i]
            _fb, cb, pb_all, db = feats[j]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < MINBASE or base > MAXBASE:
                continue
            mm = bf.knnMatch(da, db, k=2)
            good = [m for m, n in mm if m.distance < 0.7 * n.distance]
            if len(good) < 12:
                continue
            pa = pa_all[[m.queryIdx for m in good]]
            pb = pb_all[[m.trainIdx for m in good]]
            va, vb = unit_rays(ca, pa), unit_rays(cb, pb)
            P, miss, s, t = meet(ca.center, va, cb.center, vb)
            keep = np.logical_and.reduce((miss < MAXMISS, s > FAR_MIN, s < FAR_MAX,
                                          t > FAR_MIN, t < FAR_MAX))
            idx = np.where(keep)[0]
            if not len(idx):
                made += 1
                continue
            cu = float((ca.center - O) @ HU)
            ch = float(ca.center[1] - O[1])
            # only arrivals whose far point is INSIDE the building are believable; a match that lands
            # outside the hall is a mismatch and its ray is not evidence about anything.
            Q = P[idx] - O
            pu, pd, ph = Q @ HU, Q @ HD, P[idx][:, 1] - O[1]
            good2 = np.logical_and.reduce((pu > 0.2, pu < 52.0, pd > -0.3, pd < 15.6, ph > -0.3, ph < 13.6))
            g = idx[good2]
            if not len(g):
                made += 1
                continue
            RAYS.append(np.stack([np.full(len(g), cu), np.full(len(g), ch),
                                  va[g] @ HU, va[g][:, 1], s[g]], 1))
            nrays += len(g)
            made += 1
print('   %d arriving rays from the deck clips, all landing inside the building' % nrays)
if nrays < 200:
    raise SystemExit('too few arrivals to bound anything')
R = np.concatenate(RAYS, 0)
print('')
print('   face      arrivals that      the drawn top 9.110      the rival top 9.391')
print('   station   cross it           would have blocked        would have blocked')
for si, ust in enumerate(stations):
    lam = (ust - R[:, 0]) / np.where(np.abs(R[:, 2]) < 1e-6, 1e-6, R[:, 2])
    ok = np.logical_and(lam > 0.02, lam < R[:, 4])
    if ok.sum() < 20:
        continue
    hc = R[ok, 1] + R[ok, 3] * lam[ok]
    nd = int((hc < DRAWN[1]).sum())
    nr = int((hc < RIVAL[1]).sum())
    if si % 4 == 0 or abs(ust - DRAWN[0]) < 0.03 or abs(ust - RIVAL[0]) < 0.03:
        print('   %7.3f   %6d            %6d  (%5.2f%%)        %6d  (%5.2f%%)'
              % (ust, int(ok.sum()), nd, 100.0 * nd / ok.sum(), nr, 100.0 * nr / ok.sum()))
print('')
for name, (uf, tp) in (('drawn', DRAWN), ('rival', RIVAL)):
    lam = (uf - R[:, 0]) / np.where(np.abs(R[:, 2]) < 1e-6, 1e-6, R[:, 2])
    ok = np.logical_and(lam > 0.02, lam < R[:, 4])
    hc = np.sort(R[ok, 1] + R[ok, 3] * lam[ok])
    n = int((hc < tp).sum())
    print('   %s pair (%.3f, %.3f): of %d arrivals crossing that face, %d (%.2f%%) passed below its top.'
          % (name, uf, tp, len(hc), n, 100.0 * n / max(len(hc), 1)))
    print('        the 0.1st, 1st and 5th percentiles of those crossings are %.3f, %.3f and %.3f'
          % (float(np.percentile(hc, 0.1)), float(np.percentile(hc, 1)), float(np.percentile(hc, 5))))
print('')
print('   the deck under the parapet is drawn on %.3f, so each candidate top is an upstand plus rail of'
      % DECK)
for name, (_uf, tp) in (('drawn', DRAWN), ('rival', RIVAL)):
    print('      %-6s %.3f m above the deck' % (name, tp - DECK))
