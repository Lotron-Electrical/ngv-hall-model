# 2026-09-09: the back edge of the gallery soffit, which is how deep the balcony actually is.
#
# ENDW.soffitDepth is 2.1 and ENDW.head is 11.1, and the shipped file says of both that nothing has ever
# seen them. The soffit is the ceiling over the top gallery: a horizontal surface at h 11.1 running from
# the balcony face back into the end bay. Its FRONT edge sits on the face; its BACK edge is where it meets
# the end wall, and the distance between them is the depth of the balcony.
#
# BOTH EDGES ARE THE SAME LINE THE INSTRUMENT ALREADY MEASURES: a horizontal line at constant (u, h)
# spanning d, met by a ray when vh*(u* - cu) - vu*(h* - ch) = 0. So this is the fourth orientation of one
# equation, and it needs no new algebra, only the right ladder and the right parity.
#
# WHY NOBODY HAS EVER SEEN IT, WHICH IS WORTH KNOWING BEFORE READING A PIXEL. A ray from the hall floor to
# that back edge has to clear the parapet in front of it. From ten metres out it passes the face on h 9.83
# against a handrail measured on 9.799: three centimetres of clearance, which is nothing. From forty
# metres out it clears by 0.78 m. The balcony hides its own soffit from anyone standing near it, and only
# the far half of the hall can see under the head at all.
#
# THE LADDER IS CHOSEN SO THE FAN CANNOT REACH THE EDGE ALREADY MEASURED. Anything lying ON the face plane
# appears on the ladder at its own height for EVERY camera, because the ladder is built on that plane. The
# balcony front top was measured on 9.799 west and 9.865 east, so a ladder starting on 9.95 excludes it by
# construction rather than by hoping. That also sets which cameras can contribute: the crossing height
# rises with distance, so 9.95 admits everything beyond about u 22.
#
# THE PARITY IS THE LIT ONE. Below the back edge is the gallery's lit back wall; above it is the soffit
# underside, which the shipped file already records as 0.37 times the brightness of that wall by day.
# Bright below, dark above.
#
# AND THE PEEL RATHER THAN ONE FIT, because there are two edges in that band and not one: the soffit's
# front edge on the face and its back edge behind. Finding both is the measurement, since the gap between
# them IS the depth. Lines are taken strongest first and their rays removed until nothing has support.
#   python tools/soffit_back.py        END=east python tools/soffit_back.py
#   CONTROL=1 python tools/soffit_back.py     (drops the ladder onto the measured front top)
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
END = os.environ.get('END', 'west')
CONTROL = os.environ.get('CONTROL', '') == '1'
# face station, which way the bay lies from it, the drawn soffit height, and the measured front top
UF, SIGN, HEADH, FRONT = ((4.194, -1.0, 11.1, 9.799) if END == 'west'
                          else (48.056, +1.0, 11.1, 9.865))
# TARGET=rail points the same peel at the band around the balcony front top instead of the one under the
# head. It is here because the CONTROL run found something nobody had accounted for: TWO lines on that
# face, 9.795 and 9.907, 345 and 306 rays, 13 and 20 mm medians, 108 mm apart. The model draws a single
# 60 mm handrail band there. Either the rail is thicker than drawn or there is a second element above it,
# and the way to tell a building feature from an artefact is whether the OTHER end shows the same pair at
# the same spacing. One implementation, one control, three ladders.
TARGET = os.environ.get('TARGET', 'soffit')
if TARGET == 'rail':
    _dlo, _dhi = FRONT - 0.28, FRONT + 0.38
elif CONTROL:
    _dlo, _dhi = 9.60, 10.10
else:
    _dlo, _dhi = 9.95, 11.40
HLO = float(os.environ.get('HLO', '%.3f' % _dlo))
HHI = float(os.environ.get('HHI', '%.3f' % _dhi))
HS = np.arange(HLO, HHI, 0.004)
DS = np.arange(1.0, 14.0, 0.35)              # the line spans the hall, so walk it across d
HWIN, CONTRAST, THRESH, MINSUP = 40, 20.0, 0.06, 40
# THE LADDER-NARROWING TRICK HAS A FLOOR, AND IT WAS FOUND BY WALKING INTO IT. Excluding an edge by
# starting the ladder above it works beautifully when there is room: that is how the head on 11.09 was
# separated from the front top on 9.799, across a 1.45 m ladder. Tried on a 0.42 m ladder to isolate the
# line sitting 0.2 m above the front top, it returned ZERO detections at both ends, and that is arithmetic
# rather than architecture. The step is the mean of HWIN samples below a candidate against HWIN above, so
# a candidate needs HWIN*0.004 = 0.16 m of ladder on each side and the usable band is the ladder minus
# 0.32 m. A 0.42 m ladder can only place candidates in its middle 0.10 m, and 10.01 was not in it.
# So a feature cannot be isolated from one 0.2 m below it without also shrinking HWIN, which is a
# different detector and would need its own control. Recorded rather than worked around.
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'


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

face = np.array([O + UF * HU + float(dv) * HD + np.array([0.0, float(hv), 0.0])
                 for dv in DS for hv in HS])
nh = len(HS)
rows = []
kept = 0
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if ch > 6.0:
        continue
    # SIGN points from the face INTO the bay, so -SIGN points out into the hall. The first version of
    # this had both of these the wrong way round and kept zero frames, which is what a sign error looks
    # like from the outside: an empty refusal that reads exactly like a real one.
    if (cu - UF) * (-SIGN) < 8.0:            # far enough out to see under this head at all
        continue
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or (float(fwd @ HU) / n) * SIGN < 0.45:
        continue                             # looking along the hall toward this end
    x, y, z = cam.project(face)
    ok = np.logical_and.reduce((z > 0.3, x > 30, x < cam.w - 30, y > 30, y < cam.h - 30))
    if ok.sum() < 200:
        continue
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    kept += 1
    for di in range(len(DS)):
        sl = slice(di * nh, (di + 1) * nh)
        m = ok[sl]
        idx = np.where(m)[0]
        if idx.size < 3 * HWIN or not np.all(m[idx.min():idx.max() + 1]):
            continue
        a, b = int(idx.min()), int(idx.max())
        xi = np.clip(np.round(x[sl][a:b + 1]), 0, cam.w - 1).astype(np.int32)
        yi = np.clip(np.round(y[sl][a:b + 1]), 0, cam.h - 1).astype(np.int32)
        v = grey[yi, xi].astype(np.float32)
        if len(v) < 3 * HWIN:
            continue
        c = np.cumsum(np.concatenate([[0.0], v]))
        i0 = np.arange(HWIN, len(v) - HWIN)
        below = (c[i0] - c[i0 - HWIN]) / HWIN
        above = (c[i0 + HWIN + 1] - c[i0 + 1]) / HWIN
        step = below - above                                    # bright below, dark above
        cand = np.where(step > CONTRAST)[0]
        if cand.size == 0:
            continue
        order = cand[np.argsort(-step[cand])]
        taken = np.zeros(len(step), bool)
        picks = []
        for j in order:
            if taken[j]:
                continue
            picks.append(j)
            taken[max(0, j - HWIN):j + HWIN] = True
            if len(picks) >= 6:
                break
        for j in picks:
            k = a + i0[j]
            vv = rays_of(cam, [(float(x[sl][k]), float(y[sl][k]))])[0]
            rows.append((cu, ch, float(vv @ HU), float(vv[1]), float(DS[di])))

print('%s %s, ladder h %.2f to %.2f: %d frames, %d steps above %.0f grey levels'
      % (END.upper(), 'CONTROL' if CONTROL else TARGET.upper(), HLO, HHI, kept, len(rows), CONTRAST))
if len(rows) < 120:
    raise SystemExit('too few steps under that soffit; refused')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
DD = np.array([r[4] for r in rows])
os.makedirs(OUT, exist_ok=True)
# Saved under the naming tools/far_edge_range.py reads, because that tool carries the RANGE test and the
# range is the only thing that can say whether a line sits on the balcony face or on something behind it.
# The columns are the same four it expects: cu, ch, vu, vh.
POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
os.makedirs(POSEDIR, exist_ok=True)
np.save(os.path.join(POSEDIR, '%s-%s%s-far-rays.npy' % (END, TARGET, '-ctl' if CONTROL else '')),
        np.column_stack([R, DD]))
print('   cameras stand from u %.2f to %.2f, %.1f m of baseline along the hall'
      % (R[:, 0].min(), R[:, 0].max(), R[:, 0].max() - R[:, 0].min()))


def perp(R, uv, hv):
    num = R[:, 3] * (uv - R[:, 0]) - R[:, 2] * (hv - R[:, 1])
    return np.abs(num) / np.sqrt(R[:, 2] ** 2 + R[:, 3] ** 2)


def fit(R):
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, _sv = np.linalg.lstsq(A, y, rcond=None)
    return sol


live = np.ones(len(R), bool)
found = []
rng = np.random.default_rng(31)
for _round in range(12):
    idx = np.where(live)[0]
    if idx.size < MINSUP:
        break
    S = R[idx]
    ii = rng.integers(0, len(S), 30000)
    jj = rng.integers(0, len(S), 30000)
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
        behind = (c[0] - UF) * SIGN
        if behind < -0.6 or behind > 5.0:
            continue                          # on the face or behind it, never out in the hall
        if not (HLO - 0.5 < c[1] < HHI + 0.5):
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
    Sin = S[sel]
    nearer = np.abs(Sin[:, 0] - UF) <= float(np.median(np.abs(Sin[:, 0] - UF)))
    parts = []
    for lab, m2 in (('near', nearer), ('far', ~nearer)):
        if int(m2.sum()) >= 15:
            f2 = fit(Sin[m2])
            parts.append('%s %d u %.3f h %.3f' % (lab, int(m2.sum()), f2[0], f2[1]))
    found.append((float(ref[0]), float(ref[1]), int(sel.sum()),
                  float(np.median(perp(Sin, ref[0], ref[1]))), ' | '.join(parts)))
    live[idx[sel]] = False

found.sort(key=lambda t: -t[2])
print('')
print('%d line(s) peeled out of that band:' % len(found))
for u0, h0, n, med, split in found:
    print('   u %7.3f  h %7.3f  %4d rays  %3.0f mm   %.3f m behind the face'
          % (u0, h0, n, 1000 * med, (u0 - UF) * SIGN))
    print('        %s' % split)

if CONTROL:
    print('')
    if not found:
        print('   CONTROL FAILED: it cannot find an edge that two other instruments have already pinned,')
        print('   so nothing this tool says about the soffit counts.')
    else:
        best = min(found, key=lambda t: abs(t[1] - FRONT))
        print('   CONTROL: the balcony front top was measured on u %.3f h %.3f. The closest line here is'
              % (UF, FRONT))
        print('   u %.3f h %.3f, so %+.3f m in height and %+.3f m in station.'
              % (best[0], best[1], best[1] - FRONT, best[0] - UF))
elif TARGET == 'rail':
    print('')
    print('   the balcony front top was measured on h %.3f, and the model draws a 60 mm handrail band'
          % FRONT)
    hs = sorted(f[1] for f in found)
    for i in range(len(hs) - 1):
        print('   consecutive lines %.3f and %.3f are %.0f mm apart' % (hs[i], hs[i + 1],
                                                                        1000 * (hs[i + 1] - hs[i])))
else:
    print('')
    print('   the model draws the head on h %.3f and the soffit %.3f m deep, so its back edge is u %.3f'
          % (HEADH, 2.1, UF + SIGN * 2.1))
    if len(found) >= 2:
        a, b = sorted(found[:2], key=lambda t: (t[0] - UF) * SIGN)
        print('   two lines: the front on u %.3f and the back on u %.3f, a soffit %.3f m deep'
              % (a[0], b[0], abs(b[0] - a[0])))
    elif found:
        print('   only ONE line came out, %.3f m behind the face. A depth needs both edges, so that is a'
              % ((found[0][0] - UF) * SIGN))
        print('   station and not a depth, and it is reported as one.')
