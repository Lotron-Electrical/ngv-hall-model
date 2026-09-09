# 2026-09-09: THE NORTH WALL MEASURED FROM ONE METRE, out of the clips that stand in its openings.
#
# NOT to be confused with tools/opening_cloud.py, which reads the CERTIFIED SPARSE cloud inside the same
# openings. This one builds its own dense near-field cloud from the balcony clips and is a different
# instrument on the same wall; the older file is untouched.
#
# dNorth has been in the unmeasured list all day for a good reason. Every cloud aimed at that wall was
# built from hall-floor cameras: the closest square view is 5.93 m, the median is 12.92 m, the house rig
# points away from it so it is dark, and the sheet that came back moved 0.12 m when the frame selection
# changed. That is not a measurement of a wall, it is a measurement of the frame list.
#
# BUT THREE CLIPS DO NOT STAND ON THE FLOOR. b1, b4 and b5 stand IN the north openings at h 9.1 to 10.1
# with the lens between d -0.45 and +0.16, which is inside the reveal and a metre or less from stone on
# three sides. That is the south wall's case, not the north wall's: the south wall gave 31,234 points on
# one sheet with a 0.03 m interquartile spread when it was seen close and square.
#
# AND THE CONFIGURATION IS UNUSUALLY GOOD. b1 alone carries 138 posed frames at one station spanning 0.81 m
# of u, 0.61 m of d and 1.05 m of HEIGHT. A metre of vertical baseline against a surface a metre away is
# the best stereo geometry anywhere in this archive; it is the baseline the east coping did not have.
#
# NOTHING DRAWN IS SEARCHED FOR. Points are triangulated first, kept only where several independent pairs
# agree, and sorted into surfaces afterwards. The drawn stations are printed beside the peaks the cloud
# actually has, and the window is two metres of wall either side of them.
#   python tools/opening_nearcloud.py [max-pairs-per-clip]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH, REVEAL, CORRIDOR = -0.090, -0.990, -2.090      # face, back of the reveal, back of the corridor
SILL, HEAD = 8.99, 11.35
CLASSES = ('b1p', 'b1', 'b4', 'b5p', 'b5')
MINBASE, MAXBASE, MAXMISS = 0.15, 1.6, 0.015
RNEAR, RFAR = 0.25, 4.0
VOX, SUPPORT = 0.03, 4
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
sift = cv2.SIFT_create(nfeatures=4000)


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


maxpairs = int(sys.argv[1]) if len(sys.argv) > 1 else 700
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
        cd, ch = float(q @ HD), float(cam.center[1] - O[1])
        if ch < 8.7 or cd > 1.2 or cd < -1.2:
            continue                       # standing in or at a north opening
        seen.add(f)
        byclip.setdefault(f.split('_')[0], []).append((f, cam, ip))
print('frames standing at the north openings, by clip:', {k: len(v) for k, v in sorted(byclip.items())})

pts = []
for clip, items in sorted(byclip.items()):
    items.sort()
    CEN = np.array([it[1].center for it in items])
    cand = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            base = float(np.linalg.norm(CEN[i] - CEN[j]))
            if base < MINBASE or base > MAXBASE:
                continue
            cand.append((-base, i, j))     # the longest baselines first, they resolve depth best
    cand.sort()
    cand = cand[:maxpairs]
    print('  %-5s %3d frames, %d pairs between %.2f and %.2f m, using %d'
          % (clip, len(items), len(cand), MINBASE, MAXBASE, len(cand)))
    if not cand:
        continue
    need = sorted(set([i for _b, i, _j in cand] + [j for _b, _i, j in cand]))
    feats = {}
    for i in need:
        f, cam, ip = items[i]
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        kp, de = sift.detectAndCompute(img, None)
        if de is not None and len(kp) >= 30:
            feats[i] = (cam, np.array([k.pt for k in kp]), de)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    made, before = 0, len(pts)
    for _b, i, j in cand:
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
        P, miss, s, t = meet(ca.center, va, cb.center, vb)
        keep = np.logical_and.reduce((miss < MAXMISS, s > RNEAR, s < RFAR, t > RNEAR, t < RFAR))
        for k in np.where(keep)[0]:
            q = P[k] - O
            pts.append((float(q @ HU), float(q @ HD), float(P[k][1] - O[1])))
        made += 1
    print('        %d pairs matched, %d near points' % (made, len(pts) - before))

if len(pts) < 300:
    raise SystemExit('the openings did not give a near cloud; nothing to read')
A = np.array(pts)
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-openings.npy'), A)
print('%d near points triangulated' % len(A))

key = np.floor(A / VOX).astype(np.int64)
_u, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
S = A[cnt[inv] >= SUPPORT]
print('%d of them sit in a %.0f mm cell that %d or more points agree on' % (len(S), VOX * 1000, SUPPORT))
if len(S) < 150:
    raise SystemExit('no cell carried support; this refuses rather than reporting noise')


def sheets(vals, lo, hi, step, label, drawn, n=6):
    edges = np.arange(lo, hi + 1e-9, step)
    h, _ = np.histogram(vals, bins=edges)
    sm = np.convolve(h, np.ones(3), 'same')
    picked = []
    for k in np.argsort(sm)[::-1]:
        c = float(0.5 * (edges[k] + edges[k + 1]))
        if any(abs(c - p[0]) < 0.08 for p in picked):
            continue
        picked.append((c, int(h[max(0, k - 1):k + 2].sum())))
        if len(picked) >= n:
            break
    print('')
    print('   %s' % label)
    for c, c2 in picked:
        near = min(drawn, key=lambda dv: abs(dv - c))
        print('      %8.3f  %5d points   nearest drawn %8.3f   %+.3f' % (c, c2, near, c - near))
    return picked


W = S[np.logical_and.reduce((S[:, 1] > -2.6, S[:, 1] < 1.9, S[:, 2] > 8.0, S[:, 2] < 12.4))]
print('')
print('%d supported points in the wall window: d -2.6 to 1.9, h 8.0 to 12.4' % len(W))
if len(W) < 120:
    raise SystemExit('the supported points are not at the wall; refused')
sheets(W[:, 1], -2.6, 1.9, 0.01, 'ACROSS the wall (d): the sheets the cloud has',
       [DNORTH, REVEAL, CORRIDOR])
sheets(W[:, 2], 8.0, 12.4, 0.01, 'UP (h): sill, head and whatever else is there', [SILL, HEAD])

# THE FACE ITSELF, fitted rather than binned, on the densest 0.10 m slab of d. This is the same estimator
# the south wall was measured with, so the two answers are comparable and the north one can be judged
# against a 0.03 m interquartile spread that is known to be achievable.
edges = np.arange(-2.6, 1.9, 0.01)
h, _ = np.histogram(W[:, 1], bins=edges)
k = int(np.argmax(np.convolve(h, np.ones(10), 'same')))
c = float(0.5 * (edges[k] + edges[k + 1]))
slab = W[np.abs(W[:, 1] - c) < 0.05]
print('')
print('   the densest 100 mm slab of wall sits on d %.3f and holds %d points' % (c, len(slab)))
if len(slab) >= 60:
    A2 = np.stack([np.ones(len(slab)), slab[:, 0], slab[:, 2]], 1)
    sol, _r, _rk, _sv = np.linalg.lstsq(A2, slab[:, 1], rcond=None)
    res = A2 @ sol - slab[:, 1]
    q1, q3 = np.percentile(slab[:, 1], [25, 75])
    print('   fitted d = %.4f %+.5f*u %+.5f*h, residual rms %.4f m, interquartile spread %.3f m'
          % (sol[0], sol[1], sol[2], float(np.sqrt((res ** 2).mean())), float(q3 - q1)))
    print('   over the 12 m of wall those points span that plane leans %.3f m; the sim draws the face on '
          '%.3f' % (abs(float(sol[1])) * 12.0, DNORTH))
    print('   so this sheet reads %+.3f m against the drawn face' % (c - DNORTH))
