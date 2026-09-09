# 2026-09-09: THE NORTH OPENINGS WITH THE FOLLOW GAIN FITTED, not assumed.
#
# The twelve openings in this wall were positioned by a jamb finder that starts from the drawn jamb and
# walks to the nearest strong edge. That instrument partly reproduces what it was given. The bias was
# known and handled by measuring the gain in a separate experiment (0.70 before the fixed-point finder,
# 0.37 after) and then treating the reading as a lower bound.
#
# That is not good enough, and the parapet showed why: run the same reasoning on the end galleries and the
# four captures that "agreed within 61 mm" turned out to be agreeing about the DRAWING, because at a gain
# near 0.7 an instrument mostly reproduces whatever it is given and every capture had been given the same
# table. The correction is to stop assuming the gain and fit it, which is possible because a following
# instrument is LINEAR in the drawn position:
#     A(d) = truth + g * (d - truth) = (1 - g) * truth + g * d
# so reading the SAME physical jamb against three drawn tables, slid along the wall by a known amount, gives
# the gain as the slope and the truth as the intercept. Sliding the WHOLE table keeps every spacing, so the
# separability test and the search window do not move and the only thing that changes is where the search
# starts, which is exactly the variable under test.
#
# THE SHIFTS ARE PLUS AND MINUS 0.10 m. Wide enough that a 0.02 m read error becomes 0.1 of gain rather
# than the 0.22 that made the first parapet attempt return an impossible 1.58, and narrow enough that the
# 0.25 m search window still contains the real jamb at every draw.
#
# WHAT IS REPORTED PER JAMB: the fitted gain, the residual about the line (a check on linearity, since
# nothing forces a real instrument to be linear), and the truth. A gain outside 0 to 0.85 is a refusal, not
# a disagreement: an instrument cannot move further than the drawing moved or against it, so a jamb that
# reports one is noise. Then the SHIFT per opening, pooled across captures, because this wall is twelve
# identical windows and the thing that varies is where an opening stands, not how wide it is.
#   python tools/wall_gainfit.py            (after tools/wall_gainfit.sh has written the json)
import json
import os

import numpy as np

D = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/walljson'
DRAWS = [('m', -0.10), ('z', 0.0), ('p', 0.10)]
CAPS = ['walk', 'night', 'day4k', 'b1', 'b3', 'b7s', 'b1p', 'b5p']


def load(tag, cap):
    p = os.path.join(D, 'gain-%s-%s.json' % (tag, cap))
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))['jambs']
    except Exception:
        return None


shifts = {}
print('per capture, the jambs whose gain could be fitted')
for cap in CAPS:
    js = [load(t, cap) for t, _ in DRAWS]
    if any(x is None for x in js):
        print(' ', cap, 'did not produce all three draws')
        continue
    common = set(js[0]).intersection(js[1]).intersection(js[2])
    names = sorted(common)
    good = []
    for nm in names:
        dv = np.array([js[k][nm]['u'] for k in range(3)])
        av = np.array([js[k][nm]['u'] + js[k][nm]['median'] for k in range(3)])
        if dv.max() - dv.min() < 0.15:
            continue
        g, c = np.polyfit(dv, av, 1)
        resid = float(np.abs(av - (g * dv + c)).max())
        if not (0.0 <= g <= 0.85) or resid > 0.04:
            continue
        truth = float(c / (1.0 - g))
        drawn = float(js[1][nm]['u'])
        good.append((nm, int(js[1][nm]['opening']), float(g), truth - drawn, resid))
    print(' ', cap, len(good), 'of', len(names), 'jambs fitted cleanly')
    for nm, oi, g, off, resid in good:
        print('     ', nm, 'gain', round(g, 2), 'resid', round(resid, 3), 'stands', round(off, 3), 'm off')
        shifts.setdefault(oi, []).append((cap, off))

print('')
print('POOLED PER OPENING, one number per capture')
for oi in sorted(shifts):
    per = {}
    for cap, off in shifts[oi]:
        per.setdefault(cap, []).append(off)
    # an opening states its shift as the mean of whichever of its two jambs that capture resolved, because
    # both jambs of a real opening move together and most of the reading error is common to them
    vals = [(cap, float(np.mean(v))) for cap, v in per.items()]
    if len(vals) < 2:
        print(' opening', oi + 1, 'only', len(vals), 'capture, not pooled:',
              [(c, round(v, 3)) for c, v in vals])
        continue
    arr = np.array([v for _, v in vals])
    settled = abs(float(np.median(arr))) > 0.05 and float(arr.max() - arr.min()) <= 0.08
    print(' opening', oi + 1, len(vals), 'captures median', round(float(np.median(arr)), 3),
          'range', round(float(arr.max() - arr.min()), 3), 'MOVES' if settled else 'not resolved',
          [(c, round(v, 3)) for c, v in vals])
