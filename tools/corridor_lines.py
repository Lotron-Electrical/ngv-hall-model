# 2026-09-09: THE CORRIDOR BEHIND THE BRICK WALL, REACHED THROUGH THE OPENINGS FROM THE HALL FLOOR.
#
# The corridor is the part of the goal nothing has ever measured. Its floor 8.34, its ceiling 11.4 and its
# back wall on d -2.09 rest on a plan and on three lamps triangulated inside it, and the only bound on the
# ceiling is that it must be above the highest of those lamps. Every earlier attempt tried to see the room
# THROUGH the openings and failed on signal: under twenty grey levels inside a 1.2 m slot fifteen metres
# away.
#
# THIS DOES NOT TRY TO SEE THE ROOM. It looks for one line in it. Where the corridor's ceiling meets its
# back wall there is a horizontal edge at constant (d, h) running the length of the hall, which is the same
# object the sill and head fits just measured to 15 and 17 mm, and fitting it returns BOTH unknowns at
# once: the depth of the back wall and the height of the ceiling.
#
# AND IT IS GEOMETRICALLY REACHABLE, which is worth checking before any pixels are read. From a lens on the
# hall floor ten metres out, the ray to that junction crosses the wall plane on h 9.78, and the opening now
# runs 8.761 to 11.236. It goes through. The corridor FLOOR does not: it sits below the sill and the sill
# hides it from anything standing lower.
#
# THE POLARITY IS THE OTHER WAY UP FROM THE HEAD, and that is what names the edge. The three lamps measured
# inside that room hang under the ceiling on h 10.374 to 10.990, so they light the ceiling from beneath
# while the back wall below them falls away into shadow: dark below, bright above. A detector told to find
# that cannot find the head, whose masonry is bright below and whose opening is dark above.
#
# EVERY DETECTION MUST ALSO HAVE COME THROUGH AN APERTURE. A ray that reaches the corridor has to cross the
# wall plane inside an opening, between the measured sill and head and between a pair of measured jambs.
# That test uses only geometry measured today and it throws away everything that found a feature on the
# wall's own face.
#   python tools/corridor_lines.py
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
LAMPS = (10.374, 10.908, 10.990)
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.770, 19.983],
        [22.418, 23.631], [26.066, 27.279], [29.816, 31.028], [33.495, 34.706], [37.177, 38.383],
        [40.906, 42.118], [44.526, 45.739]]
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
US = np.arange(3.0, 47.0, 0.3)
# THE INSTRUMENT IS THE ONE THAT ALREADY WORKS, NOT A LOOSER COUSIN OF IT. The first version of this tool
# asked for 10 grey levels over a five-metre ladder; the fit that measured the sill and the head asked for
# 18 over three, and the ladder-span lesson was learned the hard way when a seven-metre ladder let the fan
# sweep the stained-glass ceiling junction and moved a fit four metres. Every knob here is now the one the
# working fit used, so a disagreement between the two is about the ROOM and not about the settings.
HWIN, CONTRAST, THRESH = 40, 18.0, 0.06

# THE CONTROL, and it is not optional. The first run of this tool fitted a line whose four sub-fits
# scattered over 1.7 m in depth, which is a refusal, but a refusal only means something once you know
# whether the machinery or the room is at fault. So the same detector, the same polarity, the same rays
# and the same fit are pointed at a feature measured TODAY to 17 mm: the opening head on d -0.090
# h 11.236, which is also a dark-below bright-above edge and is the strongest one anywhere near this
# ladder. The only thing that changes is the window the ray is allowed to cross the wall plane in, which
# in the corridor run stops at the head and here is opened past it.
# If the control lands on the head, the machinery works and the corridor genuinely has no line the hall
# floor can see. If the control misses the head, nothing this tool says about the corridor counts either.
# THE CONTROL NEEDED A TALLER LADDER THAN THE MEASUREMENT, and finding that out was worth the run. The
# ladder is walked on the BACK WALL plane, two metres behind the face, so a rung and the wall-plane
# crossing of the ray to it are not the same height: from a lens ten metres out the ray to a rung on 12.6
# crosses the face on about 10.3. The first control therefore returned the corridor run's numbers
# unchanged, because not one ray in the fan could reach the head on 11.236 to begin with. A control that
# cannot reach its target is not a control. The ladder is raised here until the fan crosses the face above
# the head, and nothing else about the experiment moves.
# The measurement itself is unaffected: the corridor ceiling junction IS on the back plane, so a rung on
# 11.4 is the feature itself, and the aperture check confirms every camera in the set can see it.
CONTROL = os.environ.get('CONTROL', '') == '1'
# The control searches the WALL plane for the head; the measurement searches the BACK plane for the
# ceiling junction. Same rays, same polarity, same detector, same ladder span, same fit. One surface and
# one target apart, which is the whole point.
SURF = DNORTH if CONTROL else DBACK
TARGD, TARGH = (DNORTH, HEAD) if CONTROL else (DBACK, CEIL)
HS = np.arange(TARGH - 0.9, TARGH + 0.9, 0.005)


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

back = np.array([O + uu * HU + SURF * HD + np.array([0.0, float(v), 0.0]) for uu in US for v in HS])
nh = len(HS)
rows = []
kept = 0
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if ch > 6.0 or cd < 3.0 or cd > 14.6:
        continue
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or float(fwd @ HD) / n > -0.40:
        continue                                     # pointed north; an upward tilt is expected here
    x, y, z = cam.project(back)
    ok = np.logical_and.reduce((z > 0.3, x > 30, x < cam.w - 30, y > 30, y < cam.h - 30))
    if ok.sum() < 200:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    kept += 1
    for ui in range(len(US)):
        uu = float(US[ui])
        if not any(lo + 0.06 < uu < hi - 0.06 for lo, hi in OPEN):
            continue                                 # the corridor is only visible through an aperture
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
            step = float(v[i + 1:i + 1 + HWIN].mean() - v[i - HWIN:i].mean())   # dark below, bright above
            if step > best:
                best, besti = step, i
        if besti is None or best < CONTRAST:
            continue
        k = a + besti
        vv = rays_of(cam, [(float(x[sl][k]), float(y[sl][k]))])[0]
        vd, vh = float(vv @ HD), float(vv[1])
        # THE APERTURE TEST. Where does this ray cross the wall plane, and is that inside an opening?
        lam = (DNORTH - cd) / (vd if abs(vd) > 1e-9 else 1e-9)
        if lam <= 0:
            continue
        hx = ch + vh * lam
        ux = cu + float(vv @ HU) * lam
        if not (SILL < hx < (HEAD + 0.9 if CONTROL else HEAD)):
            continue
        if not any(lo < ux < hi for lo, hi in OPEN):
            continue
        rows.append((cd, ch, vd, vh, uu, float(best), hx))

print('CORRIDOR CEILING JUNCTION: %d frames aimed north, %d detections that came through an aperture'
      % (kept, len(rows)))
if len(rows) < 40:
    raise SystemExit('nothing got through the openings to that line; refused')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
UU = np.array([r[4] for r in rows])
HX = np.array([r[6] for r in rows])
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'corridor-ceiling-rays.npy'), np.column_stack([R, UU, HX]))
BASE = float(R[:, 0].max() - R[:, 0].min())
print('cameras stand between d %.2f and %.2f, a %.2f m baseline; the rays cross the wall plane between'
      % (R[:, 0].min(), R[:, 0].max(), BASE))
print('h %.2f and %.2f' % (HX.min(), HX.max()))
# THE BASELINE IS THE WHOLE STORY AND IT IS PRINTED BEFORE THE FIT, so it cannot be read as an excuse
# afterwards. A line at constant (d, h) is separated from the rays only by cameras at different distances
# from it. The control keeps the whole hall floor because its target sits IN the aperture. The corridor
# target sits two metres behind the aperture, so a camera can only see the whole height ladder through the
# slot from far back, and the set collapses onto the far wall. The opening is a collimator.



def perp(R, dv, hv):
    num = R[:, 3] * (dv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


rng = np.random.default_rng(5)
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
    if not (TARGD - 1.6 < c[0] < TARGD + 1.6 and TARGH - 0.9 < c[1] < TARGH + 0.9):
        continue
    n = int((perp(R, c[0], c[1]) < THRESH).sum())
    if n > bestn:
        bestn, best = n, c
if best is None:
    raise SystemExit('no line found behind that wall')
inl = perp(R, best[0], best[1]) < THRESH
ref = fit(R[inl])
inl = perp(R, ref[0], ref[1]) < THRESH
ref = fit(R[inl])
d = perp(R[inl], ref[0], ref[1])
print('')
print('the junction fits a line on d %.3f h %.3f' % (ref[0], ref[1]))
print('   %d of %d rays (%.0f per cent) inside %.0f mm, median %.0f mm'
      % (int(inl.sum()), len(R), 100.0 * inl.mean(), THRESH * 1000, 1000 * float(np.median(d))))
if CONTROL:
    print('   CONTROL: the head was measured today on d %.3f h %.3f, so this control is out by %+.3f m'
          % (DNORTH, HEAD, ref[1] - HEAD))
    print('   and %+.3f m in depth' % (ref[0] - DNORTH))
else:
    print('   the sim draws the back wall on d %.3f and the ceiling on h %.3f, so this is %+.3f and %+.3f'
          % (DBACK, CEIL, ref[0] - DBACK, ref[1] - CEIL))
    print('   that makes the corridor %.3f m deep from the face and %.3f m from its floor to its ceiling'
          % (DNORTH - ref[0], ref[1] - FLOOR))

Q = R[inl]
uin = UU[inl]
umid = float(np.median(uin))
for label, sel in (('west half', uin <= umid), ('east half', uin > umid)):
    if sel.sum() < 20:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    print('   %-12s %4d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
mid = float(np.median(Q[:, 0]))
for label, sel in (('nearer half', Q[:, 0] <= mid), ('further half', Q[:, 0] > mid)):
    if sel.sum() < 20:
        print('   %s: only %d inliers' % (label, int(sel.sum())))
        continue
    f2 = fit(Q[sel])
    print('   %-12s %4d inliers -> d %.3f h %.3f' % (label, int(sel.sum()), f2[0], f2[1]))
nop = sum(1 for lo, hi in OPEN if int(np.logical_and(uin > lo, uin < hi).sum()) >= 4)
print('   %d of the 12 openings carry at least 4 inliers' % nop)

# THE VERDICT, WRITTEN BY THE SPLITS AND NOT BY THE INLIER COUNT. A high inlier count on a degenerate
# problem is worthless: when the baseline cannot separate depth from height the solution slides along the
# median ray, every subset picks a different point on that slide, and each one fits its own rays beautifully.
# So the bar is the SPREAD of the four sub-fits. The sill and head fits, on the same rays and the same code,
# held their four sub-fits inside 0.07 m of height. Anything past 0.30 m here is not one line.
# AND THE BAR GOES ON THE ALONG-WALL SPLIT, NOT ON ALL FOUR SUB-FITS. Written the other way round it
# failed the control too, and it was wrong to do so: the DISTANCE split is a quality gradient as well as a
# conditioning test, because from fourteen metres an opening is a few dozen pixels wide, so the far half
# disagreeing can be noise rather than a second feature. Splitting along the wall carries no such gradient.
# That distinction was already established on the sill and head fits and it is kept here.
SPREAD = 0.30
subs = [fit(Q[sel]) for sel in (uin <= umid, uin > umid) if int(sel.sum()) >= 20]
if len(subs) == 2:
    sh = abs(float(subs[0][1] - subs[1][1]))
    sd = abs(float(subs[0][0] - subs[1][0]))
    print('   the two halves OF THE WALL differ by %.3f m in height and %.3f m in depth, bar %.2f m'
          % (sh, sd, SPREAD))
    if sh > SPREAD:
        print('   REFUSED. This is not one line. The %.2f m camera baseline cannot separate the two'
              % BASE)
        print('   unknowns, so the answer slides along the median ray and each half stops elsewhere on it.')
    else:
        print('   the two halves agree, so one line explains the whole wall')
dsub = [fit(Q[sel]) for sel in (Q[:, 0] <= mid, Q[:, 0] > mid) if int(sel.sum()) >= 20]
if len(dsub) == 2:
    print('   (the distance split, reported as a diagnostic and not as the bar, differs by %.3f m)'
          % abs(float(dsub[0][1] - dsub[1][1])))

# THE RANGE, which is what says the feature is BEHIND the wall rather than on it.
s = ((ref[0] - Q[:, 0]) * Q[:, 2] + (ref[1] - Q[:, 1]) * Q[:, 3]) / (Q[:, 2] ** 2 + Q[:, 3] ** 2)
sface = (DNORTH - Q[:, 0]) / np.where(np.abs(Q[:, 2]) < 1e-9, 1e-9, Q[:, 2])
print('   range to the edge %.2f m against %.2f m to the wall face, %+.2f m along the ray, and %.0f per'
      % (float(np.median(s)), float(np.median(sface)), float(np.median(s - sface)),
         100.0 * float((s - sface > 0).mean())))
print('   cent of the inliers put it beyond the face, which is what being inside that room means')
print('   the highest lamp triangulated in there hangs on h %.3f, so a ceiling on %.3f clears it by %.3f m'
      % (LAMPS[2], ref[1], ref[1] - LAMPS[2]))
