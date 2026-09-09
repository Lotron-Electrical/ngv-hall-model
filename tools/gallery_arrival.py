# 2026-09-09: THE SAME TWO TESTS TAKEN TO THE WEST END, where the upstand has never been measured at all.
#
# tools/parapet_arrival.py settled the east parapet with two facts that need no view of the stone: nobody
# walks in mid-air, and light that arrived was not blocked. Both are general, and the west end has been
# sitting in the unmeasured list all day with its upstand of 0.68 m resting on nothing but symmetry with
# the east one, which is itself only bounded to a quarter of a metre.
#
# WHY THE WEST END IS THE BETTER SUBJECT OF THE TWO. b7s walks it as well, sixteen posed cameras between
# u 3.19 and 3.33 and d 12.82 to 14.03, and they are pitched down 12 to 23 degrees rather than the east
# clips' 3 to 10. A steeper look means a lower sightline over the coping, and the arrival bound is exactly
# as tight as the lowest ray that got out. It also means the lens is nearly a metre BEHIND the drawn face
# rather than leaning over it, so the two tests are being asked of a different geometry and not a mirrored
# copy of the one already run.
#
# Nothing drawn is searched for: the stations sweep a metre either side of each drawn face, and every
# candidate top from the deck to a metre and a half above it is scored against the arrivals.
#   python tools/gallery_arrival.py [east|west] [max-pairs-per-clip]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK = 8.34
# end: (drawn parapet face u, the sign that points from the gallery out into the hall, drawn upstand)
ENDS = {'east': (48.056, -1.0, 0.770), 'west': (4.194, +1.0, 0.680)}
CLASSES = ('b1p', 'b3p', 'b5p', 'b7sp', 'b6gp', 'b1', 'b3', 'b4', 'b5', 'b7s', 'b6g', 'day4k')
MINBASE, MAXBASE, MAXMISS = 0.10, 3.0, 0.02
FAR_MIN, FAR_MAX = 6.0, 60.0
BOTTOM = 0.60
sift = cv2.SIFT_create(nfeatures=3000)


# A SENSITIVITY KNOB, NOT A CALIBRATION. tools/focal_probe.py finds that b7s, the clip both end-deck
# results rest on, agrees with itself 46 per cent better when its frozen focal is scaled by 0.965. That is
# not proof the lens is wrong, but it does mean any conclusion drawn from these rays has to survive the
# question. Set FOCAL to re-run the whole test on rays made with a scaled focal length.
FOCAL = float(os.environ.get('FOCAL', '1.0'))


def unit_rays(cam, pts):
    fx, fy, ux, uy = cam.params[0] * FOCAL, cam.params[1] * FOCAL, cam.params[2], cam.params[3]
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


end = sys.argv[1] if len(sys.argv) > 1 else 'west'
maxpairs = int(sys.argv[2]) if len(sys.argv) > 2 else 300
# THE CONTROL THAT THE FIRST RUN DID NOT HAVE. How much of a frame can cross the face below the coping is
# mostly a function of HOW FAR BACK THE LENS IS: a lens 0.2 m behind the stone has to look 77 degrees down
# before its ray crosses low, and a lens a metre back only 35. The east pool was 140 b3 frames standing
# almost on the face, so its 1.62 % was never comparable with the west pool's metre of setback. Passing a
# minimum setback here makes the two ends the same experiment.
SETBACK = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
UF, OUTWARD, UPSTAND = ENDS[end]
TOPD = DECK + UPSTAND

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
        if ch < 8.7 or (cu - UF) * OUTWARD > 0.35 or abs(cu - UF) > 4.2:
            continue                       # standing on that end's deck, not out in the hall
        if (UF - cu) * OUTWARD < SETBACK:
            continue                       # matched setback, so the two ends are the same experiment
        seen.add(f)
        byclip.setdefault(f.split('_')[0], []).append((f, cam, ip))
n = sum(len(v) for v in byclip.values())
print('THE %s GALLERY, lenses at least %.2f m behind the drawn face: %d posed cameras, by clip %s'
      % (end.upper(), SETBACK, n, {k: len(v) for k, v in sorted(byclip.items())}))
if n < 6:
    raise SystemExit('nothing stands on that deck')

# ------------------------------------------------------------------ 1. nobody walks in mid-air
allcam = [(f, cam) for items in byclip.values() for f, cam, _ip in items]
CU = np.array([float((cam.center - O) @ HU) for _f, cam in allcam])
out = (CU - UF) * OUTWARD                              # positive = the lens is out over the hall
worst = int(np.argmax(out))
print('')
print('TEST ONE, WHERE THE OPERATOR STOOD')
print('   the drawn face is u %.3f; the lens that came closest to it is %s, %.3f m %s of the face'
      % (UF, allcam[worst][0], abs(float(out[worst])),
         'out over the hall' if out[worst] > 0 else 'back from it'))
print('   %d of %d lenses are out past the drawn face; a face %.3f m further into the hall would put'
      % (int((out > 0).sum()), len(CU), 0.25 - float(out[worst])))
print('   the deepest of them more than the 0.25 m of a lean over a coping')

# ------------------------------------------------------------------ 2. light that arrived was not blocked
print('')
print('TEST TWO, WHAT GOT OUT OVER THE COPING')
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
            _fa, ca, pa_all, da = feats[i]
            _fb, cb, pb_all, db = feats[j]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < MINBASE or base > MAXBASE:
                continue
            mm = bf.knnMatch(da, db, k=2)
            good = [m for m, nn in mm if m.distance < 0.7 * nn.distance]
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
            Q = P[idx] - O
            pu, pd, ph = Q @ HU, Q @ HD, P[idx][:, 1] - O[1]
            g = idx[np.logical_and.reduce((pu > 0.2, pu < 52.0, pd > -0.3, pd < 15.6,
                                           ph > -0.3, ph < 13.6))]
            if not len(g):
                made += 1
                continue
            cu = float((ca.center - O) @ HU)
            ch = float(ca.center[1] - O[1])
            RAYS.append(np.stack([np.full(len(g), cu), np.full(len(g), ch),
                                  va[g] @ HU, va[g][:, 1], s[g]], 1))
            nrays += len(g)
            made += 1
print('   %d rays arrived from points inside the building' % nrays)
if nrays < 200:
    raise SystemExit('too few arrivals on this deck to bound anything')
R = np.concatenate(RAYS, 0)


def crossings(uf):
    lam = (uf - R[:, 0]) / np.where(np.abs(R[:, 2]) < 1e-6, 1e-6, R[:, 2])
    ok = np.logical_and(lam > 0.02, lam < R[:, 4])
    return np.sort(R[ok, 1] + R[ok, 3] * lam[ok])


print('')
print('   face station   arrivals   1st pct   5th pct   %% below the drawn top %.3f' % TOPD)
for uf in np.arange(UF - 1.0, UF + 1.001, 0.20):
    hc = crossings(float(uf))
    if len(hc) < 50:
        continue
    print('   %10.3f   %8d   %7.3f   %7.3f   %6.2f%%'
          % (uf, len(hc), float(np.percentile(hc, 1)), float(np.percentile(hc, 5)),
             100.0 * float((hc < TOPD).mean())))

hc = crossings(UF)
print('')
print('AT THE DRAWN FACE u %.3f' % UF)
print('   %d arrivals crossed it. The 5th percentile crossed on h %.3f, so a parapet top up there would'
      % (len(hc), float(np.percentile(hc, 5))))
print('   have stopped one arrival in twenty. The drawn top is %.3f, deck %.3f plus an upstand of %.3f.'
      % (TOPD, DECK, UPSTAND))
print('   %.2f%% of the arrivals passed BELOW the drawn top; the bracket on the top is therefore'
      % (100.0 * float((hc < TOPD).mean())))
print('   %.3f to %.3f, %.3f m wide, and it is the first number this end has ever had.'
      % (TOPD, float(np.percentile(hc, 5)), float(np.percentile(hc, 5)) - TOPD))
print('')
print('   for the record the same percentiles: 0.1st %.3f, 1st %.3f, 5th %.3f, 10th %.3f'
      % (float(np.percentile(hc, 0.1)), float(np.percentile(hc, 1)),
         float(np.percentile(hc, 5)), float(np.percentile(hc, 10))))
