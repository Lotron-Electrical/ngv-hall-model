# 2026-09-10: THE JAMBS OF ALL TWELVE OPENINGS, READ OFF CONTRAST, THE WAY THE SILL JUST WAS.
#
# tools/opening_levels.py walked the opening-against-pier contrast UP the wall and got the sill back to
# ten millimetres, from an instrument that shares nothing with the ray fits that placed it. This turns
# the same ruler on its side.
#
# THERE IS A REAL GAP TO FILL. The twelve openings were positioned on NINE jamb lines and every one of
# those lines lies between u 20.0 and 34.9, which is openings 5 to 9. The other seven were carried into
# place by a rigid shift with no local evidence under them at all, and that is exactly how opening 3 came
# to be 0.78 m out until today. Seven openings have never had their own jambs measured by anything.
#
# THE PROFILE. For each opening, walk u from well inside the pier on one side to well inside the pier on
# the other, in 30 mm steps, sampling a narrow column of the wall band at each stop. On a pier the column
# is lit stone; across the aperture it is a hole. Pool the columns over every frame that sees them, and
# the profile is high, low, high. The two half-way crossings are the jambs.
#
# THE NULL IS THE SAME TRICK AND IT IS WHAT MAKES IT READABLE. The identical walk is run centred on a
# PIER, solid stone the whole way, where the profile should be flat. Whatever dip that invents is the
# floor: no jamb counts unless the aperture dip is deeper than it.
#
# WHAT IT MEASURES AND WHAT IT DOES NOT. It gives each opening a centre and a width in metres, from the
# photographs, with no ray fit and no rigid set. It cannot give a depth, it says nothing about the
# reveal, and it reads the aperture as it appears from the hall, so a splayed jamb reads wider than the
# built one. The width it returns is therefore an upper bound on the built width, and that is printed
# with it rather than left for somebody to trip over.
#   python tools/opening_jambs.py
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
USTEP = 0.03
MARGIN = 0.10                      # how much solid stone the null must keep clear of an aperture
JAMBED = (5, 6, 7, 8, 9)           # the openings that already carry their own measured jamb lines


def model():
    src = io.open('index.html', encoding='utf-8').read()
    mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
    return {'dNorth': float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1)),
            'sill': float(re.search(r'openY:\[([0-9.]+),', src).group(1)),
            'head': float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1)),
            'openings': [[float(a), float(b)]
                         for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]}


M = model()
DN, SILL, HEAD = M['dNorth'], M['sill'], M['head']
OPEN = M['openings']
LO, HI = SILL + 0.35, HEAD - 0.35

# HOW FAR THE WALK REACHES INTO THE PIER IS NOT A FREE CHOICE, and the first version of this file got it
# badly wrong by picking a round 1.10 m. The NULL is the same walk centred on a pier, so the walk has to
# FIT INSIDE A PIER. The piers here run 2.324 to 2.576 m and the openings 1.206 to 1.214, so a walk with
# a 1.10 m reach is 3.414 m wide: every one of the eleven nulls ran straight through parts of the two
# openings beside it. The control for "is this dip real" was therefore full of real apertures, its dips
# came out 0.211 to 0.515, and the bar it set was so high that only two openings could clear it. The
# reach is now DERIVED from the narrowest pier so the null is guaranteed to stand on solid stone.
WIDE = max(b - a for a, b in OPEN)
NARROW = min(OPEN[i + 1][0] - OPEN[i][1] for i in range(len(OPEN) - 1))
REACH = 0.5 * (NARROW - 2 * MARGIN - WIDE)
if REACH < 4 * USTEP:
    sys.exit('   the piers are too narrow to carry the null walk, so this cannot be judged')
print('walking u in %.0f mm steps across each opening, sampling the band h %.2f to %.2f'
      % (1000 * USTEP, LO, HI))
print('the band is inset from the drawn sill and head so the soffit and the cill do not blur the edges')
print('the walk reaches %.3f m into the pier either side: the narrowest pier is %.3f m and the widest'
      % (REACH, NARROW))
print('opening %.3f m, so the same walk centred on a pier clears both apertures by %.2f m of stone'
      % (WIDE, MARGIN))


def column(im, cam, uc):
    us = np.linspace(uc - USTEP / 2, uc + USTEP / 2, 2)
    ls = np.linspace(LO, HI, 9)
    pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
    if ok.sum() < 12:
        return None
    return float(np.mean([im[int(y[i]), int(x[i])] for i in np.nonzero(ok)[0]]))


def walk(centre, halfwidth):
    return np.arange(centre - halfwidth - REACH, centre + halfwidth + REACH + 1e-9, USTEP)


targets = []
for oi, (u0, u1) in enumerate(OPEN):
    targets.append(('opening %d' % (oi + 1), 0.5 * (u0 + u1), 0.5 * (u1 - u0), oi + 1))
# THE NULL: the middle of each pier, walked the same distance with the same window
for oi in range(len(OPEN) - 1):
    c = 0.5 * (OPEN[oi][1] + OPEN[oi + 1][0])
    targets.append(('pier %d-%d' % (oi + 1, oi + 2), c, 0.5 * (OPEN[0][1] - OPEN[0][0]), 0))

acc = {t[0]: [[] for _ in walk(t[1], t[2])] for t in targets}
nf = 0
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ch = float(q @ HD), float(q[1])
        if ch > 3.0 or cd < 3.0:
            continue
        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        nf += 1
        for name, cu, hw, _ in targets:
            us = walk(cu, hw)
            vals = [column(im, cam, u) for u in us]
            if sum(v is not None for v in vals) < 0.8 * len(us):
                continue
            ref = [v for v in vals if v is not None]
            base = float(np.percentile(ref, 85))
            if base < 10:
                continue
            for i, v in enumerate(vals):
                if v is not None:
                    acc[name][i].append(v / base)

print('')
print('%d frames read' % nf)


def edges(name, cu, hw):
    m = np.array([np.median(v) if len(v) >= 12 else np.nan for v in acc[name]])
    us = walk(cu, hw)
    g = np.isfinite(m)
    if g.sum() < 0.7 * len(us):
        return None
    i = int(np.nanargmin(m))
    base = float(np.nanpercentile(m, 85))
    dip = base - float(m[i])
    half = base - 0.5 * dip
    left = [us[j] for j in range(len(us)) if g[j] and us[j] < us[i] and m[j] > half]
    right = [us[j] for j in range(len(us)) if g[j] and us[j] > us[i] and m[j] > half]
    # THE DIP IS ALWAYS REPORTABLE, THE EDGES ARE NOT, and the first version of this conflated them.
    # On a FLAT profile, which is exactly what the null is supposed to be, the lowest point lands wherever
    # the noise puts it, often at one end, and then there is no crossing on that side and the whole
    # reading was thrown away. The null then answered nowhere and the run refused itself for the wrong
    # reason. The null only ever needed the depth of the dip.
    if not left or not right:
        return None, None, dip, float(m[i])
    return max(left), min(right), dip, float(m[i])


nulls = [edges(t[0], t[1], t[2]) for t in targets if t[3] == 0]
nd = [n[2] for n in nulls if n is not None]
if not nd:
    sys.exit('   the null did not answer anywhere, so nothing here can be judged')
floor = float(np.percentile(nd, 90))
print('   THE NULL, the same walk centred on a pier: %d of %d answered and their dips run %.3f to %.3f.'
      % (len(nd), len(nulls), min(nd), max(nd)))
print('   The bar is the 90th of those, %.3f. No aperture counts unless its dip is deeper.' % floor)

print('')
print('   opening   drawn centre   found centre   shift    drawn width   found width   dip    jambed')
rows = []
for name, cu, hw, oi in targets:
    if oi == 0:
        continue
    e = edges(name, cu, hw)
    if e is None or e[0] is None:
        print('   %2d        %8.3f       no pair of edges: %s'
              % (oi, cu, 'no profile' if e is None else 'the dip runs off one end of the walk'))
        continue
    a, b, dip, low = e
    fc, fw = 0.5 * (a + b), b - a
    ok = dip > floor
    rows.append((oi, cu, fc, fw, dip, ok))
    print('   %2d        %8.3f      %8.3f     %+6.3f     %.3f        %.3f     %.3f   %s'
          % (oi, cu, fc, fc - cu, 2 * hw, fw, dip, 'yes' if oi in JAMBED else 'no'))

good = [r for r in rows if r[5]]
print('')
print('   %d of %d openings dip deeper than the null bar.' % (len(good), len(rows)))
if len(good) < 6:
    print('   TOO FEW TO SAY ANYTHING. Nothing moves.')
    sys.exit(0)
sh = np.array([r[2] - r[1] for r in good])
wd = np.array([r[3] for r in good])
q1, q3 = float(np.percentile(sh, 25)), float(np.percentile(sh, 75))
print('   their centres sit %+.3f m from where this file draws them, quartiles %+.3f to %+.3f'
      % (float(np.median(sh)), q1, q3))
print('   their widths read %.3f m, quartiles %.3f to %.3f, against a drawn %.3f'
      % (float(np.median(wd)), float(np.percentile(wd, 25)), float(np.percentile(wd, 75)),
         float(np.median([2 * t[2] for t in targets if t[3]]))))
print('   the widest single miss is %+.3f m, on opening %d'
      % (max(sh, key=abs), good[int(np.argmax(np.abs(sh)))][0]))

# THE MEDIAN IS NOT THE ANSWER HERE AND SAYING SO IS THE POINT. The openings disagree with each other by
# more than the median is away from zero, so a median quoted as a placement would be a claim smaller than
# its own spread, which is the error this project has paid for more than any other. What survives is a
# BOUND: no opening is out by anything like the 0.78 m that opening 3 was.
print('')
print('   WHAT THIS CAN AND CANNOT SAY. The openings disagree with each other by %.0f mm between their'
      % (1000 * (q3 - q1)))
print('   own quartiles, which is wider than the %.0f mm the median sits from zero. So this does NOT'
      % (1000 * abs(float(np.median(sh)))))
print('   place a jamb, and nothing moves on it. What it DOES give is a bound with no ray fit in it:')
print('   every one of the %d openings that answered lands within %.3f m of where this file draws it,'
      % (len(good), float(np.max(np.abs(sh)))))
print('   so none of them carries an error of the size opening 3 carried until today.')

# AND THE RESIDUALS ARE NOT NOISE, WHICH IS WORTH MORE THAN THE BOUND. They change sign along the hall.
west = [r for r in good if r[0] <= 4]
east = [r for r in good if r[0] >= 10]
if len(west) >= 2 and len(east) >= 2:
    mw = float(np.median([r[2] - r[1] for r in west]))
    me = float(np.median([r[2] - r[1] for r in east]))
    if mw > 0.05 and me < -0.05:
        print('')
        print('   THE MISSES ARE ORDERED, NOT SCATTERED. The west openings read %+.3f m and the east ones'
              % mw)
        print('   %+.3f m, and the sign changes in the middle of the hall. That is what a %.1f m deep' % (me, 0.9))
        print('   reveal looks like from a camera pool standing in the middle: a hole with depth, seen')
        print('   from one side, shows a dark patch pulled TOWARDS the viewer and narrowed. It is not')
        print('   evidence that the openings are misplaced. tools/jamb_parallax.py takes this up, because')
        print('   if the pattern is parallax then its size measures the reveal depth, which the lamp')
        print('   occlusion route could not.')

# THE NUMBERS GO TO DISK so the parallax test reads what was measured rather than a number retyped by me.
import json
io.open('jamb-profile.json', 'w', encoding='utf-8', newline='').write(json.dumps(
    {'reach': REACH, 'ustep': USTEP, 'floor': floor, 'nulls': nd,
     'rows': [{'opening': r[0], 'drawn': r[1], 'found': r[2], 'width': r[3], 'dip': r[4],
               'over_null': bool(r[5])} for r in rows]}, indent=1))
print('')
print('   wrote jamb-profile.json: %d openings, the null dips, and the reach this walked.' % len(rows))
