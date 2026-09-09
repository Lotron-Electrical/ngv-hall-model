# 2026-09-09: THE OPENINGS' SILL AND HEAD WITH THE FOLLOW GAIN FITTED, not assumed.
#
# openY [8.99, 11.35] was tested for the first time this morning with an instrument whose follow bias was
# measured separately and then assumed to be the same everywhere. Two later results showed that assumption
# is not safe: on the end galleries four captures "agreeing within 61 mm" were agreeing about the drawing,
# and on the north jambs the fitted gain turns out to vary from 0.00 to 0.81 between jambs and captures.
# So the sill and the head get the same treatment. A following instrument is linear in the drawn height,
# A(d) = truth + g(d - truth), so reading the same physical edge against three shifted draws gives the gain
# as the slope and the truth as the intercept.
#
# THIS ONE IS HARD AND THE REASON IS THE STONE. The search window here is 0.14 m, half a bluestone course,
# because the coursing is measured (0.304 m, north bed joints h = 0.080 + 0.304k) and a real bed joint
# therefore sits within 0.152 m of ANY height on this face. Search wider and the finder grabs a course line
# instead of the opening. That caps the draw separation at about 0.12 m, a sixth of what the jambs could
# use, so the slope is six times noisier and most jambs will refuse rather than answer. A refusal here is
# the honest outcome, not a failure: the alternative is a tight number that is really the coursing.
#
# TWO THINGS ARE REPORTED. The per-edge fit, and then the SILL-TO-HEAD SPAN, head minus sill, which is a
# different quantity from either edge's position and is much better conditioned: a follow bias that pulls
# both edges the same way cancels out of their difference entirely. If the span comes back near the drawn
# 2.36 m while the individual edges refuse, that is still a real statement about the wall.
#   python tools/openy_gainfit.py           (after tools/openy_gainfit.sh has written the json)
import json
import os

import numpy as np

D = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/openjson'
DRAWS = [('m', -0.06), ('z', 0.0), ('p', 0.06)]
CAPS = ['walk', 'night', 'day4k', 'b1', 'b3', 'b7s', 'b1p', 'b5p']
DRAWN_SILL = 8.99
DRAWN_HEAD = 11.35


def load(tag, cap):
    p = os.path.join(D, 'gain-%s-%s.json' % (tag, cap))
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))['levels']
    except Exception:
        return None


def fit(dv, av):
    g, c = np.polyfit(dv, av, 1)
    resid = float(np.abs(av - (g * dv + c)).max())
    if not (0.0 <= g <= 0.85) or resid > 0.03:
        return None
    return float(g), float(c / (1.0 - g)), resid


edges = {}
spans = {}
print('per capture, the edges whose gain could be fitted')
for cap in CAPS:
    js = [load(t, cap) for t, _ in DRAWS]
    if any(x is None for x in js):
        print(' ', cap, 'did not produce all three draws')
        continue
    names = sorted(set(js[0]).intersection(js[1]).intersection(js[2]))
    got = 0
    truth = {}
    for nm in names:
        dv = np.array([js[k][nm]['h'] for k in range(3)])
        av = np.array([js[k][nm]['h'] + js[k][nm]['median'] for k in range(3)])
        if dv.max() - dv.min() < 0.08:
            continue
        f = fit(dv, av)
        if f is None:
            continue
        g, tr, resid = f
        got += 1
        drawn = DRAWN_SILL if nm.startswith('sill') else DRAWN_HEAD
        edges.setdefault(nm, []).append((cap, tr - drawn, g))
        truth[nm] = tr
        print('     ', nm, 'gain', round(g, 2), 'resid', round(resid, 3), 'stands', round(tr - drawn, 3), 'm off')
    print(' ', cap, got, 'of', len(names), 'edges fitted cleanly')
    for k in range(1, 13):
        s, h = 'sill-%d' % k, 'head-%d' % k
        if s in truth and h in truth:
            spans.setdefault(k, []).append((cap, truth[h] - truth[s]))

print('')
print('POOLED PER EDGE, one number per capture, against the drawn sill 8.99 and head 11.35')
for nm in sorted(edges):
    vals = edges[nm]
    arr = np.array([v for _, v, _ in vals])
    if len(vals) < 2:
        print(' ', nm, 'one capture only:', [(c, round(v, 3)) for c, v, _ in vals])
        continue
    print(' ', nm, len(vals), 'captures median', round(float(np.median(arr)), 3), 'range',
          round(float(arr.max() - arr.min()), 3),
          'SETTLED' if arr.max() - arr.min() <= 0.08 else 'not resolved',
          [(c, round(v, 3)) for c, v, _ in vals])

print('')
print('THE SILL TO HEAD SPAN, drawn', round(DRAWN_HEAD - DRAWN_SILL, 3), 'm')
allsp = []
for k in sorted(spans):
    arr = np.array([v for _, v in spans[k]])
    allsp.extend(arr.tolist())
    print('  opening', k, len(arr), 'captures median', round(float(np.median(arr)), 3),
          'range', round(float(arr.max() - arr.min()), 3), [(c, round(v, 3)) for c, v in spans[k]])
if len(allsp) >= 3:
    A = np.array(allsp)
    print('  across everything:', len(A), 'readings, median', round(float(np.median(A)), 3),
          'quartiles', round(float(np.percentile(A, 25)), 3), round(float(np.percentile(A, 75)), 3))
