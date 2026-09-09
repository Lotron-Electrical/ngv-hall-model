# 2026-09-09: the model draws both end galleries spanning the whole hall and nothing has ever checked it.
#
# Every quad on an end wall runs from d 0 to d 15.364, the full width. That is an assumption inherited from
# the first sketch and it has survived every measurement made this week, because every one of those
# measurements threw away the only evidence that could test it. The ladder in tools/west_far.py walks 60
# stations ACROSS the hall and reports one detection per station, then discards which station it came from
# before saving. So a fit could say where a feature stands and how high it is, and never whether it runs
# the full width or stops short.
#
# WITH THE STATION KEPT, THE QUESTION IS DIRECT. A feature that spans the hall puts inliers in every
# quarter of it. A feature that stops short leaves a quarter empty, and one that is really on a LONG wall
# rather than the end piles its inliers against one side, because a line on the north or south wall seen
# from down the hall projects almost where an end feature would and the fit cannot tell them apart.
#
# THE TEST HAS TO BE FAIR ABOUT WHERE CAMERAS CAN LOOK, and that is the trap here. The stations are not
# sampled evenly by the imagery: a camera near the north wall sees the far side of the parapet at a worse
# angle than the near side, so a raw quarter count would call every feature lopsided. So each feature's
# quarters are compared against the quarters of ALL detections on that same end, which carry exactly the
# same sampling bias. What matters is whether this feature is more lopsided than the sampling already is.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
FEATS = (('-upW', 'the solid upstand top', {'west': 9.097, 'east': 9.095}),
         ('-railW', 'the rail top', {'west': 9.799, 'east': 9.865}))
STATION = {'west': {'-upW': 3.710, '-railW': 4.194}, 'east': {'-upW': 48.056, '-railW': 48.056}}
DWALL = 15.364
QUARTERS = ((0.0, 3.841), (3.841, 7.682), (7.682, 11.523), (11.523, 15.364))
TOL = 0.05


def solve_h(R, uf):
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (uf - R[:, 0]) / vu


def quarters(d):
    return [100.0 * float(np.mean(np.logical_and(d >= lo, d < hi))) for lo, hi in QUARTERS]


for end in ('west', 'east'):
    print('')
    print('%s END' % end.upper())
    for tag, what, expect in FEATS:
        src = os.path.join(POSEDIR, '%s%s-far-rays.npy' % (end, tag))
        if not os.path.exists(src):
            print('   %-24s no saved rays' % what)
            continue
        A = np.load(src)
        if A.shape[1] < 5:
            print('   %-24s saved without the hall station, cannot be asked' % what)
            continue
        R, DD = A[:, :4], A[:, 4]
        uf = STATION[end][tag]
        h = solve_h(R, uf)
        sel = np.abs(h - expect[end]) < TOL
        base = quarters(DD)
        print('   %-24s %d detections, %d of them on this feature' % (what, len(R), int(sel.sum())))
        print('        every detection on this end, by quarter of the hall: %s'
              % '  '.join('%4.0f%%' % q for q in base))
        if int(sel.sum()) < 40:
            print('        too few on the feature to split by quarter')
            continue
        q = quarters(DD[sel])
        print('        THIS FEATURE, by quarter:                          %s'
              % '  '.join('%4.0f%%' % t for t in q))
        print('        it reaches d %.2f to %.2f of a hall %.2f wide' % (DD[sel].min(), DD[sel].max(), DWALL))
        empty = [i for i, t in enumerate(q) if t < 5.0 and base[i] >= 10.0]
        worst = max(abs(a - b) for a, b in zip(q, base))
        if empty:
            print('        QUARTER %s CARRIES DETECTIONS BUT NOT THIS FEATURE, so it does not span the hall'
                  % ', '.join(str(i + 1) for i in empty))
        elif worst < 15.0:
            print('        it follows the sampling to within %.0f points in every quarter, so it spans the'
                  % worst)
            print('        hall the way the model draws it and there is nothing to change')
        else:
            print('        it departs from the sampling by %.0f points in its worst quarter, which is a'
                  % worst)
            print('        lean rather than a gap: worth naming, not worth redrawing on')
