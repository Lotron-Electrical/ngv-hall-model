# 2026-09-10: EVERY horizontal line on an end wall, found without telling the finder where to look.
#
# WHY THIS EXISTS, and it is a blind spot rather than an oversight. tools/end_levels.py measures an end
# level by projecting the line the MODEL draws and taking the strongest gradient inside a window around it.
# That tool refuses any level whose nearest modelled neighbour is closer than 0.55 m, because inside that
# distance it cannot tell one line from the next. Run down the ENDW stack, the refusals are:
#   ground-wall top 5.30 and apron top 5.40     0.10 m apart, both refused
#   lower deck 6.33 and lower parapet top 6.85  0.52 m apart, both refused
#   top slab soffit 8.08 and top deck 8.34      0.26 m apart, both refused
# So of the nine lines the model draws across an end face, the only three ever measured from the floor are
# the top parapet 9.02, the head 11.10 and the wall top 13.50. THE ENTIRE LOWER GALLERY HAS NEVER BEEN
# MEASURED. It is also the part of this model that is hardest to believe: a deck on 6.33 under a ceiling on
# 8.08 is a clear interior height of 1.75 m, and that is not a room a person walks about in.
#
# WHAT IS DIFFERENT HERE. This does not ask "where is level X". It walks h continuously up the end face and
# reports where the brightness actually steps, so the model supplies no starting point and the finder has
# nothing to follow. tools/follow_test.py measured that following: the same 25 frames put the same east
# parapet on 9.039 when the model drew 8.90 and on 9.093 when it drew 9.02, so roughly 45 per cent of the
# answer was the model agreeing with itself. A scan with no seed cannot do that.
#
# THE ONE UNKNOWN PER RAY. A sample point is fixed to the end face plane u = uF, so a ray from a posed
# camera through an image row gives its h outright. The face is only known to about 0.3 m
# (tools/face_sweep.py) and that costs little here: from 20 m away, moving the plane 0.3 m moves an h of
# 7 m by about 0.07 m, which is why that sweep found no level agreeing on any one face.
#
# THE TESTS IT MUST PASS, stated before it is run.
#   near-far   the frames are split by range and each half pooled alone. A line the geometry really
#              carries lands in the same place from both; a line made by the lens or the walk does not.
#   null       the same frames split odd against even. That split shares the geometry, so whatever it
#              returns is this instrument's own noise, and a near-far gap under the null gap says nothing.
#   window     the profile is differentiated at two smoothing widths. A step edge holds still; a gradient
#              in the lighting walks with the window, which is how the false soffit line died on 2026-09-09.
#   python tools/end_scan.py <class> <west|east> [max_frames]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FACE = {'west': 4.194, 'east': 48.056}
HLO = float(os.environ.get('HLO', 4.40))
HHI = float(os.environ.get('HHI', 10.20))
HSTEP = 0.004
NCOL = int(os.environ.get('NCOL', '11'))
cls, end = sys.argv[1], sys.argv[2]
maxf = int(sys.argv[3]) if len(sys.argv) > 3 else 40
uF = FACE[end]
HG = np.arange(HLO, HHI + 1e-9, HSTEP)


def wpt(d, lev):
    return O + uF * HU + d * HD + np.array([0.0, lev, 0.0])


frames = U.load_class(cls)
cand = []
for fr, (cam, ip) in frames.items():
    q = cam.center - O
    cu, ch = q @ HU, q[1]
    if ch > 3.0 or abs(cu - uF) < 10.0:
        continue
    pts = np.array([wpt(d, lev) for d in (3.0, 7.5, 12.0) for lev in (HLO, HHI)])
    x, y, z = cam.project(pts)
    if not np.all(z > 0.3):
        continue
    inside = np.logical_and(np.logical_and(x > 2, x < cam.w - 3),
                            np.logical_and(y > 2, y < cam.h - 3))
    if inside.sum() < 4:
        continue
    cand.append((fr, cam, ip, abs(cu - uF)))
if not cand:
    sys.exit('%s %s: no frame sees this end face' % (cls, end))

# sharpest first: a level 0.15 m out is about 10 px from across the hall and a walking frame carries that
# much motion blur on its own, so blur is filtered before it can be averaged over.
scored = []
for fr, cam, ip, rng in cand:
    im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
    if im is None:
        continue
    small = cv2.resize(im, None, fx=0.25, fy=0.25)
    scored.append((float(cv2.Laplacian(small, cv2.CV_64F).var()), fr, cam, ip, rng))
scored.sort(key=lambda r: -r[0])
use = scored[:maxf]
print('%s %s: %d frames see the face, %d sharpest used, range %.1f to %.1f m'
      % (cls, end, len(cand), len(use), min(u[4] for u in use), max(u[4] for u in use)))


def profile(cam, im, smooth_m):
    """median brightness along h over the sample columns, and its derivative in h."""
    # THE COLUMNS ARE PLACED PER FRAME, and the fixed list this started with was the reason the far half
    # of the walk returned nothing at all. These clips are portrait video: the frame's WIDE axis is the
    # world's vertical one, so across the end wall the field of view is the SHORT side and only a few
    # metres of d are ever in shot. A fixed d list therefore lost every column on most frames and the
    # near-far test could not be run. The visible band of d is found first and the columns spread across
    # whatever it turns out to be.
    vis = []
    for d in np.arange(0.6, 14.8, 0.4):
        P = np.array([wpt(d, lev) for lev in (HLO, 0.5 * (HLO + HHI), HHI)])
        x, y, z = cam.project(P)
        if np.all(np.logical_and.reduce([z > 0.3, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])):
            vis.append(d)
    if len(vis) < 4:
        return None, None
    use_d = list(np.linspace(vis[0], vis[-1], min(NCOL, len(vis))))
    cols = []
    for d in use_d:
        P = np.array([wpt(d, lev) for lev in HG])
        x, y, z = cam.project(P)
        ok = np.logical_and.reduce([z > 0.3, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
        if ok.mean() < 0.85:
            continue
        # a column seen almost edge-on carries no resolution: demand the h band span at least 40 px of
        # image, otherwise every sample lands on the same pixel.
        # MEASURED ON BOTH AXES, and the first version measured only the row. These clips are portrait
        # video, so world-up runs along the image COLUMN axis: on w1_000084 a 5.8 m band of h moves x by
        # 390 px and y by 1 px. Testing the row alone therefore threw away every column of almost every
        # frame, and the pool that reported a near-far test was three frames deep.
        span = float(np.hypot(np.nanmax(x[ok]) - np.nanmin(x[ok]), np.nanmax(y[ok]) - np.nanmin(y[ok])))
        if span < 40:
            continue
        xs, ys = np.clip(x, 0, cam.w - 2), np.clip(y, 0, cam.h - 2)
        x0, y0 = xs.astype(np.int32), ys.astype(np.int32)
        ax, ay = xs - x0, ys - y0
        v = (im[y0, x0] * (1 - ax) * (1 - ay) + im[y0, x0 + 1] * ax * (1 - ay)
             + im[y0 + 1, x0] * (1 - ax) * ay + im[y0 + 1, x0 + 1] * ax * ay)
        v = np.where(ok, v, np.nan)
        # normalise each column by its own spread, so a bright column cannot outvote a dark one
        m, s = np.nanmedian(v), np.nanstd(v)
        cols.append((v - m) / (s + 1e-6))
    if len(cols) < 3:
        return None, None
    prof = np.nanmedian(np.array(cols), axis=0)
    k = max(3, int(round(smooth_m / HSTEP)) // 2 * 2 + 1)
    sm = cv2.GaussianBlur(prof.astype(np.float64).reshape(-1, 1), (1, k), 0).ravel()
    return sm, np.gradient(sm, HSTEP)


def pool(rows, smooth_m):
    out = []
    for _, fr, cam, ip, rng in rows:
        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        _, g = profile(cam, im.astype(np.float64), smooth_m)
        if g is not None:
            out.append(g)
    if not out:
        return None
    pool.n = len(out)
    return np.nanmedian(np.array(out), axis=0)


def peaks(g, minsep_m=0.18, top=14):
    if g is None:
        return []
    a = np.abs(g)
    sep = int(round(minsep_m / HSTEP))
    taken = []
    for i in np.argsort(a)[::-1]:
        if not np.isfinite(a[i]) or a[i] <= 0:
            continue
        if all(abs(i - j) >= sep for j in taken):
            taken.append(i)
        if len(taken) >= top:
            break
    return sorted((float(HG[i]), float(g[i])) for i in taken)


def near_peak(gg, hv, sgn, win=0.22):
    """where a SUBSET puts the same edge: the strongest same-signed slope within win of hv.

    An earlier version re-ran the global top-14 peak pick on the subset and asked whether any of them
    landed nearby, which is a different question and answered nan for the whole far half. A near-far
    test that cannot report a number is not a test.
    """
    if gg is None:
        return float('nan')
    lo, hi = np.searchsorted(HG, hv - win), np.searchsorted(HG, hv + win)
    seg = gg[lo:hi] * (1.0 if sgn > 0 else -1.0)
    if len(seg) < 3 or not np.any(np.isfinite(seg)):
        return float('nan')
    return float(HG[lo + int(np.nanargmax(seg))])


G1 = pool(use, 0.06)
G2 = pool(use, 0.10)
byrange = sorted(use, key=lambda r: r[4])
half = max(4, len(use) // 2)
near = pool(byrange[:half], 0.06)
nn = pool.n
far = pool(byrange[-half:], 0.06)
print('   pooled: all %d, near %d (%.1f to %.1f m), far %d (%.1f to %.1f m)'
      % (len(use), nn, byrange[0][4], byrange[half - 1][4], pool.n if far is not None else 0,
         byrange[-half][4], byrange[-1][4]))
odd = pool(use[1::2], 0.06)
even = pool(use[0::2], 0.06)

MODEL = [('ground-wall top', 5.30), ('apron top', 5.40), ('lower deck', 6.33),
         ('lower parapet top', 6.85), ('lower rail top', 7.16), ('top slab soffit', 8.08),
         ('top deck', 8.34), ('top parapet top', 9.02)]
print('')
print('   THE LINES THE PHOTOGRAPHS CARRY, with no seed from the model:')
print('      h     sign    win.10    near     far     odd    even   nearest drawn level')
for hv, gv in peaks(G1):
    nm, nh = min(MODEL, key=lambda m: abs(m[1] - hv))
    w2 = near_peak(G2, hv, gv)
    n1, f1 = near_peak(near, hv, gv), near_peak(far, hv, gv)
    o1, e1 = near_peak(odd, hv, gv), near_peak(even, hv, gv)
    print('   %6.3f %+6.1f  %7.3f %7.3f %7.3f %7.3f %7.3f  %6.3f %6.3f %6.3f   %-18s %+.3f'
          % (hv, gv, w2, n1, f1, o1, e1, abs(n1 - f1), abs(o1 - e1), abs(w2 - hv), nm, hv - nh))
print('')
print('   sign + is brighter ABOVE the line, - is brighter below. n-f is the near-far disagreement,')
print('   o-e the null (the same frames split odd against even, so it shares the geometry and reports')
print("   only the noise of this instrument), win the movement between the two smoothing widths.")
print('   A LINE IS ACCEPTED ONLY IF n-f IS BOTH UNDER 0.05 m AND UNDER o-e, AND win IS UNDER 0.05.')
print('   Anything else is the lens, the walk, or a gradient in the lighting.')
acc = []
for hv, gv in peaks(G1):
    w2 = near_peak(G2, hv, gv)
    nf = abs(near_peak(near, hv, gv) - near_peak(far, hv, gv))
    oe = abs(near_peak(odd, hv, gv) - near_peak(even, hv, gv))
    if nf < 0.05 and nf <= oe and abs(w2 - hv) < 0.05:
        acc.append((hv, gv))
print('')
print('   SURVIVES ALL THREE: %s' % (', '.join('%.3f (%+.1f)' % a for a in acc) if acc else 'nothing'))
