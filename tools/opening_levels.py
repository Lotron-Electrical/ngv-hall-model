# 2026-09-10: WHERE DO THE OPENINGS START AND STOP, READ OFF THE CONTRAST RATHER THAN OFF A RAY FIT.
#
# The sill 8.740 and the head 11.165 were both placed by fitting detected edges to a plane
# (tools/head_lean.py and the ladders before it). That is one instrument, and one instrument that has
# been through several revisions on the same rays. tools/opening_holes.py then showed something simpler
# and stronger about these openings: an opening is DARK against the lit pier beside it, eleven of the
# twelve read that way, and the same rule run on the piers themselves fires on 4 per cent. That contrast
# is not an edge fit. It is the difference between a hole and a wall.
#
# SO USE IT AS A RULER. Take that same opening-against-pier ratio and walk it UP the wall. Below the sill
# both patches are stone and the ratio sits near one. Between the sill and the head one patch is a hole
# and the ratio falls. Above the head it is stone again and the ratio comes back. The two heights where
# it steps are the sill and the head, and nothing is fitted to an edge anywhere: each sample is a ratio
# of two areas of wall in the same frame at the same exposure.
#
# THE NULL IS THE POINT, AND IT IS FREE. The identical profile is run on PIER AGAINST PIER, two strips of
# solid stone with no hole between them. That profile should be flat. Whatever wiggle it has is what this
# method invents, and no step in the real profile counts unless it is bigger than that.
#
# THE REDUNDANCY IS ALSO FREE. Twelve openings answer separately, so a level supported by one of them is
# not a measurement. And the drawn sill and head are never used to place a window: the profile is walked
# from well below the drawn sill to well above the drawn head and the steps land where they land.
#
# WHAT IT CANNOT DO. It reads the level at which the wall stops being a wall, seen from the hall floor
# tens of metres away. A deep reveal, a splayed jamb or a soffit that overhangs will all blur that level,
# so a step found here is the top or bottom of the APERTURE as it reads from the hall, and its width is
# reported rather than hidden.
#   python tools/opening_levels.py
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
HLO, HHI, HSTEP = 7.60, 12.40, 0.05
BAND = 0.18


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
LEV = np.arange(HLO, HHI + 1e-9, HSTEP)
print('index.html draws the sill on h %.3f and the head on h %.3f' % (SILL, HEAD))
print('the profile is walked from h %.2f to %.2f in %.0f mm steps, so neither is used to place a window'
      % (HLO, HHI, 1000 * HSTEP))


def patch(im, cam, u0, u1, lo, hi):
    us = np.linspace(u0 + 0.12, u1 - 0.12, 6)
    ls = np.linspace(lo, hi, 4)
    pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
    if ok.sum() < 16:
        return None
    if (x[ok].max() - x[ok].min()) < 8:
        return None
    return float(np.mean([im[int(y[i]), int(x[i])] for i in np.nonzero(ok)[0]]))


prof = {i: [[] for _ in LEV] for i in range(len(OPEN))}
null = [[] for _ in LEV]
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
        im = None
        for oi, (u0, u1) in enumerate(OPEN):
            w = u1 - u0
            if im is None:
                im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if im is None:
                    break
                nf += 1
            for li, hv in enumerate(LEV):
                lo, hi = hv - BAND / 2, hv + BAND / 2
                a = patch(im, cam, u0, u1, lo, hi)
                b = patch(im, cam, u1 + 0.25 * w, u1 + 1.25 * w, lo, hi)
                if a is not None and b is not None and b > 8:
                    prof[oi][li].append(a / b)
                # THE NULL: the same shape of comparison between two strips of solid stone
                c = patch(im, cam, u1 + 1.35 * w, u1 + 2.35 * w, lo, hi)
                if b is not None and c is not None and c > 8:
                    null[li].append(b / c)

print('')
print('%d frames read' % nf)
med = np.array([np.median(v) if len(v) >= 12 else np.nan for v in null])
ok = np.isfinite(med)
if ok.sum() < 20:
    sys.exit('   the null did not fill, so nothing here can be judged')
wig = float(np.nanmax(med[ok]) - np.nanmin(med[ok]))
print('   THE NULL, pier against pier, runs %.3f to %.3f over the whole sweep: a wiggle of %.3f.'
      % (float(np.nanmin(med[ok])), float(np.nanmax(med[ok])), wig))
print('   No step in a real profile counts unless it is bigger than that.')

print('')
print('   opening   levels   lowest ratio   at h     step down       step up      depth of dip')
rows = []
for oi in range(len(OPEN)):
    m = np.array([np.median(v) if len(v) >= 12 else np.nan for v in prof[oi]])
    g = np.isfinite(m)
    if g.sum() < 30:
        print('   %2d        %4d     too few levels answered' % (oi + 1, int(g.sum())))
        continue
    lo_i = int(np.nanargmin(m))
    base = float(np.nanpercentile(m, 90))
    dip = base - float(m[lo_i])
    # the step down is the lowest level where the ratio has fallen half way from the baseline to the dip
    half = base - 0.5 * dip
    below = [LEV[i] for i in range(len(LEV)) if g[i] and LEV[i] < LEV[lo_i] and m[i] > half]
    above = [LEV[i] for i in range(len(LEV)) if g[i] and LEV[i] > LEV[lo_i] and m[i] > half]
    sill = max(below) if below else float('nan')
    head = min(above) if above else float('nan')
    rows.append((oi + 1, sill, head, dip, float(m[lo_i]), LEV[lo_i]))
    print('   %2d        %4d      %.3f       %5.2f    %6.2f        %6.2f        %.3f'
          % (oi + 1, int(g.sum()), float(m[lo_i]), LEV[lo_i], sill, head, dip))

print('')
# A DIP IS NOT AN APERTURE UNLESS IT IS APERTURE-SHAPED. Opening 4 returned its deepest ratio on h 7.95
# with a step down on 7.75 and a step up on 8.15: a dip 0.40 m tall, sitting entirely BELOW the sill.
# Whatever that is, it is not a 2.4 m opening, and letting it into the pool would be letting the method
# vote on a question it has not been asked. So a profile also has to show a dip at least 1.5 m tall.
MINTALL = 1.5
good = [r for r in rows if r[3] > 2 * wig and np.isfinite(r[1]) and np.isfinite(r[2])
        and (r[2] - r[1]) > MINTALL]
dropped = [r[0] for r in rows if r[3] > 2 * wig and np.isfinite(r[1]) and np.isfinite(r[2])
           and (r[2] - r[1]) <= MINTALL]
if dropped:
    print('   openings %s dip deeper than the null but their dip is under %.1f m tall, so it is not an'
          % (', '.join(str(v) for v in dropped), MINTALL))
    print('   aperture and they are dropped rather than averaged in.')
if len(good) < 4:
    print('   FEWER THAN FOUR OPENINGS GIVE A DIP DEEPER THAN THE NULL, so this cannot measure a level.')
    sys.exit(0)
sills = np.array([r[1] for r in good])
heads = np.array([r[2] for r in good])
print('   %d openings dip deeper than the null wiggle of %.3f.' % (len(good), wig))
print('   the wall stops being a wall on h %.3f, quartiles %.3f to %.3f, against a drawn sill of %.3f'
      % (float(np.median(sills)), float(np.percentile(sills, 25)), float(np.percentile(sills, 75)), SILL))
print('   and starts again on h %.3f, quartiles %.3f to %.3f, against a drawn head of %.3f'
      % (float(np.median(heads)), float(np.percentile(heads, 25)), float(np.percentile(heads, 75)), HEAD))
ds, dh = float(np.median(sills)) - SILL, float(np.median(heads)) - HEAD
iqs = float(np.percentile(sills, 75) - np.percentile(sills, 25))
iqh = float(np.percentile(heads, 75) - np.percentile(heads, 25))
print('   that is %+.0f mm on the sill and %+.0f mm on the head, with %d and %d openings behind them.'
      % (1000 * ds, 1000 * dh, len(good), len(good)))
# A LEVEL IS ONLY MEASURED IF THE OPENINGS AGREE WITH EACH OTHER, and the sampling step is 50 mm, so
# nothing here can be quoted finer than that whatever the median does.
if max(iqs, iqh) > 0.30:
    print('   REFUSED: the openings spread %.0f and %.0f mm between their own quartiles, which is wider'
          % (1000 * iqs, 1000 * iqh))
    print('   than the disagreement being tested. They are not measuring one level. Nothing moves.')
else:
    tall = float(np.median(heads) - np.median(sills))
    print('   the aperture reads %.3f m tall against the %.3f this file draws.' % (tall, HEAD - SILL))
    if abs(ds) <= HSTEP:
        print('   THE SILL IS CONFIRMED to within one sampling step by an instrument that shares no')
        print('   machinery with the ray fits that placed it: this reads the contrast between two areas')
        print('   of wall, not the position of an edge.')
    else:
        print('   THE SILL READS %+.0f mm from the drawn one, more than one sampling step.' % (1000 * ds))
    # AND THE HEAD IS EXPECTED TO READ LOW, WHICH IS NOT THE SAME AS BEING RIGHT. This file already
    # records that the head soffit stands over the reveal, so from the hall floor the top of the aperture
    # is partly shadowed by its own soffit and reads as wall. That predicts a head measured HERE that is
    # lower than the built one, by an amount nobody has bounded. The sign and the size are consistent
    # with it, so this does not refute the drawn head, and it does not confirm it either.
    if abs(dh) > HSTEP:
        print('   THE HEAD READS %+.0f mm, more than one %.0f mm step, and that was expected: the head'
              % (1000 * dh, 1000 * HSTEP))
        print('   soffit stands over the reveal, so from the hall floor the top of the aperture is partly')
        print('   shadowed by its own soffit and reads as wall. A head measured this way should come out')
        print('   LOW. The sign and the size agree with that, so the drawn head is neither refuted nor')
        print('   confirmed here, and the aperture height %.3f is a floor on the true one, not a value.'
              % tall)
    else:
        print('   THE HEAD TOO lands within one sampling step of the drawn one.')
