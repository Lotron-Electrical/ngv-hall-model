# 2026-09-10: IS THERE AN EDGE ANYWHERE ON THE BALUSTRADE, OR IS GLASS SIMPLY NOT MEASURABLE THIS WAY?
#
# WHERE THIS COMES FROM. tools/line_audit.py put every horizontal line in the balconies, walls and
# corridor through one measurement with a control at each end of the scale. Six INVENTED lines, heights
# where this file draws nothing, scored 0.83 to 0.97. The two solid upstand tops, the lines this project
# has always said are the only balcony lines the floor imagery can resolve, scored 3.11 and 1.46. And the
# two GLASS RAIL TOPS came LAST of everything, on 0.73 and 0.74: lower than lines I made up.
#
# THAT IS NOT YET A FAULT, WHICH IS WHY THIS RUN EXISTS. Glass has no tone of its own, so a glass top edge
# may leave no step for anything to find, and then a low score is a property of the material rather than
# of the number. There are two ways that can go and they need separating: EITHER no height anywhere on
# that face reads as an edge above the upstand, in which case the rail top cannot be measured this way and
# the route closes properly; OR some height does, and then the drawn one is in the wrong place.
#
# THE CONTROL IS INSIDE THE SWEEP AND COSTS NOTHING. The walk starts BELOW the solid upstand top and ends
# above the rail. The upstand top is opaque stone, and line_audit scored it 3.11 on the east. It must come
# back as a peak here. If the sweep cannot find the one edge on this face that is known to exist, it
# cannot be trusted to report that another is missing.
#   python tools/rail_sweep.py
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
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b1p', 'b3', 'b3p', 'b4', 'b5', 'b5p', 'b7s', 'b7sp')
STEP = 0.06
VSTEP = 0.05

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(key):
    return float(re.search(r'\b' + key + r':\s*(-?[0-9.]+)', BLOCK).group(1))


DS = endw('dSouth')
DECK = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1))
WFACE, EFACE = endw('west') + endw('face'), endw('east') - endw('face')
RT = re.search(r'railTops:\{west:([0-9.]+), *east:([0-9.]+)\}', BLOCK)
UPS = re.search(r'upstands:\{west:([0-9.]+), *east:([0-9.]+)\}', BLOCK)
ENDS = (('west', WFACE, float(RT.group(1)), float(UPS.group(1))),
        ('east', EFACE, float(RT.group(2)), float(UPS.group(2))))
VS = np.arange(DECK + 0.30, DECK + 2.30 + 1e-9, VSTEP)
print('the deck is drawn on h %.3f; the walk runs h %.2f to %.2f in %.0f mm steps'
      % (DECK, VS[0], VS[-1], 1000 * VSTEP))
for nm, uF, rt, ups in ENDS:
    print('   %s: solid upstand top drawn on h %.3f, glass rail top on h %.3f'
          % (nm, DECK + ups, DECK + rt))


def sample(im, cam, uF, v):
    ts = np.linspace(1.0, DS - 1.0, 11)
    pts = np.array([O + uF * HU + t * HD + np.array([0.0, v, 0.0]) for t in ts])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
    if ok.sum() < 6:
        return None
    return np.array([float(im[int(y[i]), int(x[i])]) for i in np.nonzero(ok)[0]])


acc = {nm: [[] for _ in VS] for nm, _, _, _ in ENDS}
nf = 0
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ce = float(q @ HD), float(q[1])
        if not (-1.0 < cd < DS + 1.0) or ce > 12.0:
            continue
        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        nf += 1
        for nm, uF, rt, ups in ENDS:
            for i, v in enumerate(VS):
                above = sample(im, cam, uF, v + STEP)
                below = sample(im, cam, uF, v - STEP)
                if above is None or below is None:
                    continue
                n = min(len(above), len(below))
                mu = 0.5 * (float(np.mean(above[:n])) + float(np.mean(below[:n])))
                if mu < 8:
                    continue
                acc[nm][i].append(float(np.mean(np.abs(above[:n] - below[:n]))) / mu)

print('')
print('%d frames read' % nf)
for nm, uF, rt, ups in ENDS:
    m = np.array([np.median(v) if len(v) >= 40 else np.nan for v in acc[nm]])
    g = np.isfinite(m)
    print('')
    print('%s END: %d of %d heights answered' % (nm.upper(), int(g.sum()), len(VS)))
    if g.sum() < 20:
        print('   too few heights answered to sweep this face')
        continue
    base = float(np.nanmedian(m))
    print('   h      step     against the sweep median %.4f' % base)
    for i, v in enumerate(VS):
        if not g[i]:
            continue
        mark = ''
        if abs(v - (DECK + ups)) < VSTEP / 2:
            mark = '  <- solid upstand top, the control'
        if abs(v - (DECK + rt)) < VSTEP / 2:
            mark = '  <- glass rail top as drawn'
        bar = '#' * int(round(30 * m[i] / max(base * 2.2, 1e-6)))
        print('   %5.2f  %.4f  %-32s%s' % (v, m[i], bar, mark))
    iu = int(np.argmin(np.abs(VS - (DECK + ups))))
    ir = int(np.argmin(np.abs(VS - (DECK + rt))))
    ctl = m[iu] / base if g[iu] else float('nan')
    drawn = m[ir] / base if g[ir] else float('nan')
    peak = int(np.nanargmax(m))
    print('   the control, the solid upstand top, reads %.2f times the sweep median.' % ctl)
    if not np.isfinite(ctl) or ctl < 1.25:
        print('   THE CONTROL FAILS ON THIS FACE: the one edge here that is known to exist does not come')
        print('   back as a peak, so this sweep cannot report that another edge is missing. NOTHING.')
        continue
    print('   the drawn glass rail top reads %.2f times the median, and the strongest height in the'
          % drawn)
    print('   whole walk is h %.2f on %.2f times the median.' % (VS[peak], m[peak] / base))
    above_up = [i for i in range(len(VS)) if g[i] and VS[i] > DECK + ups + 0.25]
    if not above_up:
        print('   nothing above the upstand answered.')
        continue
    ja = max(above_up, key=lambda i: m[i])
    print('   ABOVE the upstand, the strongest height is h %.2f on %.2f times the median.'
          % (VS[ja], m[ja] / base))
    if m[ja] / base < 1.25:
        print('   NO HEIGHT ABOVE THE UPSTAND READS AS AN EDGE ON THIS FACE. The control works and finds')
        print('   the stone, and there is nothing for it to find higher up. That is what a GLASS rail')
        print('   looks like to this instrument: no tone of its own, so no step. The rail top cannot be')
        print('   measured this way, on this face, and its low score in the audit is a property of the')
        print('   material and NOT evidence that the number is wrong. Route closed, reason attached.')
    elif abs(VS[ja] - (DECK + rt)) < 0.15:
        print('   AND IT IS WHERE THIS FILE DRAWS THE RAIL, to within %.0f mm. The drawn value is'
              % (1000 * abs(VS[ja] - (DECK + rt))))
        print('   supported after all, and the audit score was the material rather than the number.')
    else:
        print('   AND IT IS NOT WHERE THIS FILE DRAWS THE RAIL: %.2f m above the deck against a drawn'
              % (VS[ja] - DECK))
        print('   %.3f, a difference of %.0f mm. That is a candidate and not a correction, because one'
              % (rt, 1000 * abs(VS[ja] - DECK - rt)))
        print('   peak on one face is not a measurement. It is the first positive thing anything has')
        print('   said about this number, and it is written down for the run that tests it properly.')
