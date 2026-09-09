# 2026-09-09: measure the corridor from a lens standing IN the opening, which is the one place the
# collimation argument does not apply.
#
# The hall-floor route to that room closed this evening with a number. A line two metres behind the wall
# can only be separated from the rays by cameras at different distances from it, and seeing the whole
# height ladder through a 1.2 m slot forces the lens far back, so the usable set collapsed from an 8.64 m
# baseline to 1.59 m and the two halves of the wall disagreed by 573 mm. The slot collimates.
#
# BUT A LENS INSIDE THE SLOT IS NOT LOOKING THROUGH IT. b1 was posed standing in north opening 5, and it
# is the best-posed clip in the archive: median near-field ray miss 0.061 m, against 0.173 for the worst
# clip anything has ever been asked to carry. From in there the corridor back wall is about two metres
# away instead of sixteen, and the aperture is behind the lens rather than in front of it.
#
# THE BASELINE COMES FROM THE OPERATOR'S OWN HEIGHT, WHICH IS THE POINT. Those frames span h 9.17 to 9.80,
# and the fit does not care whether the cameras differ in depth or in height: a ray meets a line at
# constant (d, h) spanning u when vh*(d* - cd) - vd*(h* - ch) = 0, and both cd and ch appear in it. Two
# thirds of a metre of vertical baseline against a wall two metres away is a third of a radian of
# parallax, which is far more than the hall floor ever had on that room.
#
# THE CONTROL IS THE APERTURE THE LENS IS STANDING IN. The sill and the head of these openings were
# measured today from the hall floor to 15 and 17 mm, on h 8.761 and 11.236. The same detector, rays and
# fit are pointed at them from inside first. If it cannot recover an edge a metre from the lens that
# another instrument has already pinned, nothing it says about the room behind counts.
#   TARGET=head python tools/corridor_from_opening.py     TARGET=ceil python tools/corridor_from_opening.py
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH, SILL, HEAD = -0.090, 8.761, 11.236
DBACK, CEIL, FLOOR = -2.090, 11.4, 8.34
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.854, 12.067],
        [15.374, 16.587], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'

# THE TWO TARGETS AND THEIR POLARITIES, and the parity is what names each one.
#   head  the top of the aperture seen from inside it: the lit reveal soffit is above, the way out into
#         the bright hall is below, so it is a bright-above dark-below step, and it is the CONTROL.
#   ceil  where the corridor ceiling meets its back wall: the lamps in that room hang under the ceiling
#         and light it from beneath while the wall below falls into shadow, so bright above, dark below.
# NOT ONE LENS IN THE ARCHIVE LOOKS INTO THAT ROOM, and this is where that was found out.
# 317 frames sit at opening height within two metres of the wall plane, 340 of them across b1 in opening
# 5, b5 in opening 6 and b4 in opening 11, all within half a metre of the face. Every single one points
# back OUT into the hall: the most inward-facing frame in the whole set still has its axis 0.38 of the way
# toward the hall, and none is even parallel to the wall (tools/opening_facing.py). The operator stood in
# the apertures and filmed the room he had come from. So the corridor cannot be measured from inside
# either, and that is now a counted fact rather than an impression.
# WHAT THOSE FRAMES CAN DO is measure the aperture they are standing in, from a metre away instead of
# fifteen, which is an independent check on the sill and head the hall floor fitted today. From inside,
# the parity of each edge is REVERSED: the head has the bright hall below it and the dark soffit above,
# where from the floor it had dark opening below and lit masonry above. FACING and POL carry that.
TARGET = os.environ.get('TARGET', 'head')
FACING = os.environ.get('FACING', 'in')          # 'in' looks into the corridor, 'out' back into the hall
POL = os.environ.get('POL', 'up')                # 'up' = bright above dark below, 'down' = the reverse
FSIGN = -1.0 if FACING == 'in' else 1.0
PSIGN = 1.0 if POL == 'up' else -1.0
SURF, TARGD, TARGH = ((DNORTH, DNORTH, HEAD) if TARGET == 'head' else (DBACK, DBACK, CEIL))
HS = np.arange(TARGH - 1.2, TARGH + 1.2, 0.004)
HWIN, CONTRAST, THRESH = 30, 14.0, 0.05
CLASSES = os.environ.get('CLASSES', 'b1 b1p b3 b3p b4 b5 b5p').split()


def rays_of(cam, pix):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pix, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


frames = {}
for cls in CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass
print('%d frames loaded from %s' % (len(frames), ', '.join(CLASSES)))

rows = []
kept = 0
cams = []
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    # THE ONLY CAMERAS THAT COUNT ARE THE ONES IN THE APERTURE. Standing in an opening means being at
    # gallery height, within a metre of the wall plane, and between a pair of measured jambs.
    if not (SILL - 0.4 < ch < HEAD + 0.4):
        continue
    if abs(cd - DNORTH) > 1.2:
        continue
    if not any(lo - 0.2 < cu < hi + 0.2 for lo, hi in OPEN):
        continue
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or FSIGN * (float(fwd @ HD) / n) < 0.30:
        continue                          # pointing the way this run asks for, in or out
    cams.append((stem, cu, cd, ch))
    us = np.arange(max(3.0, cu - 1.4), min(47.0, cu + 1.4), 0.01)
    grid = np.array([O + uu * HU + SURF * HD + np.array([0.0, float(hv), 0.0])
                     for uu in us for hv in HS])
    nh = len(HS)
    x, y, z = cam.project(grid)
    ok = np.logical_and.reduce((z > 0.15, x > 20, x < cam.w - 20, y > 20, y < cam.h - 20))
    if ok.sum() < 150:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (5, 5), 0)
    kept += 1
    for ui in range(len(us)):
        sl = slice(ui * nh, (ui + 1) * nh)
        m = ok[sl]
        idx = np.where(m)[0]
        if idx.size < 3 * HWIN or not np.all(m[idx.min():idx.max() + 1]):
            continue
        a, b = int(idx.min()), int(idx.max())
        xi = np.clip(np.round(x[sl][a:b + 1]), 0, cam.w - 1).astype(np.int32)
        yi = np.clip(np.round(y[sl][a:b + 1]), 0, cam.h - 1).astype(np.int32)
        v = grey[yi, xi].astype(np.float32)
        best, besti = -1e9, None
        for i in range(HWIN, len(v) - HWIN):
            step = PSIGN * float(v[i + 1:i + 1 + HWIN].mean() - v[i - HWIN:i].mean())
            if step > best:
                best, besti = step, i
        if besti is None or best < CONTRAST:
            continue
        k = a + besti
        vv = rays_of(cam, [(float(x[sl][k]), float(y[sl][k]))])[0]
        rows.append((cd, ch, float(vv @ HD), float(vv[1]), float(us[ui])))

print('%s, lenses facing %s: %d stand in an opening, %d used, %d detections'
      % (TARGET.upper(), FACING, len(cams), kept, len(rows)))
if cams:
    cu = np.array([c[1] for c in cams])
    cd = np.array([c[2] for c in cams])
    ch = np.array([c[3] for c in cams])
    print('   they span u %.2f to %.2f, d %.3f to %.3f, h %.3f to %.3f'
          % (cu.min(), cu.max(), cd.min(), cd.max(), ch.min(), ch.max()))
    print('   the baseline that conditions this fit is %.3f m of height and %.3f m of depth'
          % (ch.max() - ch.min(), cd.max() - cd.min()))
if len(rows) < 60:
    raise SystemExit('too few detections from inside the aperture; refused')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
UU = np.array([r[4] for r in rows])
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'inside-%s-rays.npy' % TARGET), np.column_stack([R, UU]))


def perp(R, dv, hv):
    num = R[:, 3] * (dv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


rng = np.random.default_rng(23)
ii = rng.integers(0, len(R), 40000)
jj = rng.integers(0, len(R), 40000)
bestn, best = -1, None
for a, b in zip(ii, jj):
    if a == b:
        continue
    S = R[[a, b]]
    A = np.stack([S[:, 3], -S[:, 2]], 1)
    y = S[:, 3] * S[:, 0] - S[:, 2] * S[:, 1]
    if abs(np.linalg.det(A)) < 1e-9:
        continue
    c = np.linalg.solve(A, y)
    if not (TARGD - 1.6 < c[0] < TARGD + 1.6 and TARGH - 1.2 < c[1] < TARGH + 1.2):
        continue
    n = int((perp(R, c[0], c[1]) < THRESH).sum())
    if n > bestn:
        bestn, best = n, c
if best is None:
    raise SystemExit('no line found from inside')
inl = perp(R, best[0], best[1]) < THRESH
ref = fit(R[inl])
inl = perp(R, ref[0], ref[1]) < THRESH
ref = fit(R[inl])
res = perp(R[inl], ref[0], ref[1])
print('')
print('the %s fits a line on d %.3f h %.3f' % (TARGET, ref[0], ref[1]))
print('   %d of %d rays (%.0f per cent) inside %.0f mm, median %.0f mm'
      % (int(inl.sum()), len(R), 100.0 * inl.mean(), THRESH * 1000, 1000 * float(np.median(res))))
if TARGET == 'head':
    print('   CONTROL: the head was measured from the hall floor on d %.3f h %.3f, so this is %+.3f m'
          % (DNORTH, HEAD, ref[1] - HEAD))
    print('   in height and %+.3f m in depth' % (ref[0] - DNORTH))
else:
    print('   the sim draws the back wall on d %.3f and the ceiling on h %.3f, so this is %+.3f and %+.3f'
          % (DBACK, CEIL, ref[0] - DBACK, ref[1] - CEIL))
    print('   the room would then be %.3f m deep from the wall face and %.3f m floor to ceiling'
          % (DNORTH - ref[0], ref[1] - FLOOR))

Q = R[inl]
uin = UU[inl]
hin = Q[:, 1]
hmid = float(np.median(hin))
for label, sel in (('lower lenses', hin <= hmid), ('higher lenses', hin > hmid)):
    if sel.sum() < 15:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    print('   %-14s %4d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
umid = float(np.median(uin))
subs = []
for label, sel in (('west of centre', uin <= umid), ('east of centre', uin > umid)):
    if sel.sum() < 15:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    subs.append(f2)
    print('   %-14s %4d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
if len(subs) == 2:
    sh = abs(float(subs[0][1] - subs[1][1]))
    print('   the two halves differ by %.3f m in height, bar 0.10 m' % sh)
    print('   %s' % ('REFUSED, this is not one line' if sh > 0.10 else 'they agree, so it is one line'))
