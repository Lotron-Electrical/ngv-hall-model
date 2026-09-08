# 2026-09-09: IS THE EAST END WALL WHERE THE MODEL PUTS IT?
# The audit's largest claim: the east end face may stand 0.26-0.36 m west of the drawn u 48.056, which
# would move the whole east-end build further than any correction made today. tools/end_levels.py already
# carries the discriminator in its own comments: a wrong FACE position moves as the face moves and zeroes
# for EVERY level at one u, while a wrong HEIGHT stays put whatever the face does. So sweep the face and
# watch all the levels together. One capture cannot decide it (the audit's sweep was the day walk alone),
# so every capture that sees the end is swept and the results are pooled, the way the levels and the jambs
# both had to be.
#   python tools/face_sweep.py <west|east> [classes] [faces]
import sys, os, json, subprocess, tempfile
import numpy as np
end = sys.argv[1] if len(sys.argv) > 1 else 'east'
classes = (sys.argv[2].split(',') if len(sys.argv) > 2 else ['walk', 'night', 'b1'])
faces = [float(v) for v in (sys.argv[3].split(',') if len(sys.argv) > 3 else
                            ['47.70', '47.80', '47.90', '48.056', '48.20'])]
WATCH = ['top parapet top', 'head', 'end-wall top', 'lower parapet top']
tmp = tempfile.gettempdir()
res = {}
for cls in classes:
    for f in faces:
        jf = os.path.join(tmp, 'face-%s-%s-%s.json' % (cls, end, f))
        subprocess.run([sys.executable, '-u', 'tools/end_levels.py', cls, end, '25', str(f)],
                       env=dict(os.environ, LEVEL_JSON=jf), capture_output=True, text=True)
        if os.path.exists(jf): res[(cls, f)] = json.load(open(jf))['levels']
print('%s END, faces swept: %s' % (end.upper(), ', '.join('%.3f' % f for f in faces)))
for lvl in WATCH:
    print('')
    print('%s' % lvl.upper())
    print('  %-7s %s' % ('face', ''.join('%12s' % c for c in classes) + '%12s' % 'pooled'))
    for f in faces:
        vals = []
        cells = ''
        for cls in classes:
            r = res.get((cls, f), {}).get(lvl)
            if r is None: cells += '%12s' % '-'
            else: cells += '%12s' % ('%+0.3f(%d)' % (r['median'], r['n'])); vals.append(r['median'])
        pooled = '%12s' % ('%+0.3f' % float(np.median(vals)) if vals else '-')
        print('  %-7.3f %s' % (f, cells + pooled))
# the verdict: the face at which the pooled residuals of several levels are simultaneously smallest
print('')
print('THE TEST: a wrong FACE zeroes every level together at one u; a wrong HEIGHT does not move with the face.')
best = {}
for lvl in WATCH:
    got = [(f, [res[(c, f)][lvl]['median'] for c in classes if (c, f) in res and lvl in res[(c, f)]]) for f in faces]
    got = [(f, float(np.median(v))) for f, v in got if v]
    if len(got) < 3: print('  %-18s too few faces resolved' % lvl); continue
    f0 = min(got, key=lambda g: abs(g[1]))
    best[lvl] = f0[0]
    print('  %-18s smallest pooled residual %+0.3f at face %.3f' % (lvl, f0[1], f0[0]))
if len(best) >= 2:
    v = sorted(best.values())
    print('  the levels put the face between %.3f and %.3f' % (v[0], v[-1]))
    print('  the model draws it %.3f' % (48.056 if end == 'east' else 4.194))
