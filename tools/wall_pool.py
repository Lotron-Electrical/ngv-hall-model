# 2026-09-09: the north wall's jambs pooled ACROSS captures, which is the only spread that means anything.
# A single capture's quartiles say how well its own frames agree with each other, and consecutive frames of
# one walking pass share every systematic that pass has: its exposure, its motion, its pose solution, the
# side of the hall it walked. Measured today, that inner spread is typically 0.03 m while the spread BETWEEN
# five separate captures of the same jamb reaches 0.33 m, ten times larger. So a jamb is only "measured"
# when several captures agree, and the number to quote is the median of the per-capture medians with the
# capture-to-capture range beside it.
# Feed it the json files tools/wall_edges.py writes with WALL_JSON set.
#   python tools/wall_pool.py <dir of *.json> [max spread to accept, default 0.10]
import sys, os, json, glob
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/walljson'
lim = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
files = sorted(glob.glob(os.path.join(d, '*.json')))
caps = [json.load(open(f)) for f in files]
print('%d captures: %s' % (len(caps), ', '.join('%s(%d frames)' % (c['class'], c['frames']) for c in caps)))
names = []
for c in caps:
    for k in c['jambs']:
        if k not in names: names.append(k)
names.sort(key=lambda k: next(c['jambs'][k]['u'] for c in caps if k in c['jambs']))
print('%-22s %6s  %5s %7s %7s %7s   %s' % ('jamb', 'u', 'caps', 'median', 'range', 'inner', 'verdict'))
firm, loose = [], []
for k in names:
    vals, inner, who = [], [], []
    for c in caps:
        j = c['jambs'].get(k)
        if not j: continue
        vals.append(j['median']); inner.append(j['p75'] - j['p25']); who.append(c['class'])
    if len(vals) < 2:
        print('%-22s %6.3f  %5d %7s %7s %7s   one capture only, not measured'
              % (k, next(c['jambs'][k]['u'] for c in caps if k in c['jambs']), len(vals), '%+.3f' % vals[0] if vals else '-', '-', '-'))
        continue
    v = np.array(vals); u = next(c['jambs'][k]['u'] for c in caps if k in c['jambs'])
    med = float(np.median(v)); rng = float(v.max() - v.min()); inn = float(np.median(inner))
    ok = rng <= lim
    if ok and abs(med) > 0.05: verdict = 'MOVES: %+.3f m' % med; firm.append((k, u, med, rng, len(v)))
    elif ok: verdict = 'settled, within %.0f mm' % (abs(med) * 1000)
    else: verdict = 'captures disagree by %.0f mm, not measured' % (rng * 1000); loose.append((k, rng))
    print('%-22s %6.3f  %5d %+7.3f %7.3f %7.3f   %s' % (k, u, len(v), med, rng, inn, verdict))
allr = [c['jambs'][k]['p75'] - c['jambs'][k]['p25'] for c in caps for k in c['jambs']]
per = []
for k in names:
    v = [c['jambs'][k]['median'] for c in caps if k in c['jambs']]
    if len(v) >= 2: per.append(max(v) - min(v))
print('')
print('inner spread (one capture, frame to frame)  median %.3f m over %d jamb/capture pairs' % (float(np.median(allr)), len(allr)))
print('outer spread (capture to capture)           median %.3f m over %d jambs' % (float(np.median(per)) if per else 0, len(per)))
print('the outer spread is %.1f times the inner: quoting a capture\'s own quartiles as the uncertainty '
      'understates it by that factor' % ((np.median(per) / max(np.median(allr), 1e-6)) if per else 0))
print('')
if firm:
    print('jambs that several captures agree are still wrong:')
    for k, u, m, r, nn in firm: print('  %-22s u %.3f  move %+.3f m  (%d captures, range %.3f)' % (k, u, m, nn, r))
else:
    print('no jamb is both agreed across captures and out by more than 50 mm: the table stands as drawn')
if loose: print('%d jambs the captures cannot agree on, worst %.0f mm' % (len(loose), 1000 * max(r for _, r in loose)))
