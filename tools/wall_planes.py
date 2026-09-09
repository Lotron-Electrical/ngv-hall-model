# 2026-09-09: THE TWO LONG WALLS MEASURED AS PLANES, from the hall's own walk footage.
#
# Everything on these walls hangs off two numbers, WALLF.dNorth -0.090 and WALLF.dSouth 15.364. They came
# from a plane fitted to the certified scan, and nothing since has re-derived them: the openings, the
# reveals, the corridor and every level on the end galleries are all positioned against them, so a common
# error in either would move all of it together and no edge measurement would notice.
#
# The instrument is the one that worked on b4 this afternoon rather than the ones that failed. Matching a
# clip against ITSELF gives thousands of triangulated points, because consecutive frames share exposure,
# lens and lighting and the surface fills the frame; matching between captures through a slot gave three
# usable pairs all day. The walks run the length of the hall at floor level with both long walls a few
# metres away, so their own frames are exactly the pair a wall plane needs.
#
# WHAT IS AND IS NOT ASSUMED. The drawn planes are used ONLY to say which slab of space to collect points
# from, and the slab is 1.5 m thick either side so a wall half a metre out would still be caught. Within
# that slab the plane is fitted to the points, free in offset AND in tilt along the hall, and the residual
# is reported so a bow shows up instead of averaging away. Heights below the openings are used, where the
# wall is plain ashlar, so no reveal or fitting biases the fit.
#   python tools/wall_planes.py [class] [maxframes]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH, DSOUTH = -0.090, 15.364
SLAB = 1.5
HLO, HHI = 1.0, 8.0              # plain ashlar, below every opening and above the skirting clutter
MINBASE, MAXBASE = 0.30, 4.0
MAXMISS = 0.03
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


cls = sys.argv[1] if len(sys.argv) > 1 else 'walk'
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 160
frames = U.load_class(cls)
clips = {}
for f in frames:
    clips.setdefault(f.split('_')[0], []).append(f)
for k in clips:
    clips[k].sort()
print(cls, len(frames), 'poses in', len(clips), 'clips:', {k: len(v) for k, v in sorted(clips.items())})

pts = []
for clip, names in sorted(clips.items()):
    take = names[:: max(1, len(names) // maxf)][:maxf]
    feats = {}
    for f in take:
        cam, ip = frames[f]
        img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        kp, de = sift.detectAndCompute(img, None)
        if de is not None and len(kp) >= 40:
            feats[f] = (cam, kp, de)
    ns = sorted(feats)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    made = 0
    for i in range(len(ns)):
        for j in range(i + 1, min(i + 7, len(ns))):
            ca, ka, da = feats[ns[i]]
            cb, kb, db = feats[ns[j]]
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
    print('  ', clip, len(feats), 'frames with features,', made, 'pairs used, running total',
          len(pts), 'points')

A = np.array(pts)
print(len(A), 'points triangulated in all')
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'cloud-%s.npy' % cls), A)


def fit(name, drawn):
    sel = np.logical_and(np.abs(A[:, 1] - drawn) < SLAB,
                         np.logical_and(A[:, 2] > HLO, A[:, 2] < HHI))
    sel = np.logical_and(sel, np.logical_and(A[:, 0] > 1.0, A[:, 0] < 51.0))
    W = A[sel]
    print('')
    print('%s wall, drawn on d %.3f: %d points in the %.1f m slab either side'
          % (name, drawn, len(W), SLAB))
    if len(W) < 300:
        print('   too few to fit a plane')
        return
    # the wall is the DENSEST sheet in that slab, not its average: the slab also holds tapestries hanging
    # off the face, people standing in front of it and the odd stray point
    hist, edges = np.histogram(W[:, 1], bins=np.arange(drawn - SLAB, drawn + SLAB, 0.01))
    k = int(np.argmax(np.convolve(hist, np.ones(9), 'same')))
    peak = float(0.5 * (edges[k] + edges[k + 1]))
    S = W[np.abs(W[:, 1] - peak) < 0.10]
    print('   the densest sheet in it sits on d %.3f and holds %d points' % (peak, len(S)))
    if len(S) < 200:
        print('   that sheet is too thin to fit')
        return
    G = np.stack([S[:, 0], S[:, 2], np.ones(len(S))], 1)
    coef, *_ = np.linalg.lstsq(G, S[:, 1], rcond=None)
    resid = S[:, 1] - G @ coef
    print('   fitted plane: d = %.5f + %.5f*u + %.5f*h, residual rms %.4f m, %d points'
          % (coef[2], coef[0], coef[1], float(np.sqrt((resid ** 2).mean())), len(S)))
    mid = coef[2] + coef[0] * 26.0 + coef[1] * 4.5
    print('   at the middle of the hall it stands on d %.4f, and the sim draws %.3f, a difference of %+.4f m'
          % (mid, drawn, mid - drawn))
    print('   over the 50 m length it leans %+.4f m, and over the 7 m height %+.4f m'
          % (coef[0] * 50.0, coef[1] * 7.0))


fit('NORTH', DNORTH)
fit('SOUTH', DSOUTH)
