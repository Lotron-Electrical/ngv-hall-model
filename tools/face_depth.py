# 2026-09-09: HOW FAR OUT IS THE NORTH WALL'S FACE? The model draws it on d -0.090 and that number has never
# been fitted from an identified estimator. tools/wall_edges.py used to fit it jointly with the jamb
# positions, and the audit showed that fit was not identified: forcing the depth term to zero changed the
# residual rms by 3 mm over 492 readings, which means the data never constrained it.
# THE IDENTIFIED FORM. A jamb is a vertical line ON the wall face. If the face is drawn at the wrong depth
# by d, the projected line lands sideways in the image by roughly d * (how far along the hall the camera
# stands from that jamb) / (how far out from the wall it stands). That ratio varies enormously across a
# walking pass, from near zero when the camera is square on to well past one at the ends, so the slope of
# the offsets against it IS the depth error, separately from any jamb being in the wrong place: a
# misplaced jamb adds a constant, and a misplaced face adds a slope.
# Fitted per capture, then pooled across captures, because a single pass shares its own systematics.
#   python tools/face_depth.py <dir of raw csv>
import sys, os, glob, csv
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/wallraw'
print('%-8s %6s %9s %9s %9s   %s' % ('capture', 'rows', 'slope', 'intercept', 'r range', 'reading'))
slopes = []
for f in sorted(glob.glob(os.path.join(d, '*.csv'))):
    rows = list(csv.DictReader(open(f)))
    if len(rows) < 30:
        print('%-8s %6d %9s %9s %9s   too few rows' % (os.path.basename(f)[:8], len(rows), '-', '-', '-')); continue
    cls = rows[0]['class']
    r = np.array([float(x['ratio']) for x in rows]); o = np.array([float(x['offset']) for x in rows])
    # one jamb per opening can carry its own constant, so remove each jamb's own mean before the fit:
    # what is left is only how the reading VARIES with the geometry, which is the depth term alone
    keys = [x['jamb'] for x in rows]
    for k in set(keys):
        m = np.array([q == k for q in keys])
        if m.sum() >= 3: o[m] -= o[m].mean(); r[m] -= r[m].mean()
    if r.std() < 0.05:
        print('%-8s %6d %9s %9s %9.3f   the camera never moves enough for this to be identified'
              % (cls, len(rows), '-', '-', float(r.max() - r.min()))); continue
    A = np.vstack([r, np.ones_like(r)]).T
    sol, res, _, _ = np.linalg.lstsq(A, o, rcond=None)
    slopes.append((cls, float(sol[0]), len(rows)))
    print('%-8s %6d %+9.3f %+9.3f %9.3f   face is %+0.3f m from where it is drawn'
          % (cls, len(rows), sol[0], sol[1], float(r.max() - r.min()), sol[0]))
print('')
if len(slopes) >= 2:
    v = np.array([s[1] for s in slopes])
    med = float(np.median(v)); rng = float(v.max() - v.min())
    print('POOLED over %d captures: %+0.3f m, capture range %.3f m' % (len(v), med, rng))
    if rng > 0.10: print('the captures disagree by %.0f mm: the face is NOT measured by this' % (rng * 1000))
    elif abs(med) > 0.05: print('agreed and out: the drawn face should move %+0.3f m' % med)
    else: print('agreed and within %.0f mm: the drawn face stands' % (abs(med) * 1000))
else:
    print('fewer than two captures could be fitted: not measured')
