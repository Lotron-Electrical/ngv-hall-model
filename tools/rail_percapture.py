# 2026-09-10: THE RAIL TOP, ASKED OF EACH CAPTURE SEPARATELY, WHICH IS THE TEST THE LAST RUN NAMED.
#
# WHERE THIS COMES FROM AND WHY IT IS THE RIGHT NEXT STEP. tools/line_audit.py put every horizontal line
# in the balconies, walls and corridor through one measurement with a control on each end of the scale.
# The GLASS RAIL TOP came last of everything, east 0.73 and west 0.74, below all six INVENTED lines. Then
# tools/rail_sweep.py walked the whole balustrade with the solid upstand top inside the walk as a control:
# the control fired 3.66 times the sweep median east and 2.13 west, the drawn rail top read 0.89 and 0.64,
# below its own median on both faces, and the strongest height above the upstand came out deck plus 1.10
# east on 1.46 and deck plus 1.05 west on only 1.13. Two peaks 50 mm apart that could not agree either was
# real. That run refused to move anything and wrote down the test that would settle it, which is this one.
#
# WHY PER CAPTURE IS THE TEST AND NOT JUST MORE DATA. This project has moved exactly one level on a real
# measurement, the east parapet top, and it moved because four captures shot on different nights with
# different cameras were read one at a time and then compared: west settled within 21 mm across three
# captures, east agreed within 61 mm across four and moved +0.090. Pooling hides that. A pooled peak can
# be one capture shouting; four captures agreeing cannot be.
#
# THE DECISION RULE IS FIXED HERE, BEFORE THE RUN, so the result cannot be read to suit me. A face moves
# only if ALL THREE hold: at least 3 captures vote, their votes span less than 0.15 m, and the median vote
# differs from the drawn value by more than the 0.05 m sampling step. A capture only votes if its own
# control, the solid upstand top, fires above 1.25 times its own sweep median: a capture that cannot find
# the one edge known to be there does not get an opinion about one that might not be.
#
# WHAT IT STILL CANNOT DO. It measures where a step in brightness is, not what makes it. If the real rail
# has a metal cap the step is the cap; if it is frameless glass there may be no step to find and the right
# answer is that this is unmeasurable, which the run is allowed to return.
#   python tools/rail_percapture.py
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
# one entry per CAPTURE, with its re-gated pan variant folded in: they are the same footage
CAPTURES = [('walk', ('walk',)), ('night', ('night',)), ('day4k', ('day4k',)),
            ('b1', ('b1', 'b1p')), ('b3', ('b3', 'b3p')), ('b4', ('b4',)),
            ('b5', ('b5', 'b5p')), ('b7s', ('b7s', 'b7sp'))]
STEP = 0.06
VSTEP = 0.05
BAR = 1.25
MINR = 15
MINVOTES = 3
MAXSPAN = 0.15

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
print('the deck is drawn on h %.3f; each capture walks h %.2f to %.2f in %.0f mm steps'
      % (DECK, VS[0], VS[-1], 1000 * VSTEP))
print('a face moves only if %d or more captures vote, they span under %.2f m, and the median differs'
      % (MINVOTES, MAXSPAN))
print('from the drawn value by more than the %.0f mm step. That rule is fixed before the run.'
      % (1000 * VSTEP))


def sample(im, cam, uF, v):
    ts = np.linspace(1.0, DS - 1.0, 11)
    pts = np.array([O + uF * HU + t * HD + np.array([0.0, v, 0.0]) for t in ts])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
    if ok.sum() < 6:
        return None
    return np.array([float(im[int(y[i]), int(x[i])]) for i in np.nonzero(ok)[0]])


votes = {nm: [] for nm, _, _, _ in ENDS}
drawn_support = {nm: [] for nm, _, _, _ in ENDS}
for capname, classes in CAPTURES:
    acc = {nm: [[] for _ in VS] for nm, _, _, _ in ENDS}
    nf = 0
    for cname in classes:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cdd, cee = float(q @ HD), float(q[1])
            if not (-1.0 < cdd < DS + 1.0) or cee > 12.0:
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
    print('CAPTURE %s: %d frames' % (capname, nf))
    for nm, uF, rt, ups in ENDS:
        m = np.array([np.median(v) if len(v) >= MINR else np.nan for v in acc[nm]])
        g = np.isfinite(m)
        if g.sum() < 20:
            print('   %-5s  only %d of %d heights answered: this capture does not see this face'
                  % (nm, int(g.sum()), len(VS)))
            continue
        base = float(np.nanmedian(m))
        iu = int(np.argmin(np.abs(VS - (DECK + ups))))
        ir = int(np.argmin(np.abs(VS - (DECK + rt))))
        ctl = m[iu] / base if g[iu] else float('nan')
        dr = m[ir] / base if g[ir] else float('nan')
        hi_i = [i for i in range(len(VS)) if g[i] and VS[i] > DECK + ups + 0.25]
        if not np.isfinite(ctl) or ctl < BAR:
            print('   %-5s  control %s: NO VOTE, it cannot find the upstand top'
                  % (nm, '%.2f' % ctl if np.isfinite(ctl) else 'blank'))
            continue
        if not hi_i:
            print('   %-5s  control %.2f, but nothing above the upstand answered: NO VOTE' % (nm, ctl))
            continue
        j = max(hi_i, key=lambda i: m[i])
        sc = m[j] / base
        drawn_support[nm].append(dr)
        if sc < BAR:
            print('   %-5s  control %.2f  drawn rail %.2f  strongest above %.2f m on %.2f: UNDER THE BAR'
                  % (nm, ctl, dr, VS[j] - DECK, sc))
            continue
        votes[nm].append((capname, VS[j] - DECK, sc, ctl, dr))
        print('   %-5s  control %.2f  drawn rail %.2f  VOTES deck plus %.2f m on %.2f'
              % (nm, ctl, dr, VS[j] - DECK, sc))

print('')
moved = {}
for nm, uF, rt, ups in ENDS:
    vv = votes[nm]
    print('%s FACE: %d captures voted' % (nm.upper(), len(vv)))
    if drawn_support[nm]:
        print('   the DRAWN rail top scores %s across the captures that could look'
              % ', '.join('%.2f' % v for v in drawn_support[nm]))
    if len(vv) < MINVOTES:
        print('   FEWER THAN %d VOTES. Not enough captures can see an edge above this upstand, so this'
              % MINVOTES)
        print('   face is left exactly as drawn and the reason is recorded, not the number.')
        continue
    hs = np.array([t[1] for t in vv])
    span = float(hs.max() - hs.min())
    med = float(np.median(hs))
    print('   votes: %s' % ', '.join('%s %.2f' % (t[0], t[1]) for t in vv))
    print('   median deck plus %.3f m, span %.3f m, against a drawn %.3f' % (med, span, rt))
    if span >= MAXSPAN:
        print('   THE CAPTURES DO NOT AGREE: they span %.0f mm where the rule allows %.0f. That is the'
              % (1000 * span, 1000 * MAXSPAN))
        print('   same failure the old following instrument gave on the parapet before it was fixed, and')
        print('   it means these captures are not measuring one line. NOTHING MOVES on this face.')
        continue
    if abs(med - rt) <= VSTEP:
        print('   AND THEY AGREE WITH WHAT IS DRAWN, inside one sampling step. The drawn value is')
        print('   CONFIRMED by %d captures read one at a time, and its low audit score was the material')
        print('   and not the number.' % len(vv))
        continue
    moved[nm] = med
    print('   %d CAPTURES AGREE WITHIN %.0f mm ON deck plus %.3f, WHICH IS %+.0f mm FROM THE DRAWN %.3f.'
          % (len(vv), 1000 * span, med, 1000 * (med - rt), rt))
    print('   Every condition set before the run is met, so this face moves.')

print('')
if not moved:
    print('NOTHING MOVES. The rule was fixed before the run and it was not met, on either face.')
    sys.exit(0)
print('THE RULE IS MET ON: %s' % ', '.join('%s to %.3f' % (k, moved[k]) for k in sorted(moved)))
print('railTops becomes %s'
      % ', '.join('%s %.3f' % (nm, moved.get(nm, rt)) for nm, _, rt, _ in ENDS))
io.open('rail-vote.json', 'w', encoding='utf-8', newline='').write(
    '{%s}' % ', '.join('"%s": %.3f' % (k, moved[k]) for k in sorted(moved)))
print('wrote rail-vote.json for the patch step')
