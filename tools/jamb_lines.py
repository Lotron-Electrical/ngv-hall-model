# 2026-09-09: THE INSTRUMENT TURNED THE THIRD WAY, ONTO THE JAMBS, which are the last thing about these
# walls that has never been checked against a photograph.
#
# The sill and the head are measured. The wall face is measured, twice, from two edges of opposite
# polarity. What is still purely a plan is WHERE ALONG THE WALL the twelve openings are: twenty-four
# numbers in the OPEN table that every tool in this repo has used as truth, including the aperture test
# that decided the corridor an hour ago. If they are wrong, a lot of today's work was standing on them.
#
# A JAMB IS THE SAME TWO-UNKNOWN LINE WITH ITS THIRD PAIR OF COLUMNS. A balcony front is a line at constant
# (u, h) spanning d; a sill is a line at constant (d, h) spanning u; a jamb is a VERTICAL line at constant
# (u, d) spanning h, and a ray meets one when vd*(u* - cu) - vu*(d* - cd) = 0. Identical algebra, identical
# fit, identical metric residual. The conditioning is the best of the three: it comes from cameras standing
# at different points ALONG the hall, and the hall floor gives forty metres of that.
#
# NOTHING DRAWN IS SEARCHED FOR, WHICH MATTERS MORE HERE THAN ANYWHERE. The drawn jambs are exactly what is
# on trial, so a window around them would decide the verdict in advance. Instead every step above the
# contrast bar anywhere along the wall becomes a ray, and the fit is peeled: find the strongest line, take
# its rays out, find the next, and keep going until no line has enough support left. What comes out is a
# LIST, and only then is that list laid against the drawn one.
#
# PARITY NAMES WHICH SIDE OF THE OPENING IT IS, and it is a real control rather than a label. Walking west
# to east, the west jamb of an opening goes from lit masonry into a dark opening, and the east jamb goes
# back the other way. Two runs of the same code with the sign flipped must therefore return two interleaved
# sets, and the gap between each pair must come out near the same width twelve times over. A single fit
# cannot fake that.
#   python tools/jamb_lines.py          EDGE=east python tools/jamb_lines.py
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
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
EDGE = os.environ.get('EDGE', 'west')            # which side of an opening this run is allowed to find
# The ladder runs ACROSS the wall now, and the rungs are heights well inside the openings: clear of the
# sill by half a metre and clear of the head by more, so the fan cannot reach either of the edges already
# measured and mistake one for a jamb.
US = np.arange(3.0, 47.0, 0.008)
HS = (9.40, 9.80, 10.20, 10.60)
# HWIN is settable so this number can face the window-invariance test, which caught a gradient
# masquerading as an edge on the balcony face (2026-09-09). A real edge is a step and the position
# of a step does not depend on how many samples are averaged either side of it; a gradient's
# apparent peak walks with the window. Every shipped number measured by a step detector owes this
# test, including the ones already in the model.
HWIN = int(os.environ.get('HWIN', '40'))
# ANCHORD FIXES THE DEPTH AND SOLVES ONLY FOR THE STATION, and it is here because the sill was caught
# sliding this evening. A two-unknown fit whose rays cannot separate its two unknowns does not fail
# loudly; it returns a confident number somewhere along a line, and which point it stops on depends on
# the averaging window. The sill did exactly that, three windows landing on one straight line in the
# (d, h) plane to within a millimetre.
# THE JAMBS ARE THE SAME FIT AND THEY MOVED TEN NUMBERS IN THE SHIPPED MODEL. All nine of them came back
# on d -0.203 to -0.216 while the wall face is measured on -0.090, so every one sits 0.117 m behind the
# plane it should be on. If that depth offset is the slide rather than a reveal, it drags the STATION with
# it, and the station is what the openings were moved on.
# So the depth is fixed to the independently measured face and only u is solved. For a vertical line at
# known d the ray equation vd*(u* - cu) - vu*(d* - cd) = 0 gives u* directly, one unknown per ray, and
# there is nothing left to slide.
ANCHORD = os.environ.get('ANCHORD', '')
CONTRAST = float(os.environ.get('CONTRAST', '18.0'))
THRESH = 0.05
# Support and reach are knobs because coverage, not precision, is what limits this. The first pass found
# only the middle four openings, and a line nobody can see is not a line that is wrong.
MINSUP = int(os.environ.get('MINSUP', '40'))
DMAX = float(os.environ.get('DMAX', '14.6'))
# A JAMB OF THIS WALL HAS TO BE ON THIS WALL, and the peel finds that out for itself rather than being
# told. Relaxing the support bar pulled in three extra lines whose own fitted DEPTH placed them at
# d +0.217, -0.567 and +1.020, up to a metre out in the hall, while every real one landed within 7 mm of
# its neighbours. So depth is the discriminator, and it is not a fit to the plan: the wall face was
# measured independently today from the sill and the head, both times on -0.090. The gate is generous
# enough to admit a reveal a quarter of a metre deep and still throws every one of those three out.
DGATE = float(os.environ.get('DGATE', '0.30'))


def rays_of(cam, pix):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pix, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


frames = {}
# THE CLASSES ARE SETTABLE BECAUSE THAT IS THE TEST FOR WHAT THIS DETECTOR IS FINDING. Every jamb line
# comes back 0.117 m behind the measured wall face, and two explanations fit equally well from where the
# cameras stood: a real rebate in the masonry, or the depth to which light entering from above stops
# reaching the reveal returns. Both parities agreeing to 2 mm rules out a sideways lighting effect but not
# an overhead one, because light from above shadows both returns at the same depth.
# A REBATE IS GEOMETRY AND A SHADOW IS LIGHT. Geometry reads the same by day and by night; a shadow line
# does not, because after dark this hall is lit by uplights and wall washers from below and the sides
# rather than through the stained glass overhead. So fit the same jambs on the day walk alone and on the
# night walk alone. Same depth, it is stone. Different depth, it is a shadow and no rebate should ever be
# drawn on it.
CLASSES = os.environ.get('CLASSES', 'walk night day4k').split()
for cls in CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass

wall = np.array([O + uu * HU + DNORTH * HD + np.array([0.0, float(hv), 0.0])
                 for hv in HS for uu in US])
nu = len(US)
rows = []
kept = 0
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if ch > 6.0 or cd < 1.2 or cd > DMAX:
        continue
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or float(fwd @ HD) / n > -0.45 or abs(float(fwd[1])) > 0.55:
        continue
    x, y, z = cam.project(wall)
    ok = np.logical_and.reduce((z > 0.3, x > 30, x < cam.w - 30, y > 30, y < cam.h - 30))
    if ok.sum() < 300:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    kept += 1
    for hi in range(len(HS)):
        sl = slice(hi * nu, (hi + 1) * nu)
        m = ok[sl]
        idx = np.where(m)[0]
        if idx.size < 4 * HWIN:
            continue
        a, b = int(idx.min()), int(idx.max())
        if not np.all(m[a:b + 1]):
            continue
        xi = np.clip(np.round(x[sl][a:b + 1]), 0, cam.w - 1).astype(np.int32)
        yi = np.clip(np.round(y[sl][a:b + 1]), 0, cam.h - 1).astype(np.int32)
        v = grey[yi, xi].astype(np.float32)
        if len(v) < 3 * HWIN:
            continue
        # THE STEP, EVERYWHERE ALONG THE WALL, NOT JUST AT ITS BEST POINT. Taking one winner per column is
        # what a single-feature detector does; there are twenty-four features here, so every local maximum
        # above the bar is kept and the fit is left to sort them out.
        c = np.cumsum(np.concatenate([[0.0], v]))
        i0 = np.arange(HWIN, len(v) - HWIN)
        before = (c[i0] - c[i0 - HWIN]) / HWIN
        after = (c[i0 + HWIN + 1] - c[i0 + 1]) / HWIN
        step = (before - after) if EDGE == 'west' else (after - before)
        cand = np.where(step > CONTRAST)[0]
        if cand.size == 0:
            continue
        peaks = []
        order = cand[np.argsort(-step[cand])]
        taken = np.zeros(len(step), bool)
        for j in order:
            if taken[j]:
                continue
            peaks.append(j)
            taken[max(0, j - HWIN):j + HWIN] = True
            if len(peaks) >= 30:
                break
        for j in peaks:
            k = a + i0[j]
            vv = rays_of(cam, [(float(x[sl][k]), float(y[sl][k]))])[0]
            rows.append((cu, cd, float(vv @ HU), float(vv @ HD), float(US[k])))

print('%s JAMBS: %d hall-floor frames on the north wall, %d steps above %.0f grey levels'
      % (EDGE.upper(), kept, len(rows), CONTRAST))
if len(rows) < 200:
    raise SystemExit('too few steps to peel anything out')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
SEEN = np.array([r[4] for r in rows])
os.makedirs(OUT, exist_ok=True)
np.save(os.path.join(OUT, 'jamb-%s-rays.npy' % EDGE), np.column_stack([R, SEEN]))
print('cameras stand between u %.2f and %.2f, a %.2f m baseline along the hall'
      % (R[:, 0].min(), R[:, 0].max(), R[:, 0].max() - R[:, 0].min()))


def perp(R, uval, dval):
    """metres, not the raw form: the numerator is the distance times sqrt(vu^2 + vd^2)"""
    num = R[:, 3] * (uval - R[:, 0]) - R[:, 2] * (dval - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


# THE PEEL. Strongest line first, its rays removed, then the next, until nothing has support left. No
# opening is looked for; the count of what comes out is itself a result.
live = np.ones(len(R), bool)
found = []
rng = np.random.default_rng(17)
for _round in range(40):
    idx = np.where(live)[0]
    if idx.size < MINSUP:
        break
    S = R[idx]
    ii = rng.integers(0, len(S), 40000)
    jj = rng.integers(0, len(S), 40000)
    bestn, best = -1, None
    for a, b in zip(ii, jj):
        if a == b:
            continue
        T = S[[a, b]]
        A = np.stack([T[:, 3], -T[:, 2]], 1)
        y = T[:, 3] * T[:, 0] - T[:, 2] * T[:, 1]
        if abs(np.linalg.det(A)) < 1e-9:
            continue
        c = np.linalg.solve(A, y)
        if not (2.0 < c[0] < 48.0 and -1.2 < c[1] < 1.0):
            continue
        n = int((perp(S, c[0], c[1]) < THRESH).sum())
        if n > bestn:
            bestn, best = n, c
    if best is None or bestn < MINSUP:
        break
    sel = perp(S, best[0], best[1]) < THRESH
    ref = fit(S[sel])
    sel = perp(S, ref[0], ref[1]) < THRESH
    if int(sel.sum()) < MINSUP:
        live[idx[perp(S, best[0], best[1]) < THRESH]] = False
        continue
    ref = fit(S[sel])
    if ANCHORD:
        dfix = float(ANCHORD)
        Sin = S[sel]
        uper = Sin[:, 0] + (Sin[:, 2] / np.where(np.abs(Sin[:, 3]) < 1e-9, 1e-9, Sin[:, 3]))             * (dfix - Sin[:, 1])
        ref = np.array([float(np.median(uper)), dfix])
        sel = perp(S, ref[0], ref[1]) < THRESH
        if int(sel.sum()) < MINSUP // 2:
            live[idx[sel]] = False
            continue
    res = perp(S[sel], ref[0], ref[1])
    if abs(float(ref[1]) - DNORTH) <= DGATE:
        # THE SPLIT THIS GEOMETRY ACTUALLY DEMANDS, and it is not the one used on the horizontal edges.
        # An opening is recessed, so a jamb is TWO parallel edges: the one on the face and the one at the
        # back of the reveal. From a camera west of the opening the west jamb shows its face edge; from
        # one east of it the same jamb shows its reveal edge instead, because the face edge has swung out
        # of sight behind the pier. A single fit over cameras on both sides therefore averages two real
        # lines and calls the average a measurement. Splitting the inliers by WHICH SIDE the camera stood
        # on is the only test that can tell those apart, and the answer is also the reveal depth.
        Sin = S[sel]
        west_of = Sin[:, 0] < float(ref[0])
        parts = []
        for lab, m2 in (('cams W', west_of), ('cams E', ~west_of)):
            if int(m2.sum()) >= 12:
                f2 = fit(Sin[m2])
                parts.append('%s %d -> u %.3f d %+.3f' % (lab, int(m2.sum()), f2[0], f2[1]))
            else:
                parts.append('%s %d (too few)' % (lab, int(m2.sum())))
        found.append((float(ref[0]), float(ref[1]), int(sel.sum()), float(np.median(res)),
                      Sin[:, 0].min(), Sin[:, 0].max(), ' | '.join(parts)))
    else:
        print('   rejected a line on u %.3f: its depth d %+.3f is not on this wall' % (ref[0], ref[1]))
    live[idx[sel]] = False

found.sort(key=lambda t: t[0])
print('')
print('%d jamb lines peeled out, u then d then support then median residual then camera span:'
      % len(found))
for u0, d0, nsup, med, umin, umax, split in found:
    drawn = [lo if EDGE == 'west' else hi for lo, hi in OPEN]
    near = min(drawn, key=lambda t: abs(t - u0))
    print('   u %7.3f  d %+6.3f  %4d rays  %3.0f mm  cameras u %5.1f to %5.1f   drawn %7.3f  %+6.3f m'
          % (u0, d0, nsup, 1000 * med, umin, umax, near, u0 - near))
    print('        %s' % split)

# WHAT THE LIST IS WORTH. Three things are asked of it and none of them is "does it match the plan".
mm = [f[0] - min([lo if EDGE == 'west' else hi for lo, hi in OPEN], key=lambda t: abs(t - f[0]))
      for f in found]
if found:
    print('')
    print('   the depths land between d %+.3f and %+.3f against a wall face measured on %+.3f'
          % (min(f[1] for f in found), max(f[1] for f in found), DNORTH))
    print('   the offsets from the drawn jambs have median %+.3f m and spread %.3f m'
          % (float(np.median(mm)), float(np.ptp(mm)) if len(mm) > 1 else 0.0))
    gaps = [found[i + 1][0] - found[i][0] for i in range(len(found) - 1)]
    if gaps:
        print('   consecutive lines of this parity are %.3f to %.3f m apart, median %.3f'
              % (min(gaps), max(gaps), float(np.median(gaps))))
    other = os.path.join(OUT, 'jamb-%s-lines.npy' % ('east' if EDGE == 'west' else 'west'))
    np.save(os.path.join(OUT, 'jamb-%s-lines.npy' % EDGE),
            np.array([[f[0], f[1], f[2], f[3]] for f in found]))
    if os.path.exists(other):
        # THE WIDTH TEST, which is the one that cannot be faked. Pair each line of this parity with the
        # nearest of the opposite parity on the correct side, and the twelve gaps must agree with each
        # other. Two independent peels, twelve numbers, one width.
        P = np.load(other)
        w = []
        for u0, d0, nsup, med, _a, _b, _s in found:
            cands = P[P[:, 0] > u0] if EDGE == 'west' else P[P[:, 0] < u0]
            if len(cands):
                w.append(abs(float(cands[np.argmin(np.abs(cands[:, 0] - u0))][0]) - u0))
        w = [t for t in w if 0.5 < t < 2.5]
        if len(w) >= 3:
            print('   %d openings measured end to end: width median %.3f m, spread %.3f m, against a'
                  % (len(w), float(np.median(w)), float(np.ptp(w))))
            print('   drawn width of %.3f m' % (OPEN[0][1] - OPEN[0][0]))
