# 2026-09-09: THE PARAPET THE OPERATOR IS LEANING OVER, triangulated on the ONE baseline that can see it.
#
# Lloyd walks along the east top gallery in b3, 3.52 m of it, and the first cloud built from that walk put
# 7,120 points in the air beside him and no sheet anywhere near the parapet. The reason is geometry, not
# footage. Every posed frame on that deck looks WEST down the hall (tools/balcony_walk.py: 163 frames on the
# east deck, 163 of them aimed down the hall, none aimed at the gallery). The only near surface in those
# frames is the parapet coping along the bottom edge, and the coping RUNS ALONG THE WALK. A feature on a line
# parallel to the baseline slides along its own epipolar line, so walking past it triangulates nothing.
#
# WHAT DOES SEE IT is the operator's hand. Across those 140 frames the lens rises and falls from h 9.56 to
# 10.23, and vertical motion is square across the coping edge. A vertical baseline of 0.3 to 0.7 m, with the
# stone a metre or so away, is a better stereo pair than anything else in the archive has had on this edge;
# the silhouette fit failed on 0.68 m of HORIZONTAL span the same distance away, because horizontal span is
# the degenerate direction here and vertical span is not.
#
# So this picks pairs by VERTICAL baseline, works on the bottom of the frame where a downward-pitched camera
# puts the near field, and keeps only points several independent pairs agree on. The window spans 2 m either
# side of the drawn face and 1.5 m either side of the drawn top, so a parapet well out of place still lands
# inside it, and the drawn stations are printed next to whatever comes back rather than searched for.
#   python tools/coping_cloud.py [max-pairs]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UFACE, UBACK, DECK, TOP, SOFFIT = 48.056, 51.906, 8.34, 9.11, 11.1
CLASSES = ('b3p', 'b3', 'b7sp', 'b7s', 'b6gp', 'b6g')
DVMIN, BMAX, MAXMISS = 0.12, 2.5, 0.02       # vertical baseline, total baseline, ray agreement
RNEAR, RFAR = 0.4, 4.0                       # a point this close is the parapet or the deck, not the hall
BOTTOM = 0.40                                # the lower part of the frame, where a pitched lens looks near
VOX, SUPPORT = 0.04, 4                       # a point survives only if several pairs put one in its cell
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


maxpairs = int(sys.argv[1]) if len(sys.argv) > 1 else 500
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
print('frames on the east deck by clip:', {k: len(v) for k, v in sorted(byclip.items())})

pts = []
for clip, items in sorted(byclip.items()):
    items.sort()
    YCEN = np.array([it[1].center[1] for it in items])
    CEN = np.array([it[1].center for it in items])
    cand = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            dv = abs(float(YCEN[i] - YCEN[j]))
            base = float(np.linalg.norm(CEN[i] - CEN[j]))
            if dv < DVMIN or base > BMAX:
                continue
            cand.append((-dv, i, j))
    cand.sort()
    cand = cand[:maxpairs]
    print('  %-5s %3d frames, %d usable vertical pairs' % (clip, len(items), len(cand)))
    if not cand:
        continue
    need = sorted(set([i for _dv, i, _j in cand] + [j for _dv, _i, j in cand]))
    feats = {}
    for i in need:
        f, cam, ip = items[i]
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        mask = np.zeros(img.shape, np.uint8)
        mask[int(img.shape[0] * (1.0 - BOTTOM)):, :] = 255
        kp, de = sift.detectAndCompute(img, mask)
        if de is not None and len(kp) >= 30:
            feats[i] = (cam, np.array([k.pt for k in kp]), de)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    made, before = 0, len(pts)
    for _dv, i, j in cand:
        if i not in feats or j not in feats:
            continue
        ca, pa_all, da = feats[i]
        cb, pb_all, db = feats[j]
        mm = bf.knnMatch(da, db, k=2)
        good = [m for m, n in mm if m.distance < 0.75 * n.distance]
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

if len(pts) < 100:
    raise SystemExit('the vertical baselines produced almost nothing; nothing to read')
A = np.array(pts)
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-coping-east.npy'), A)
print('%d near points triangulated on vertical baselines' % len(A))

# SUPPORT. A wrong match still lands somewhere, and one pair cannot tell a surface from a coincidence.
# A real surface point is put in the same 40 mm cell by several independent pairs; a coincidence is not.
key = np.floor(A / VOX).astype(np.int64)
_u, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
S = A[cnt[inv] >= SUPPORT]
print('%d of them sit in a %.0f mm cell that %d or more points agree on' % (len(S), VOX * 1000, SUPPORT))
if len(S) < 60:
    raise SystemExit('no cell carried support, so this refuses rather than reporting the noise')


def sheets(vals, lo, hi, step, label, drawn, n=5):
    edges = np.arange(lo, hi + 1e-9, step)
    h, _ = np.histogram(vals, bins=edges)
    sm = np.convolve(h, np.ones(3), 'same')
    picked = []
    for k in np.argsort(sm)[::-1]:
        c = float(0.5 * (edges[k] + edges[k + 1]))
        if any(abs(c - p[0]) < 0.10 for p in picked):
            continue
        picked.append((c, int(h[max(0, k - 1):k + 2].sum())))
        if len(picked) >= n:
            break
    print('')
    print('   %s' % label)
    for c, cnt2 in picked:
        near = min(drawn, key=lambda dv: abs(dv - c))
        print('      %8.3f  %5d points   nearest drawn %8.3f   %+.3f' % (c, cnt2, near, c - near))
    return picked


W = S[np.logical_and.reduce((S[:, 0] > 46.0, S[:, 0] < 50.5, S[:, 2] > 7.6, S[:, 2] < 11.0))]
print('')
print('%d supported points in the window u 46.0-50.5, h 7.6-11.0: 2 m either side of the drawn face' % len(W))
if len(W) < 60:
    raise SystemExit('the supported points are not in the parapet window; refused')
print('they lie between d %.2f and %.2f' % (float(W[:, 1].min()), float(W[:, 1].max())))
sheets(W[:, 0], 46.0, 50.5, 0.02, 'ACROSS: where the near stone stands in u', [UFACE, UBACK])
sheets(W[:, 2], 7.6, 11.0, 0.02, 'UP: the near levels', [DECK, TOP, SOFFIT])

# THE COPING AS A SOLID. Take the highest level that carries a sheet, then ask where in u it starts and
# stops. Its height is the parapet top; its west edge is the face. Neither is derived from the other, which
# is the whole point: one frame, or many frames sharing one u, cannot separate them and this can.
edges = np.arange(8.4, 10.6 + 1e-9, 0.02)
cnt2, _ = np.histogram(W[:, 2], bins=edges)
floor_n = max(8, int(0.02 * len(W)))
tops = [k for k in range(len(cnt2)) if cnt2[k] >= floor_n]
print('')
print('   a level counts as a sheet at %d supported points per 20 mm; %d of the 110 levels qualify'
      % (floor_n, len(tops)))
if tops:
    k = max(tops)
    band = W[np.logical_and(W[:, 2] > edges[k] - 0.06, W[:, 2] < edges[k + 1] + 0.02)]
    us = np.sort(band[:, 0])
    hmid = float(0.5 * (edges[k] + edges[k + 1]))
    print('   the highest sheet sits on h %.3f with %d points, spanning u %.3f to %.3f'
          % (hmid, len(band), us[0], us[-1]))
    print('   its 5th to 95th percentile in u is %.3f to %.3f, %.3f m wide'
          % (float(np.percentile(us, 5)), float(np.percentile(us, 95)),
             float(np.percentile(us, 95) - np.percentile(us, 5))))
    print('   drawn top %.3f face %.3f: the top reads %+.3f and the west edge of the sheet %+.3f'
          % (TOP, UFACE, hmid - TOP, float(np.percentile(us, 5)) - UFACE))
