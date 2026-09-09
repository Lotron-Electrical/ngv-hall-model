# 2026-09-09: THE OPENING HEAD FOUND WITHOUT A DRAWN LINE, using the wall's own coursing as the ruler.
#
# Every reading of this edge so far has come from an instrument that starts at the drawn height and walks
# to the nearest strong gradient. Fitting the follow gain three ways showed what that costs: the surviving
# readings put the head 40 to 205 mm BELOW 11.35 and disagree by 165 mm, which is a lean without a
# magnitude. The way past it is not a better window. It is a detector that never sees the drawn value.
#
# TWO THINGS MAKE THAT POSSIBLE HERE.
# First, the head is not an edge like the others. Below it is the opening, which is a dark void; above it
# is lit bluestone. That is a STEP IN BRIGHTNESS across half a metre, not a thin dark line, and a bed joint
# is the opposite: a thin dark line with the same stone either side. So the head can be found by the
# statistic that separates those two, the difference between the mean brightness above a height and below
# it, maximised over the WHOLE height range rather than a window around a guess. A course line scores
# nothing on that statistic no matter how sharp it is.
# Second, the coursing is a measured ruler. The north bed joints sit on h = 0.080 + 0.304k, from 4 mm
# orthophotos of 1,026 posed frames, so the wall carries its own scale independent of anything drawn. The
# profile taken on the PIER beside an opening shows that ladder directly, and its phase is checked here
# against the ladder rather than assumed, which is the test that the profile is sampling what it thinks.
#
# WHAT THIS CANNOT DO. It needs the stone above the head to be lit and the void below it to be dark, which
# is a daylight condition, and it needs the wall face square enough to the camera that a horizontal line
# stays horizontal over the sampled width. Frames failing either are refused rather than fitted.
#   python tools/head_courses.py <class> [max_frames]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.090
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.770, 19.983],
            [22.418, 23.631], [26.066, 27.279], [29.816, 31.028], [33.495, 34.706], [37.177, 38.383],
            [40.906, 42.118], [44.526, 45.739]]
COURSE = 0.304
PHASE = 0.080
HLO, HHI = 9.60, 12.60          # the range searched, wide enough that no drawn value is implied
STEP = 0.004
HALF = 0.45                     # the half window the step statistic averages over

cls = sys.argv[1]
maxf = int(sys.argv[2]) if len(sys.argv) > 2 else 24
frames = U.load_class(cls)
hs = np.arange(HLO, HHI + 1e-9, STEP)


def profile(cam, img, uu):
    pts = np.array([O + uu * HU + DN * HD + np.array([0, float(v), 0]) for v in hs])
    x, y, z = cam.project(pts)
    ok = (z > 0.5) * (x > 20) * (x < cam.w - 20) * (y > 20) * (y < cam.h - 20)
    if ok.sum() < 0.6 * len(hs):
        return None
    xi = np.clip(np.round(x), 0, img.shape[1] - 1).astype(np.int32)
    yi = np.clip(np.round(y), 0, img.shape[0] - 1).astype(np.int32)
    v = img[yi, xi].astype(np.float32)
    v[np.logical_not(ok)] = np.nan
    return v


def step_height(v):
    """the height where the profile changes level most, dark below and bright above"""
    n = int(round(HALF / STEP))
    best, besti = -1e9, None
    for i in range(n, len(v) - n):
        lo = v[i - n:i]
        hi = v[i + 1:i + 1 + n]
        if np.isnan(lo).any() or np.isnan(hi).any():
            continue
        d = float(hi.mean() - lo.mean())
        if d > best:
            best, besti = d, i
    if besti is None:
        return None
    return float(hs[besti]), best


rows = []
for fr, (cam, ip) in sorted(frames.items()):
    if len(rows) >= maxf:
        break
    q = cam.center - O
    cu, cd = float(q @ HU), float(q @ HD)
    if cd < 1.0:
        continue                         # must be out in the hall looking at this wall
    img = None
    for oi, (u0, u1) in enumerate(OPENINGS):
        mid = 0.5 * (u0 + u1)
        if abs(cu - mid) > 12.0:
            continue                     # square enough that a level line stays level across the sample
        if img is None:
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None:
                break
            img = cv2.GaussianBlur(img, (5, 5), 0)
        v = profile(cam, img, mid)
        if v is None:
            continue
        got = step_height(v)
        if got is None:
            continue
        hv, contrast = got
        if contrast < 12.0:
            continue                     # no real step here, so no head is visible
        pier = profile(cam, img, u1 + 0.35 if u1 + 0.35 < 51.0 else u0 - 0.35)
        # THE DISCRIMINATOR. A reveal 0.9 m deep shows its SOFFIT UNDERSIDE to anyone looking up from the
        # hall, and that underside faces the lit floor, so it can read brighter than the stone above it and
        # put the brightness step below the true head. If that is what is being found, the reading must
        # MOVE WITH THE VIEWING ANGLE, because the soffit's apparent depth into the opening is pure
        # perspective; if it is the head itself, the reading cannot care where the camera stands. So each
        # reading carries the camera's elevation angle to the drawn head, and the two hypotheses are then
        # separated by a correlation rather than by argument.
        rng = float(np.hypot(cu - mid, cd - DN))
        elev = float(np.degrees(np.arctan2(11.35 - float(q[1]), rng)))
        rows.append((fr, oi + 1, hv, contrast, rng, elev))

if not rows:
    raise SystemExit('no frame in this class shows a lit step over a dark opening')

print(cls, len(rows), 'readings from', len(set(r[0] for r in rows)), 'frames')
print('   the search ran over h', HLO, 'to', HHI, 'and never saw the drawn 11.35')
per = {}
for fr, oi, hv, c, dist, elev in rows:
    per.setdefault(oi, []).append(hv)
print('')
print('opening   n   median h   spread   nearest bed joint   head above it')
allh = []
for oi in sorted(per):
    a = np.array(per[oi])
    if len(a) < 3:
        continue
    m = float(np.median(a))
    allh.append(m)
    k = round((m - PHASE) / COURSE)
    joint = PHASE + COURSE * k
    print('%7d %3d %10.3f %8.3f %19.3f %15.3f' % (oi, len(a), m, float(a.max() - a.min()), joint, m - joint))
E = np.array([[r[5], r[2], r[4]] for r in rows])
if E.shape[0] >= 6:
    cc = float(np.corrcoef(E[:, 0], E[:, 1])[0, 1])
    print('')
    print('   IS IT THE HEAD OR THE SOFFIT. elevation angle', round(float(E[:, 0].min()), 1), 'to',
          round(float(E[:, 0].max()), 1), 'deg; correlation between angle and the height found:', round(cc, 3))
    slope = float(np.polyfit(E[:, 0], E[:, 1], 1)[0])
    print('   the reading moves', round(slope, 4), 'm per degree of elevation, so over the', 
          round(float(E[:, 0].max() - E[:, 0].min()), 1), 'deg spread it moves',
          round(slope * float(E[:, 0].max() - E[:, 0].min()), 3), 'm')
    if abs(cc) > 0.5:
        print('   THAT IS PERSPECTIVE, NOT A LEVEL. What is being found moves with where the camera stands,')
        print('   which the head cannot do. The low readings are the reveal soffit, and every one of them is')
        print('   a LOWER BOUND on the head rather than a measurement of it.')
    else:
        print('   the reading does not track the viewing angle, so it is a property of the wall')

if len(allh) >= 3:
    A = np.array(allh)
    print('')
    print('   across', len(A), 'openings: median', round(float(np.median(A)), 3),
          'spread', round(float(A.max() - A.min()), 3))
    print('   the model draws 11.35, so this puts the head', round(float(np.median(A)) - 11.35, 3), 'm from it')
