# 2026-09-09: THE OPENINGS MOVE AS OPENINGS, not as loose jambs.
# The pooled jamb table (tools/wall_pool.py) now has five jambs that several captures agree are out by more
# than 50 mm. Applying those five one at a time would change four openings' WIDTHS to 1.269, 1.112, 1.094
# and 1.240, and this is a bluestone wall of twelve identical windows: the widths are not what varies.
# Read the same numbers as whole openings and the picture is different and much more believable. Where both
# jambs of an opening are resolved they mostly move the SAME WAY BY THE SAME AMOUNT, which is an opening
# standing a few centimetres from where it is drawn, not a window of a different size:
#   opening 2   west -0.056  east -0.100
#   opening 4   west +0.119  east +0.121
#   opening 5   west +0.068  east +0.095
# So the test applied here is stricter than the per-jamb one AND it keeps the width fixed: an opening moves
# only when BOTH its jambs are pooled from two or more captures, both point the same way, and their mean
# exceeds 50 mm. The shift applied is that mean.
# The measured shift is a LOWER BOUND: tools/wall_follow.py puts a residual follow gain of 0.37 on this
# instrument even after the fixed-point repair, and a following instrument always understates.
#   python tools/opening_shift.py [walljson dir] [min captures] [min shift]
import sys, os, json, glob
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/walljson'
minc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
minm = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
caps = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, '*.json')))]
print('%d captures: %s' % (len(caps), ', '.join(c['class'] for c in caps)))
# THE ESTIMATOR IS THE SHIFT ITSELF, pooled. Reading each jamb separately and combining the pooled results
# afterwards throws away the fact that both jambs are seen in the SAME frames of the SAME capture, where
# most of the error is common to them: the capture's exposure, its pose solution, the side it walked. So
# each capture first states its OWN shift for an opening, the mean of its two jamb offsets, and only then
# are those per-capture shifts pooled. What the pooling then measures is capture-to-capture disagreement
# about a shift, which is the number that matters, and the width never enters it.
print('%-8s %8s %8s %5s %8s %8s   %s' % ('opening', 'u0', 'u1', 'caps', 'shift', 'range', 'verdict'))
out, moved = [], 0
for i, (a, b) in enumerate(OPEN):
    wn, en = 'opening %2d west jamb' % i, 'opening %2d east jamb' % i
    per = []
    for c in caps:
        j = c['jambs']
        if wn in j and en in j:
            per.append((c['class'], (j[wn]['median'] + j[en]['median']) / 2.0))
    if len(per) < minc:
        print('%-8d %8.3f %8.3f %5d %8s %8s   fewer than %d captures resolve both jambs'
              % (i + 1, a, b, len(per), '-', '-', minc))
        out.append([a, b]); continue
    v = np.array([p[1] for p in per]); m = float(np.median(v)); r = float(v.max() - v.min())
    who = '; '.join('%s %+.3f' % (n, x) for n, x in per)
    if r > 0.10:
        print('%-8d %8.3f %8.3f %5d %+8.3f %8.3f   captures disagree by %.0f mm, no move'
              % (i + 1, a, b, len(v), m, r, r * 1000)); print('      %s' % who)
        out.append([a, b]); continue
    if abs(m) <= minm:
        print('%-8d %8.3f %8.3f %5d %+8.3f %8.3f   agreed and within %.0f mm: stays'
              % (i + 1, a, b, len(v), m, r, minm * 1000)); print('      %s' % who)
        out.append([a, b]); continue
    print('%-8d %8.3f %8.3f %5d %+8.3f %8.3f   MOVES %+0.3f m, width kept %.3f'
          % (i + 1, a, b, len(v), m, r, m, b - a)); print('      %s' % who)
    out.append([round(a + m, 3), round(b + m, 3)]); moved += 1
print('')
print('%d of 12 openings move. Widths untouched: every one stays %.3f.' % (moved, OPEN[0][1] - OPEN[0][0]))
print('openings:[' + ','.join('[%.3f,%.3f]' % (p[0], p[1]) for p in out) + ']')
