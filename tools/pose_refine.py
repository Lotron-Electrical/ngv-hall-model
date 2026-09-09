# 2026-09-09: STOP MEASURING AROUND THE POSE ERROR AND REDUCE IT.
#
# tools/pose_selfcheck.py put a number on the ceiling every balcony measurement has been hitting: matched
# rays in these clips pass 0.061 to 0.200 m apart in the near field. That is why the north wall gave 560
# supported points instead of 31,234, and why the west parapet's 0.202 m disagreement cannot be told from
# noise. Every instrument built today has worked AROUND that number. This one attacks it.
#
# WHY THERE IS ROOM TO. Each clip was registered against the SITE model with the day4k camera frozen, and
# the site model carries the hall, not the balcony. A frame standing on a deck has little in that model to
# match, so its pose was fixed by a handful of distant correspondences and never checked against the thing
# the frame actually looks at, which is its own neighbours a few frames away. Those neighbours are a dense,
# unused constraint.
#
# HOW, without a bundle adjuster and without cutting the clip loose from the building. Alternating
# resection and intersection: triangulate the clip's own tracks from the poses as they stand, then re-solve
# each camera against those points, then repeat. The scene is rebuilt from the poses at every round, so it
# stays in the hall frame, and each camera is CAPPED to 0.20 m of movement and 3 degrees of rotation from
# where the registration put it. A clip that needs more than that to agree with itself is not being
# refined, it is being moved, and the cap refuses.
#
# WHAT IS AND IS NOT EVIDENCE OF SUCCESS. The ray miss is the thing being minimised, so its fall is not by
# itself a result; it is reported because it is the number every other tool cares about. The honest checks
# are the two beside it: how far the cameras actually had to move, and whether the movement stays well
# inside the registration's own stated error.
#   python tools/pose_refine.py <class> [rounds] [apply]
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import trackA_geom as G  # noqa: E402
import underside_geom as U  # noqa: E402

CAP_T, CAP_R = 0.20, np.deg2rad(3.0)
WIN, MINTRACK, MAXREPROJ, MINANG = 5, 3, 8.0, np.deg2rad(1.0)
RNEAR, RFAR = 0.25, 60.0
sift = cv2.SIFT_create(nfeatures=3000)


def kmat(cam):
    return (np.array([[cam.params[0], 0, cam.params[2]], [0, cam.params[1], cam.params[3]], [0, 0, 1]],
                     float),
            np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4))


def rays_of(cam, pts):
    K, dist = kmat(cam)
    un = cv2.undistortPoints(np.asarray(pts, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def triangulate(cs, vs):
    """the point closest to a bundle of rays: sum (I - v v^T) X = sum (I - v v^T) C"""
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for c, v in zip(cs, vs):
        M = np.eye(3) - np.outer(v, v)
        A += M
        b += M @ c
    if abs(np.linalg.det(A)) < 1e-9:
        return None
    return np.linalg.solve(A, b)


def miss_metric(items):
    """the self-check number: how far apart matched rays pass in the near field, median in metres"""
    out = []
    for i in range(len(items)):
        for j in range(i + 1, min(i + WIN, len(items))):
            _fa, ca, ka, da = items[i]
            _fb, cb, kb, db = items[j]
            base = float(np.linalg.norm(ca.center - cb.center))
            if base < 0.10 or base > 2.0:
                continue
            mm = bf.knnMatch(da, db, k=2)
            good = [m for m, nn in mm if m.distance < 0.72 * nn.distance]
            if len(good) < 12:
                continue
            pa = ka[[m.queryIdx for m in good]]
            pb = kb[[m.trainIdx for m in good]]
            va, vb = rays_of(ca, pa), rays_of(cb, pb)
            w = cb.center - ca.center
            aa = np.einsum('ij,ij->i', va, va)
            bb2 = np.einsum('ij,ij->i', va, vb)
            cc = np.einsum('ij,ij->i', vb, vb)
            dd = va @ w
            ee = vb @ w
            den = aa * cc - bb2 * bb2
            ok = np.abs(den) > 1e-9
            den = np.where(ok, den, 1.0)
            s = (cc * dd - bb2 * ee) / den
            t = (bb2 * dd - aa * ee) / den
            P1 = ca.center + s[:, None] * va
            P2 = cb.center + t[:, None] * vb
            m = np.linalg.norm(P1 - P2, axis=1)
            sel = np.logical_and.reduce((s > RNEAR, s < 6.0, t > RNEAR, t < 6.0))
            if sel.any():
                out.append(m[sel])
    return float(np.median(np.concatenate(out))) if out else float('nan')


cls = sys.argv[1] if len(sys.argv) > 1 else 'b7s'
rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
apply_it = 'apply' in sys.argv
frames = U.load_class(cls)
stems = sorted(frames)
print('%s: %d posed frames' % (cls, len(stems)))
if len(stems) < 6:
    raise SystemExit('too few frames to refine anything')

items = []
for stem in stems:
    cam, ip = frames[stem]
    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    kp, de = sift.detectAndCompute(img, None)
    if de is None or len(kp) < 40:
        continue
    items.append([stem, cam, np.array([k.pt for k in kp]), de])
bf = cv2.BFMatcher(cv2.NORM_L2)
print('%d frames carry features' % len(items))

# --- the tracks, matched once and reused every round -------------------------------------------
# THE FIRST RUN PAIRED NEIGHBOURS IN FRAME ORDER WITH NO DISTANCE TEST, and on b7s that is wrong: its
# twelve frames are two clusters forty-five metres apart, so "the next frame in the list" can be the other
# end of the hall. Those pairs match on nothing and their tracks poison the scene. A pair now has to be
# within 3 m as well as within five frames.
pairs = {}
for i in range(len(items)):
    for j in range(i + 1, min(i + WIN, len(items))):
        if float(np.linalg.norm(np.array(items[i][1].center) - np.array(items[j][1].center))) > 3.0:
            continue
        mm = bf.knnMatch(items[i][3], items[j][3], k=2)
        good = [(m.queryIdx, m.trainIdx) for m, nn in mm if m.distance < 0.72 * nn.distance]
        if len(good) >= 12:
            pairs[(i, j)] = good
print('%d matched neighbour pairs' % len(pairs))
parent = {}


def find(a):
    while parent.get(a, a) != a:
        parent[a] = parent.get(parent[a], parent[a])
        a = parent[a]
    return a


def union(a, b):
    parent.setdefault(a, a)
    parent.setdefault(b, b)
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


for (i, j), good in pairs.items():
    for qi, ti in good:
        union((i, qi), (j, ti))
groups = {}
for (i, j), good in pairs.items():
    for qi, ti in good:
        groups.setdefault(find((i, qi)), set()).add((i, qi))
        groups.setdefault(find((j, ti)), set()).add((j, ti))
tracks = [sorted(v) for v in groups.values() if len({a for a, _b in v}) >= MINTRACK]
print('%d tracks seen in %d or more frames' % (len(tracks), MINTRACK))
if len(tracks) < 60:
    raise SystemExit('not enough tracks to resect anything')

C0 = {it[0]: np.array(it[1].center, float) for it in items}
R0 = {it[0]: np.array(it[1].R, float) for it in items}
before = miss_metric(items)
print('median near-field ray miss before: %.4f m' % before)

for rnd in range(rounds):
    P3, OBS = [], []
    for tr in tracks:
        cs, vs, obs = [], [], []
        for fi, ki in tr:
            cam = items[fi][1]
            v = rays_of(cam, items[fi][2][ki:ki + 1])[0]
            cs.append(np.array(cam.center, float))
            vs.append(v)
            obs.append((fi, items[fi][2][ki]))
        X = triangulate(cs, vs)
        if X is None:
            continue
        ang = 0.0
        for a in range(len(vs)):
            for b in range(a + 1, len(vs)):
                ang = max(ang, float(np.arccos(np.clip(vs[a] @ vs[b], -1, 1))))
        if ang < MINANG:
            continue
        bad = False
        for fi, pt in obs:
            cam = items[fi][1]
            x, y, z = cam.project(X.reshape(1, 3))
            if z[0] <= 0.05 or np.hypot(x[0] - pt[0], y[0] - pt[1]) > MAXREPROJ:
                bad = True
                break
            r = float(np.linalg.norm(X - cam.center))
            if r < RNEAR or r > RFAR:
                bad = True
                break
        if bad:
            continue
        P3.append(X)
        OBS.append(obs)
    per = {}
    for X, obs in zip(P3, OBS):
        for fi, pt in obs:
            per.setdefault(fi, [[], []])
            per[fi][0].append(X)
            per[fi][1].append(pt)
    moved, nref, capped = [], 0, 0
    for fi, (Xs, pts) in per.items():
        if len(Xs) < 12:
            continue
        cam = items[fi][1]
        K, dist = kmat(cam)
        # Cam.R here is the WORLD-TO-CAMERA rotation: trackA_geom defines center as -R.T t, and rays_of
        # multiplies by cam.R on the right, which is R^T applied to a camera-space direction. So solvePnP's
        # rvec is Rodrigues(cam.R) directly and its tvec is cam.t. Getting this backwards silently refines
        # a mirrored pose and every camera hits the cap.
        rvec, _ = cv2.Rodrigues(np.asarray(cam.R, float))
        tvec = np.asarray(cam.t, float).reshape(3, 1)
        rv, tv = cv2.solvePnPRefineLM(np.asarray(Xs, np.float64).reshape(-1, 1, 3),
                                      np.asarray(pts, np.float64).reshape(-1, 1, 2),
                                      K, dist.reshape(1, -1), rvec.copy(), tvec.copy())
        Rn, _ = cv2.Rodrigues(rv)
        Cn = (-Rn.T @ tv).ravel()
        dt = float(np.linalg.norm(Cn - C0[items[fi][0]]))
        dr = float(np.arccos(np.clip((np.trace(Rn @ R0[items[fi][0]].T) - 1) / 2.0, -1, 1)))
        if dt > CAP_T or dr > CAP_R or not np.isfinite(dt):
            capped += 1
            continue                              # the cap refuses: that is a move, not a refinement
        items[fi][1] = G.Cam(cam.model, cam.w, cam.h, cam.params, Rn, tv.ravel())
        moved.append(dt)
        nref += 1
    print('round %d: %d points, %d cameras refined, %d refused by the cap, median move %.4f m, worst %.4f'
          % (rnd + 1, len(P3), nref, capped, float(np.median(moved)) if moved else 0.0,
             float(np.max(moved)) if moved else 0.0))

after = miss_metric(items)
print('')
print('median near-field ray miss  before %.4f m   after %.4f m' % (before, after))
if before == before and before > 0:
    print('that is %.0f per cent of it removed' % (100.0 * (1.0 - after / before)))
dt_all = np.array([float(np.linalg.norm(np.array(it[1].center) - C0[it[0]])) for it in items])
print('cameras moved: median %.4f m, 90th %.4f m, worst %.4f m, %d of %d past 0.10 m'
      % (float(np.median(dt_all)), float(np.percentile(dt_all, 90)), float(dt_all.max()),
         int((dt_all > 0.10).sum()), len(dt_all)))
print('the cap was %.2f m and %.1f degrees; a camera that hit it kept its registered pose'
      % (CAP_T, np.rad2deg(CAP_R)))

if apply_it:
    spec = U.CLASSES[cls]
    dst = spec['model'].rstrip('/') + '-refined.json'
    out = {it[0]: {'R': np.asarray(it[1].R).tolist(), 'C': np.asarray(it[1].center).tolist()}
           for it in items}
    json.dump({'class': cls, 'cap_t': CAP_T, 'cap_r_deg': 3.0, 'rounds': rounds,
               'miss_before': before, 'miss_after': after, 'poses': out},
              open(dst, 'w'), indent=1)
    print('')
    print('written to', dst)
