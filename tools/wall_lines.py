# 2026-09-09: THE SAME INSTRUMENT TURNED SIDEWAYS ONTO THE NORTH WALL, for the sill and the head.
#
# The far-edge fit has now earned its keep: it measured both balcony fronts to 10 and 15 mm, survived a
# split of the cameras into near and far halves, and carries a range test that says the feature was beyond
# the plane. Everything in it is general except the axis it was written along.
#
# THE BALCONY VERSION FITS A LINE AT CONSTANT (u, h) SPANNING d, because a balcony front runs across the
# hall. The north wall's openings run ALONG the hall, so their sill and head are lines at constant (d, h)
# spanning u, and the algebra is the same equation with two columns swapped: a ray meets such a line when
# vh*(d* - cd) - vd*(h* - ch) = 0, linear in both unknowns. The conditioning now comes from cameras at
# different DISTANCES FROM THE WALL, and the hall-floor clips span d 0.8 to 14.6, a fourteen-metre baseline
# where the balcony work had one metre.
#
# TWO EDGES, TWO POLARITIES, AND THAT IS WHAT NAMES THEM. Under a sill the wall is lit masonry and above it
# is the dark opening, so the sill is a BRIGHT-BELOW, DARK-ABOVE step. Over a head the opening is dark and
# the masonry above it is lit, so the head is the opposite. Each detector can only find its own edge, which
# is the discipline that identified the balcony front and it is kept here.
#
# NOTHING DRAWN IS SEARCHED FOR. The ladder is a metre and a half either side of each candidate, the u
# stations run the whole wall including the solid piers between openings, and where the inliers actually
# land in u is reported against the drawn openings rather than assumed.
#   EDGE=sill python tools/wall_lines.py
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH, SILL, HEAD = -0.090, 8.99, 11.35
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
EDGE = os.environ.get('EDGE', 'sill')
DRAWN = SILL if EDGE == 'sill' else HEAD
HS = np.arange(DRAWN - 1.5, DRAWN + 1.5, 0.005)
US = np.arange(3.0, 47.0, 0.4)
HWIN, CONTRAST, THRESH = 40, 18.0, 0.06
sift = None


def rays_of(cam, pix):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pix, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


frames = {}
for cls in ('walk', 'night', 'day4k'):
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass

wall = np.array([O + uu * HU + DNORTH * HD + np.array([0.0, float(v), 0.0]) for uu in US for v in HS])
nh = len(HS)
rows = []
kept = 0
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if ch > 6.0 or cd < 1.2 or cd > float(os.environ.get('DMAX', '14.6')):
        continue
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or float(fwd @ HD) / n > -0.45 or abs(float(fwd[1])) > 0.55:
        continue                                    # pointed north, and not straight up
    x, y, z = cam.project(wall)
    ok = np.logical_and.reduce((z > 0.3, x > 30, x < cam.w - 30, y > 30, y < cam.h - 30))
    if ok.sum() < 300:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    kept += 1
    for ui in range(len(US)):
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
            below = float(v[i - HWIN:i].mean())
            above = float(v[i + 1:i + 1 + HWIN].mean())
            step = (below - above) if EDGE == 'sill' else (above - below)
            if step > best:
                best, besti = step, i
        if besti is None or best < CONTRAST:
            continue
        k = a + besti
        vv = rays_of(cam, [(float(x[sl][k]), float(y[sl][k]))])[0]
        rows.append((cd, ch, float(vv @ HD), float(vv[1]), float(US[ui]), stem))

print('%s: %d hall-floor frames aimed at the north wall, %d detections'
      % (EDGE.upper(), kept, len(rows)))
if len(rows) < 60:
    raise SystemExit('too few detections to fit anything')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
UU = np.array([r[4] for r in rows])
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'wall-%s-rays.npy' % EDGE), np.column_stack([R, UU]))
print('cameras stand between d %.2f and %.2f, a %.2f m baseline across the hall'
      % (R[:, 0].min(), R[:, 0].max(), R[:, 0].max() - R[:, 0].min()))


def perp(R, dv, hv):
    num = R[:, 3] * (dv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


rng = np.random.default_rng(3)
ii = rng.integers(0, len(R), 30000)
jj = rng.integers(0, len(R), 30000)
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
    if not (-2.5 < c[0] < 1.5 and DRAWN - 1.5 < c[1] < DRAWN + 1.5):
        continue
    n = int((perp(R, c[0], c[1]) < THRESH).sum())
    if n > bestn:
        bestn, best = n, c
if best is None:
    raise SystemExit('no line found')
inl = perp(R, best[0], best[1]) < THRESH
ref = fit(R[inl])
inl = perp(R, ref[0], ref[1]) < THRESH
ref = fit(R[inl])
d = perp(R[inl], ref[0], ref[1])
print('')
print('the %s fits a line on d %.3f h %.3f' % (EDGE, ref[0], ref[1]))
print('   %d of %d rays (%.0f per cent) inside %.0f mm, median %.0f mm'
      % (int(inl.sum()), len(R), 100.0 * inl.mean(), THRESH * 1000, 1000 * float(np.median(d))))
print('   the sim draws the %s on h %.3f and the wall face on d %.3f, so this is %+.3f m and %+.3f m'
      % (EDGE, DRAWN, DNORTH, ref[1] - DRAWN, ref[0] - DNORTH))

Q = R[inl]
uin_all = UU[inl]
mid = float(np.median(Q[:, 0]))
# TWO SPLITS, AND THEY ASK DIFFERENT QUESTIONS. Splitting by DISTANCE tests conditioning, but it is also a
# quality gradient: from 14 m away an opening is a few dozen pixels wide, so a disagreement there may be
# noise rather than a second feature. Splitting by WHERE ALONG THE WALL the detections came from has no
# such gradient, so it is the fair test of whether one line explains the whole thing.
umid = float(np.median(uin_all))
for label, sel in (('west half of wall', uin_all <= umid), ('east half of wall', uin_all > umid)):
    if sel.sum() < 30:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    print('   %-18s %5d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
for label, sel in (('nearer half', Q[:, 0] <= mid), ('further half', Q[:, 0] > mid)):
    if sel.sum() < 30:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    print('   %-13s %5d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))

# WHERE THE INLIERS LAND ALONG THE WALL, which is the test that says the line is the openings' own edge
# and not something that runs the whole face. A sill exists only where there is an opening.
uin = UU[inl]
inop = np.zeros(len(uin), bool)
for lo, hi in OPEN:
    inop |= np.logical_and(uin > lo - 0.3, uin < hi + 0.3)
cover = sum(hi - lo + 0.6 for lo, hi in OPEN) / (US.max() - US.min())
print('   %.0f per cent of the inliers sit inside a drawn opening, which covers %.0f per cent of the wall'
      % (100.0 * float(inop.mean()), 100.0 * cover))
print('   %d of the 12 openings carry at least 5 inliers'
      % sum(1 for lo, hi in OPEN if int(np.logical_and(uin > lo - 0.3, uin < hi + 0.3).sum()) >= 5))
s = ((ref[0] - Q[:, 0]) * Q[:, 2] + (ref[1] - Q[:, 1]) * Q[:, 3]) / (Q[:, 2] ** 2 + Q[:, 3] ** 2)
sface = (DNORTH - Q[:, 0]) / np.where(np.abs(Q[:, 2]) < 1e-9, 1e-9, Q[:, 2])
print('   range to the edge %.2f m against %.2f m to the drawn wall face, %+.2f m along the ray'
      % (float(np.median(s)), float(np.median(sface)), float(np.median(s - sface))))
