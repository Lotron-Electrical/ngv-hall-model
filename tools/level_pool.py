# 2026-09-09: the balcony levels pooled ACROSS captures, the same test tools/wall_pool.py applies to the
# wall's jambs and for the same reason. Today's upstand change (0.56 to 0.68) was made on three readings
# that each looked tight inside their own capture; the wall's jambs then showed that inner tightness is not
# accuracy, so the same change has to survive the same test. Six captures now see the two ends: the day
# walk, the night walk, the 4K balcony set, the two balcony clips b1 and b3, and the six posed frames of
# clip 153148. A level is measured when several of them agree, and the number to quote is the median of
# the per-capture medians with the capture-to-capture range beside it.
#   python tools/level_pool.py <dir of *.json> [max spread to accept, default 0.10]
import sys, os, json, glob
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/leveljson'
lim = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
caps = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, '*.json')))]
for end in ('west', 'east'):
    here = [c for c in caps if c['end'] == end and c['levels']]
    print('')
    print('%s END: %s' % (end.upper(), ', '.join('%s(%d frames)' % (c['class'], c['frames']) for c in here) or 'nothing'))
    if not here: continue
    names = []
    for c in here:
        for k in c['levels']:
            if k not in names: names.append(k)
    names.sort(key=lambda k: next(c['levels'][k]['h'] for c in here if k in c['levels']))
    print('  %-19s %6s %5s %8s %8s %8s   %s' % ('level', 'h', 'caps', 'median', 'range', 'inner', 'verdict'))
    for k in names:
        vals, inner, who = [], [], []
        for c in here:
            j = c['levels'].get(k)
            if not j: continue
            vals.append(j['median']); inner.append(j['p75'] - j['p25']); who.append('%s %+.3f' % (c['class'], j['median']))
        hv = next(c['levels'][k]['h'] for c in here if k in c['levels'])
        if len(vals) < 2:
            print('  %-19s %6.2f %5d %8s %8s %8s   one capture only, not measured   [%s]'
                  % (k, hv, len(vals), '%+.3f' % vals[0], '-', '-', '; '.join(who)))
            continue
        v = np.array(vals); med = float(np.median(v)); rng = float(v.max() - v.min()); inn = float(np.median(inner))
        if rng > lim: verdict = 'captures disagree by %.0f mm, not measured' % (rng * 1000)
        elif abs(med) > 0.05: verdict = 'MOVES: %+.3f m' % med
        else: verdict = 'settled, within %.0f mm' % (abs(med) * 1000)
        print('  %-19s %6.2f %5d %+8.3f %8.3f %8.3f   %s' % (k, hv, len(vals), med, rng, inn, verdict))
        print('      %s' % '; '.join(who))
