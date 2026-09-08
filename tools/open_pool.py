# 2026-09-09: the openings' sill and head pooled ACROSS captures, the test the jambs and the balcony levels
# both forced. One capture's own quartiles say how well its consecutive frames agree, not how well the edge
# is known. Feed it the json tools/open_levels.py writes with OPEN_JSON set.
#   python tools/open_pool.py <dir of *.json> [max spread to accept, default 0.10]
import sys, os, json, glob
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/openjson'
lim = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
caps = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, '*.json')))]
print('%d captures: %s' % (len(caps), ', '.join('%s(%d frames)' % (c['class'], c['frames']) for c in caps)))
for lvl, drawn in (('sill', 8.99), ('head', 11.35)):
    keys = []
    for c in caps:
        for k in c['levels']:
            if k.startswith(lvl + '-') and k not in keys: keys.append(k)
    keys.sort(key=lambda k: int(k.split('-')[1]))
    print('')
    print('%s, drawn h %.2f' % (lvl.upper(), drawn))
    print('  %-10s %6s %5s %8s %8s %8s   %s' % ('opening', 'u', 'caps', 'median', 'range', 'inner', 'verdict'))
    agreed = []
    for k in keys:
        vals, inner, who = [], [], []
        for c in caps:
            j = c['levels'].get(k)
            if not j: continue
            vals.append(j['median']); inner.append(j['p75'] - j['p25']); who.append('%s %+.3f' % (c['class'], j['median']))
        u = next(c['levels'][k]['u'] for c in caps if k in c['levels'])
        if len(vals) < 2:
            print('  %-10s %6.2f %5d %8s %8s %8s   one capture only, not measured' % (k, u, len(vals), '%+.3f' % vals[0], '-', '-'))
            continue
        v = np.array(vals); med = float(np.median(v)); rng = float(v.max() - v.min()); inn = float(np.median(inner))
        if rng > lim: verdict = 'captures disagree by %.0f mm, not measured' % (rng * 1000)
        elif abs(med) > 0.05: verdict = 'MOVES %+.3f m' % med; agreed.append((k, med))
        else: verdict = 'settled, within %.0f mm' % (abs(med) * 1000); agreed.append((k, med))
        print('  %-10s %6.2f %5d %+8.3f %8.3f %8.3f   %s' % (k, u, len(v), med, rng, inn, verdict))
        print('      %s' % '; '.join(who))
    allv = []
    for k in keys:
        v = [c['levels'][k]['median'] for c in caps if k in c['levels']]
        if len(v) >= 2: allv.append(float(np.median(v)))
    if allv:
        print('  POOLED OVER %d OPENINGS: median %+0.3f m, opening-to-opening spread %.3f m'
              % (len(allv), float(np.median(allv)), float(max(allv) - min(allv))))
        if agreed:
            am = float(np.median([m for _, m in agreed]))
            print('  of those, %d agree across captures within %.0f mm; their median is %+0.3f m'
                  % (len(agreed), lim * 1000, am))
# the coursing is measured on this wall, so say where the drawn levels and the measured ones sit in it
print('')
print('THE COURSING CHECK. North bed joints are measured at h = 0.080 + 0.304k (4 mm orthophotos, 1,026 frames).')
for lvl, drawn in (('sill', 8.99), ('head', 11.35)):
    kk = (drawn - 0.080) / 0.304
    near = round(kk)
    print('  %-5s drawn %6.3f  =  joint %.2f, i.e. %+0.3f m off the nearest bed joint (%.3f)'
          % (lvl, drawn, kk, drawn - (0.080 + 0.304 * near), 0.080 + 0.304 * near))
