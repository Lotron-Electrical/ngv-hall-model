# 2026-09-09: THE WEST PARAPET FROM THE HALL FLOOR, which is the only geometry that can separate its
# three unknowns.
#
# The failing bound says the west parapet stands 0.202 m into light that arrived, and says nothing about
# WHICH number is wrong, because from the west deck a top 0.20 m lower, a deck 0.20 m lower and a face
# 0.20 m further into the hall all fit the same rays. Sixteen cameras inside a hand's width of one station
# cannot tell them apart. That is a conditioning problem and conditioning is fixed by standing elsewhere.
#
# THE HALL FLOOR IS ELSEWHERE, AND IT IS BETTER THAN THE EAST CASE WAS. Down there the lens is eight
# metres BELOW the coping instead of a metre above it, so the sightline to the top edge climbs steeply and
# its angle changes fast with distance: 37 degrees from ten metres away, 11 degrees from forty. Two rays
# like that cross at a point. The pair (face station, top height) is then pinned rather than traded, which
# is precisely what the deck could not do and what the east end's far attempt failed to deliver for a
# different reason, photometric rather than geometric.
#
# SO THE FIRST THING HERE IS THE FEASIBILITY TEST THE EAST END FAILED, and it is run before any fitting:
# pool the brightness up the parapet's own face plane over every frame aimed at that end and ask whether
# there is a step there at all. The east answer was a steepest fall of 0.13 of a standard deviation, which
# is no step, and that closed the route with numbers. If the west answers the same way this refuses in the
# same way and nothing is fitted.
#
# THE ROLL RULE APPLIES THROUGHOUT. The hall-floor clips are stored rolled about ninety degrees, so a level
# line in the room is a vertical line in those pictures and any detector that walks image rows or columns
# finds canopy ribs and lift shafts. Everything here walks the face plane's own height ladder.
#   python tools/west_far.py [draw]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
# THE EAST END IS THE CONTROL and it runs through the same code. Its face is now settled to 0.09 m by two
# independent tests on 163 camera positions, so if this instrument returns 48.056 from the hall floor it
# has earned the right to be believed about the west.
END = os.environ.get('END', 'west')
# TAG separates one ladder's rays from another's on the same face, see tools/patch_far_tag.py
TAG = os.environ.get('TAG', '')
# POLARITY names which feature is being looked for, see tools/patch_far_polarity.py.
# 'lit' is the top of a lit front, bright below and dark above. 'shade' is the top of a
# shaded solid with something see-through and lit above it, which is the upstand.
POLARITY = os.environ.get('POLARITY', 'lit')
PSIGN = 1.0 if POLARITY == 'lit' else -1.0
DECK = 8.34
UF, TOPD, SIGN = (4.194, 9.020, +1.0) if END == 'west' else (48.056, 9.110, -1.0)
# THE CLASS LIST IS SETTABLE BECAUSE DAY AGAINST NIGHT IS A TEST, not a convenience. A stone edge reads
# the same under any light; a boundary that is really where the light stops does not, because after dark
# this hall is lit from below and the sides rather than through the stained glass overhead. The jambs
# could not take this test, their 22 night frames yielding no usable column on that band of wall even at
# a 3 grey level bar. The balcony fronts can: the night walk stands u 13.4 to 28.5, which is 9 to 24 m
# from the west end and well past the 8 m this tool needs.
FAR = os.environ.get('FAR', 'walk night day4k').split()
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
# THE LADDER'S SPAN IS THE WHOLE EXPERIMENT, and the first run got it wrong in an instructive way. Over
# h 7.0 to 11.4 the ray fan from a floor camera is wide enough to sweep across the stained-glass ceiling
# where it meets the wall, which is the brightest edge in the building. Drawn back on w1_000023 all 52
# detections sat on that junction, and the line fitted to them landed on u 8.261, four metres out in the
# hall. A step being STRONG says nothing about it being the RIGHT step. Narrowing the ladder to a metre
# and a half around the candidate top puts the ceiling junction outside the fan from anywhere in the hall:
# from u 20 the band subtends 24 to 27 degrees and the junction sits on 30.
HLO = float(os.environ.get('HLO', '8.20'))
HHI = float(os.environ.get('HHI', '10.00'))
HS = np.arange(HLO, HHI, 0.005)           # the height ladder on the face plane
DS = np.linspace(0.6, 14.8, 60)           # stations across the hall
HWIN = int(os.environ.get('HWIN', '40'))  # samples averaged either side of a candidate edge
CONTRAST = 22.0


def rays_of(cam, pix):
    fx, fy, ux, uy = cam.params[0], cam.params[1], cam.params[2], cam.params[3]
    K = np.array([[fx, 0, ux], [0, fy, uy], [0, 0, 1]], float)
    dist = np.array(cam.params[4:8], float) if cam.model == 'OPENCV' else np.zeros(4)
    un = cv2.undistortPoints(np.asarray(pix, np.float64).reshape(-1, 1, 2), K,
                             dist.reshape(1, -1)).reshape(-1, 2)
    v = np.concatenate([un, np.ones((len(un), 1))], 1) @ cam.R
    return v / np.linalg.norm(v, axis=1, keepdims=True)


frames = {}
for cls in FAR:
    try:
        for k, v in U.load_class(cls).items():
            frames.setdefault(k, v)
    except Exception:
        pass
print('%d hall-floor frames in the archive' % len(frames))

face = np.array([O + UF * HU + dd * HD + np.array([0.0, float(v), 0.0]) for dd in DS for v in HS])
nh = len(HS)
profiles = []
rows = []
kept = 0
for stem, (cam, ip) in sorted(frames.items()):
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if ch > 6.0 or cd < 0.8 or cd > 14.6:
        continue                                   # standing on the hall floor
    if (cu - UF) * SIGN < 4.0 or (cu - UF) * SIGN > 42.0:
        continue                                   # far enough from that end to see its face, not past it
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
    if n < 1e-6 or float(fwd @ HU) / n * SIGN > -0.6 or abs(float(fwd[1])) > 0.45:
        continue                                   # pointed at that end, and roughly level not at the roof
    x, y, z = cam.project(face)
    ok = np.logical_and.reduce((z > 0.3, x > 40, x < cam.w - 40, y > 40, y < cam.h - 40))
    if ok.sum() < 400:
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
        sd = float(v.std())
        if sd < 1e-3:
            continue
        prof = np.full(len(HS), np.nan)
        prof[a:b + 1] = (v - v.mean()) / sd
        profiles.append(prof)
        # the biggest bright-below dark-above step, walked along the wall's own height
        best, besti = -1e9, None
        for i in range(HWIN, len(v) - HWIN):
            dstep = PSIGN * float(v[i - HWIN:i].mean() - v[i + 1:i + 1 + HWIN].mean())
            if dstep > best:
                best, besti = dstep, i
        if besti is None or best < CONTRAST:
            continue
        k = a + besti
        pix = [(float(x[sl][k]), float(y[sl][k]))]
        vv = rays_of(cam, pix)[0]
        rows.append((cu, ch, float(vv @ HU), float(vv[1]), stem,
                     (int(round(pix[0][0])), int(round(pix[0][1]))), float(best)))

print('%d frames on the floor look at the %s end and are roughly level' % (kept, END))
if len(profiles) < 40:
    raise SystemExit('nothing down there sees the west parapet face; refused')

P = np.vstack(profiles)
mean = np.nanmean(P, axis=0)
cnt = np.sum(~np.isnan(P), axis=0)
good = cnt > max(20, 0.2 * len(P))
hs, mm = HS[good], mean[good]
grad = np.gradient(mm, hs)
k = int(np.argmin(PSIGN * grad))               # the steepest step of the chosen polarity
print('')
print('THE FEASIBILITY TEST, pooled over %d station profiles' % len(P))
print('   the steepest %s in brightness going up the face plane is between h %.3f and %.3f'
      % ('fall' if POLARITY == 'lit' else 'rise', hs[max(0, k - 1)],
         hs[min(len(hs) - 1, k + 1)]))
print('   and it is %.2f of a standard deviation per metre. The east end returned 0.13 and was refused.'
      % abs(float(grad[k])))
for probe in (DECK + 0.05, TOPD, TOPD + 0.3):
    j = int(np.argmin(np.abs(hs - probe)))
    print('   at the drawn %.3f the pooled profile reads %+.3f sd with a slope of %+.3f sd per metre'
          % (probe, float(mm[j]), float(grad[j])))

if abs(float(grad[k])) < 0.6:
    print('')
    print('   THERE IS NO STEP THERE TO MEASURE. Refused, exactly as the east end was, and for the same')
    print('   photometric reason rather than a geometric one. Nothing is fitted and nothing moves.')
    raise SystemExit(0)

print('')
print('%d edge detections survived the %.0f grey level contrast test' % (len(rows), CONTRAST))
if len(rows) < 30:
    raise SystemExit('too few detections to fit a line')
R = np.array([[r[0], r[1], r[2], r[3]] for r in rows], float)
np.save(os.path.join(OUT, '%s%s-far-rays.npy' % (END, TAG)), R)
span = float(R[:, 0].max() - R[:, 0].min())
A = np.stack([R[:, 3], -R[:, 2]], 1)
yv = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
sol, _r, _rk, sv = np.linalg.lstsq(A, yv, rcond=None)
res = A @ sol - yv
cond = float(sv.max() / sv.min()) if sv.min() > 0 else float('inf')
print('')
print('%d rays from cameras spanning %.1f m of u; least squares puts the top edge on u %.3f h %.3f'
      % (len(R), span, float(sol[0]), float(sol[1])))
print('   condition number %.0f, residual rms %.4f m' % (cond, float(np.sqrt((res ** 2).mean()))))

# A HALF-METRE RESIDUAL OVER FOUR THOUSAND DETECTIONS IS A MIXTURE, NOT A LINE. Least squares fits every
# ray including the ones that found a truss, a lamp or a lit doorway, and one line through all of them is
# an average of several things. RANSAC asks the different question: is there a line a large minority of
# these rays actually agree on, and how many.
rng = np.random.default_rng(7)
bestn, bestsol = -1, None
for _ in range(4000):
    i, j = rng.integers(0, len(R), 2)
    a2 = np.stack([R[[i, j], 3], -R[[i, j], 2]], 1)
    y2 = R[[i, j], 3] * R[[i, j], 0] - R[[i, j], 2] * R[[i, j], 1]
    if abs(np.linalg.det(a2)) < 1e-9:
        continue
    cand = np.linalg.solve(a2, y2)
    if not (UF - 2.0 < cand[0] < UF + 2.0 and 8.0 < cand[1] < 11.0):
        continue
    r2 = np.abs(A @ cand - yv)
    n2 = int((r2 < 0.08).sum())
    if n2 > bestn:
        bestn, bestsol = n2, cand
if bestsol is not None:
    inl = np.abs(A @ bestsol - yv) < 0.08
    a3 = A[inl]
    y3 = yv[inl]
    ref, _r3, _rk3, _sv3 = np.linalg.lstsq(a3, y3, rcond=None)
    print('   RANSAC: %d of %d rays (%.0f per cent) agree on u %.3f h %.3f inside 80 mm'
          % (bestn, len(R), 100.0 * bestn / len(R), float(ref[0]), float(ref[1])))
    print('   refit on those inliers alone: residual rms %.4f m'
          % float(np.sqrt(((a3 @ ref - y3) ** 2).mean())))


def rms_for(uu, vv):
    r = R[:, 3] * uu - R[:, 2] * vv - (R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1])
    return float(np.sqrt((r ** 2).mean()))


best = rms_for(float(sol[0]), float(sol[1]))
drawn = rms_for(UF, TOPD)
print('   the drawn pair (%.3f, %.3f) scores %.4f against the best %.4f, %.2f times worse'
      % (UF, TOPD, drawn, best, drawn / max(best, 1e-9)))
lower = rms_for(UF, 8.818)
print('   the pair the deck arrivals allow (%.3f, 8.818) scores %.4f, %.2f times the best'
      % (UF, lower, lower / max(best, 1e-9)))

if 'draw' in sys.argv:
    by = {}
    for r in rows:
        by.setdefault(r[4], []).append(r[5])
    stem = max(by, key=lambda k2: len(by[k2]))
    cam, ip = frames[stem]
    im = cv2.imread(ip)
    for c, rr in by[stem]:
        cv2.circle(im, (c, rr), 12, (0, 255, 255), 3)
    cv2.putText(im, '%s  %d detections on the west parapet' % (stem, len(by[stem])), (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 255), 3, cv2.LINE_AA)
    os.makedirs(OUT, exist_ok=True)
    kk = 1400.0 / im.shape[0]
    dst = os.path.join(OUT, stem + '-' + END + '-far.jpg')
    cv2.imwrite(dst, cv2.resize(im, (int(im.shape[1] * kk), 1400)), [cv2.IMWRITE_JPEG_QUALITY, 86])
    print('')
    print('drawn back into', dst)
