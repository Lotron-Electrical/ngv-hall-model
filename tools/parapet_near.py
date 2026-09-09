# 2026-09-09: THE PARAPET READ FROM ARM'S LENGTH, which no measurement in this project had ever done.
#
# Every previous reading of an end parapet came from 28 to 40 m away across the hall, and when the follow
# gain was finally fitted rather than assumed those readings turned out to run a gain of 0.66 to 0.70,
# meaning they mostly reproduced the line they started from. The reason nothing closer existed is not that
# the footage is missing. b7s walks the two upper galleries and stands 0.86 to 1.00 m behind a parapet in
# twelve frames, twenty-seven counting the pan-chained ones. TWO RULES IN THE INSTRUMENT REFUSED ALL OF
# THEM BEFORE A PIXEL WAS READ:
#   the edge finder capped its search radius to 90 px, and the window is set in METRES, so from 0.9 m away
#     a 0.25 m window is 490 to 566 px and the frame was refused for being NEAR;
#   the frame filter required the level to be visible across the whole 15 m width, which a camera a metre
#     away can never satisfy: it sees about a metre of the line.
# Both are now fixed (MAXR in tools/edge_refine.py, and the sampler in tools/end_levels.py follows the
# stretch each camera can actually see). This reads what came out.
#
# The estimator is the same three-draw fit used everywhere else: A(d) = truth + g(d - truth) is linear in
# the drawn height, so the slope is the follow gain and the intercept gives the truth, with nothing
# assumed. A gain outside its physical range is refused as noise rather than reported as a disagreement.
#   python tools/parapet_near.py
import glob
import json
import os

import numpy as np

D = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson'
DRAWS = [('a', 8.92), ('b', 9.06), ('c', 9.20)]
KEY = 'top parapet top'
DECK = 8.34

pairs = set()
for f in glob.glob(os.path.join(D, 'near-a-*.json')):
    stem = os.path.basename(f)[len('near-a-'):-len('.json')]
    cut = stem.rfind('-')
    pairs.add((stem[:cut], stem[cut + 1:]))

print('%-8s %-6s %6s %8s %8s %8s %6s %7s %9s %8s'
      % ('capture', 'end', 'looks', 'A(low)', 'A(mid)', 'A(high)', 'gain', 'resid', 'truth', 'upstand'))
keep = []
for cap, end in sorted(pairs):
    rows = []
    for tag, _dv in DRAWS:
        p = os.path.join(D, 'near-%s-%s-%s.json' % (tag, cap, end))
        rows.append(json.load(open(p)).get('levels', {}).get(KEY) if os.path.exists(p) else None)
    if any(r is None for r in rows):
        print('%-8s %-6s   not every draw reported this level' % (cap, end))
        continue
    dv = np.array([v for _t, v in DRAWS])
    av = np.array([dv[i] + rows[i]['median'] for i in range(3)])
    looks = min(r['looks'] for r in rows)
    g, c = np.polyfit(dv, av, 1)
    resid = float(np.abs(av - (g * dv + c)).max())
    if not (0.0 <= g <= 0.85) or resid > 0.05:
        why = 'gain outside its physical range' if not (0.0 <= g <= 0.85) else 'not linear in the drawing'
        print('%-8s %-6s %6d %8.3f %8.3f %8.3f %6.2f %7.3f   %s' % (cap, end, looks, av[0], av[1], av[2], g, resid, why))
        continue
    truth = float(c / (1.0 - g))
    print('%-8s %-6s %6d %8.3f %8.3f %8.3f %6.2f %7.3f %9.3f %8.3f'
          % (cap, end, looks, av[0], av[1], av[2], g, resid, truth, truth - DECK))
    keep.append((cap, end, float(g), truth))

print('')
for end in ('west', 'east'):
    v = [k for k in keep if k[1] == end]
    if len(v) >= 2:
        t = np.array([x[3] for x in v])
        print(end, 'end:', len(v), 'near-field captures, median', round(float(np.median(t)), 3),
              'range', round(float(t.max() - t.min()), 3), 'implied upstand', round(float(np.median(t)) - DECK, 3))
    else:
        print(end, 'end:', len(v), 'near-field capture surviving, not enough to pool')
