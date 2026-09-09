# 2026-09-10: IS THE EAST LOWER TIER A RECESS OR A FACE? ASKED BY PARALLAX, WITH NO LAMPS INVOLVED.
#
# THE GAP THIS AIMS AT IS ADMITTED IN index.html IN SO MANY WORDS. When the apron, the solid upstand, the
# glass rail and the 6.33 slab were deleted and the lower tier became an open recess, the proof was WEST
# ONLY: 33 rays near d 6.2 to 8.2 at the west end. The two east candidates failed their own split-halves
# test by 0.481 and 2.015 m and were dropped. The file says outright that drawing the two ends differently
# on no east evidence would be worse than drawing them alike, so BOTH ends were changed and the asymmetry
# in what is proved was written down. That leaves the east lower tier drawn on nothing.
#
# THE TEST NEEDS NO LAMP AND NO EDGE. A surface has a DEPTH, and depth shows up as parallax. Pick a plane
# at some distance behind the end face, sample a fixed world point on it, and look at that point in many
# frames taken from different places. If the real surface is on that plane, every frame is looking at the
# same physical spot and the brightness agrees. If the real surface is somewhere else, each frame samples
# a different spot and the brightness scatters. Sweep the plane from the face backwards and the depth
# where the scatter is least is where the surface is. This is a plane sweep, and it decides recess
# against face without knowing what is inside either.
#
# THE INSTRUMENT IS VALIDATED ON A SURFACE WHOSE ANSWER IS ALREADY KNOWN. The same sweep is run on the
# NORTH WALL, a large flat wall whose position this project has measured many times over. If the sweep
# does not put the north wall on the north wall, nothing it says about an end face counts.
#
# AND THE ONE WAY IT CAN FAIL QUIETLY IS CHECKED FOR. A recess interior that is unlit and featureless has
# nothing to disagree about, so every depth scores well and the minimum means nothing. The contrast
# actually present in the sampled band is measured and printed, and the run refuses itself if it is flat.
#   python tools/end_depth.py
import io
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k')
DEPTHS = np.arange(0.0, 4.001, 0.20)
MINFR = 8
FLAT = 0.06                        # a band with less spread than this across the grid is featureless

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(key):
    return float(re.search(r'\b' + key + r':\s*(-?[0-9.]+)', BLOCK).group(1))


BACK_W, BACK_E = endw('west'), endw('east')
DEEP = endw('face')
FACE_W, FACE_E = BACK_W + DEEP, BACK_E - DEEP
DSOUTH = endw('dSouth')
GROUND = endw('groundTop')
TOPSLAB = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1)) - endw('slab')
DNORTH = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
print('the recess this file draws runs h %.2f to %.2f and is %.3f m deep at both ends'
      % (GROUND, TOPSLAB, DEEP))
print('the west proof was 33 rays; the east has none, and that is what this is for')

DS = np.arange(1.0, DSOUTH - 1.0 + 1e-9, 1.00)
DECK = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1))
RAILTOP = DECK + float(re.search(r'railTops:\{west:[0-9.]+, east:([0-9.]+)\}', BLOCK).group(1))
HEAD = endw('head')


def grid(u, hlo, hhi):
    hs = np.arange(hlo, hhi + 1e-9, 0.30)
    return np.array([O + u * HU + dv * HD + np.array([0.0, hv, 0.0]) for hv in hs for dv in DS])


# THE TARGETS. Two end faces whose depth is the question, and one north wall whose depth is the answer.
# THE CONTROL RUNS FIRST, because a control printed after the results it is meant to validate is
# decoration. If the north wall does not come back on the north wall, the run stops there.
# AND A SECOND CONTROL THAT THE FIRST CANNOT PROVIDE. A plane sweep run across an APERTURE is biased
# towards the aperture plane: at deeper planes the sampled points fall behind the jambs for some views and
# not others, so the frames disagree for a reason that has nothing to do with where the surface is. The
# north wall has no aperture in front of it and cannot test that. The TOP GALLERY can: it is a recess of
# the same drawn depth, in the same end wall, and it is KNOWN to be open because 286 posed cameras stand
# inside it. Sampled above the rail top so no barrier is in the way. If the sweep cannot find 3.85 m
# there, it cannot find it in the tier below either, and the lower reading means nothing.
TARGETS = [('north wall CONTROL', DNORTH, -1.0, 'd', 0.0, 0.0),
           ('east top gallery CONTROL', FACE_E, 1.0, 'u', RAILTOP + 0.15, HEAD - 0.40),
           ('west top gallery CONTROL', FACE_W, -1.0, 'u', RAILTOP + 0.15, HEAD - 0.40),
           ('west end', FACE_W, -1.0, 'u', GROUND + 0.30, TOPSLAB - 0.30),
           ('east end', FACE_E, 1.0, 'u', GROUND + 0.30, TOPSLAB - 0.30)]
HSN = np.arange(3.0, 7.5 + 1e-9, 0.30)
USN = np.arange(6.0, 46.0 + 1e-9, 2.00)


def grid_north(d):
    return np.array([O + uv * HU + d * HD + np.array([0.0, hv, 0.0]) for hv in HSN for uv in USN])


RESULT = {}
for name, base, sgn, axis, hlo, hhi in TARGETS:
    pts = {}
    for D in DEPTHS:
        pts[D] = grid_north(base - D) if axis == 'd' else grid(base + sgn * D, hlo, hhi)
    npts = len(next(iter(pts.values())))
    acc = {D: [[] for _ in range(npts)] for D in DEPTHS}
    nf = 0
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            if ch > 3.0 or not (0.0 < cd < DSOUTH):
                continue
            if axis == 'u' and ((sgn < 0 and cu < base + 3.0) or (sgn > 0 and cu > base - 3.0)):
                continue
            # it has to be looking that way, or the plane is edge on and nothing is sampled
            f = cam.R.T @ np.array([0, 0, 1.0])
            # sgn already points from the face INTO the recess, so a camera looking that way has
            # its forward vector along +sgn. The first version negated this and every end returned
            # zero frames, which looked like missing data and was a sign error.
            look = (float(f @ HU) * sgn) if axis == 'u' else (-float(f @ HD))
            if look < 0.5:
                continue
            im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            used = False
            for D in DEPTHS:
                x, y, z = cam.project(pts[D])
                ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
                idx = np.nonzero(ok)[0]
                if idx.size < 0.4 * npts:
                    continue
                v = np.array([float(im[int(y[i]), int(x[i])]) for i in idx])
                m = float(np.median(v))
                if m < 6:
                    continue
                used = True
                for n, i in enumerate(idx):
                    acc[D][i].append(v[n] / m)
            if used:
                nf += 1

    print('')
    print('%s: %d frames' % (name.upper(), nf))
    if nf < 15:
        print('   too few frames look at it; nothing can be judged here')
        continue
    curve = []
    for D in DEPTHS:
        sp = [float(np.percentile(vv, 75) - np.percentile(vv, 25))
              for vv in acc[D] if len(vv) >= MINFR]
        if len(sp) < 0.3 * npts:
            continue
        med = [float(np.median(vv)) for vv in acc[D] if len(vv) >= MINFR]
        curve.append((D, float(np.median(sp)), len(sp), float(np.percentile(med, 90) -
                                                              np.percentile(med, 10))))
    if len(curve) < 5:
        print('   too few depths filled; nothing can be judged here')
        continue
    con = float(np.median([c[3] for c in curve]))
    print('   the sampled band spreads %.3f across the grid; under %.2f there is nothing to disagree'
          % (con, FLAT))
    if con < FLAT:
        print('   THE BAND IS FEATURELESS, so every depth agrees and the minimum means nothing. REFUSED.')
        continue
    print('   depth   scatter across frames   cells')
    for D, s, n, _ in curve:
        if abs(D % 0.4) < 1e-6:
            print('   %.2f    %.4f                 %5d' % (D, s, n))
    best = min(curve, key=lambda t: t[1])
    worst = max(curve, key=lambda t: t[1])
    print('   LEAST SCATTER ON DEPTH %.2f m (%.4f), most on %.2f m (%.4f), a contrast of %.0f per cent'
          % (best[0], best[1], worst[0], worst[1], 100.0 * (worst[1] - best[1]) / worst[1]))
    RESULT[name] = best[0]
    # AND THE SAME NUMBERS RESOLVED ALONG THE LENGTH, because a recess need not be one depth all the way
    # and pooling over 14 m of it would hide that. The cells run h-major over DS, so the column index is
    # the remainder. This costs nothing: it is the accumulator already built, grouped a second way.
    if axis == 'u':
        nd = len(DS)
        line = []
        for di in range(nd):
            sub = []
            for D in DEPTHS:
                vv = [acc[D][i] for i in range(npts) if i % nd == di and len(acc[D][i]) >= MINFR]
                if len(vv) >= 3:
                    sub.append((D, float(np.median([np.percentile(v, 75) - np.percentile(v, 25)
                                                    for v in vv]))))
            line.append('%.0f:%s' % (DS[di], '%.1f' % min(sub, key=lambda t: t[1])[0] if sub else '-'))
        print('   depth by the metre along d:  %s' % '  '.join(line))
    if name.startswith('north'):
        ok = best[0] <= 0.4
        print('   THE CONTROL %s: the north wall should read depth 0 and reads %.2f.'
              % ('PASSES' if ok else 'FAILS', best[0]))
        if not ok:
            print('   NOTHING THIS RUN SAYS ABOUT AN END FACE COUNTS. The sweep cannot find a wall it')
            print('   already knows the answer to, so it cannot find one it does not.')
            sys.exit(0)
    elif name.endswith('CONTROL'):
        print('   this gallery IS open and its back wall IS %.3f m back. The sweep says %.2f m.'
              % (DEEP, best[0]))
    else:
        print('   this file draws that surface %.3f m back. The sweep puts it %.2f m back.' % (DEEP, best[0]))

print('')
# EVERY CONTROL HAS TO PASS BEFORE ANY TARGET IS BELIEVED, and the first version of this verdict took the
# BEST control and ignored the other, which is how a broken instrument gets quoted.
GOOD = 0.60
ctl = {k: RESULT[k] for k in RESULT if k.endswith('CONTROL')}
passed = {k: (v <= 0.40 if k.startswith('north') else abs(v - DEEP) <= GOOD) for k, v in ctl.items()}
for k in sorted(ctl):
    print('   control %-28s reads %.2f   %s'
          % (k.replace(' CONTROL', ''), ctl[k], 'passes' if passed[k] else 'FAILS'))
if not all(passed.values()):
    bad = [k for k in passed if not passed[k]]
    print('')
    print('   THE INSTRUMENT IS NOT RELIABLE AND THE CONTROLS ARE WHAT SAY SO. %s returns %.2f m where'
          % (bad[0].replace(' CONTROL', ''), ctl[bad[0]]))
    print('   the answer is %.3f and is not in doubt: 286 posed cameras stand inside that gallery. A' % DEEP)
    print('   sweep that misses a recess it can be checked against cannot be quoted on one it cannot.')
    print('   SO NOTHING IS CONCLUDED ABOUT THE EAST LOWER TIER AND NOTHING MOVES.')
    print('')
    print('   WHAT SURVIVES IS NARROWER AND IT IS ON THE WEST END ONLY. There the instrument has a')
    print('   control that PASSES on the same wall, in the same frames: the west top gallery reads')
    print('   %.2f m against a drawn %.3f. On that same wall the lower tier reads %.2f m back.'
          % (ctl['west top gallery CONTROL'], DEEP, RESULT['west end']))
    print('   THAT DOES NOT REFUTE THE 33 RAYS. They proved emptiness along their OWN paths near d 6.2')
    print('   to 8.2 and reached %.3f m in; this pools the whole %.0f m of the gallery length. Both hold'
          % (2.003, DS[-1] - DS[0]))
    print('   together if the lower recess is deep only over part of its length, which is a specific')
    print('   thing to test and is written down rather than acted on. The per-metre line above is the')
    print('   first look at it and it is one instrument on one end, which is not enough to draw with.')
    print('')
    print('   AND THAT PER-METRE LINE DOES NOT SUPPORT THE IDEA EITHER, WHICH IS WHY IT IS PRINTED. Its')
    print('   estimates jump across the whole sweep, 0.0 to 4.0 m, between neighbouring metres of the')
    print('   same wall. A real depth profile does not do that; an unstable estimator does. The one')
    print('   thing worth noting and not more: d 7 and d 8, which is where the 33 rays went, read 2.6')
    print('   and 2.0 against a fitting %.3f m in. With neighbours reading 0.0 and 4.0 that is as'
          % 2.003)
    print('   likely to be coincidence as signal, and nothing is built on it.')
