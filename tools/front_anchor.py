# 2026-09-09: does the balcony front top read the same by day and by night?
#
# A stone edge reads the same under any light. A boundary that is really where the light stops does not,
# because after dark this hall is lit from below and the sides rather than through the stained glass
# overhead. The jambs could not take that test at all: their 22 night frames yield no usable column on
# that band of wall even with a 3 grey level bar and an 8 sample window. The fronts can.
#
# BUT THE FREE FITS CANNOT BE COMPARED DIRECTLY, and pretending otherwise would repeat the mistake that
# cost the sill. The day walk spans 37 m of hall and the night walk 15, and a horizontal line at constant
# (u, h) is separated from its rays only by cameras at different distances along that axis. Run free, the
# night east fit lands on u 50.065 h 10.289 against the day's 48.565 and 9.883: two metres of station and
# 0.42 m of height. That is the slide, not a disagreement about the building.
#
# SO ANCHOR BOTH ON THE SAME STATION AND COMPARE ONLY THE HEIGHT. With u fixed, each ray gives the height
# directly, one unknown, nothing left to slide: h = ch + vh*(ufix - cu)/vu. If day and night then agree,
# the edge is stone. If they do not, it is a lighting boundary and the number this model draws is a
# photograph of the lights rather than of the balcony.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
# ANCHOR EACH END ON THE STATION ITS OWN FIT MEASURED, not on the drawn face, and the first run of this
# shows why it matters. Anchored on the drawn 48.056 the east came out 0.12 m low in both lighting states,
# which is not a finding about the balcony: the shipped east height was derived at u 48.397, and along the
# median ray from the middle of the hall 0.34 m of station is worth 0.12 m of height. Anchoring both ends
# on the drawn face therefore compared the night against a shifted version of the day.
FACE = {'west': 4.160, 'east': 48.397}
DRAWNFACE = {'west': 4.194, 'east': 48.056}
SHIPPED = {'west': 9.799, 'east': 9.865}


def anchored(R, ufix, expect, win=0.5, tol=0.05):
    """the height the rays agree on, by consensus rather than by average.

    The first version of this took the MEDIAN of every anchored height inside a half metre window and
    came back 0.21 m low at both ends. That is not a fit, it is the middle of a mixed population: the
    ladder spans 1.8 m of face and catches several edges, so the median sits between them rather than on
    any one. A line is found by consensus, so this counts how many rays land within a tolerance of each
    candidate height and takes the peak, which is the one-dimensional form of what RANSAC does.
    """
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    h = R[:, 1] + R[:, 3] * (ufix - R[:, 0]) / vu
    h = h[np.abs(h - expect) < win]
    if len(h) < 25:
        return None, len(h)
    grid = np.arange(expect - win, expect + win, 0.002)
    counts = np.array([int(np.sum(np.abs(h - g) < tol)) for g in grid])
    g = float(grid[int(np.argmax(counts))])
    near = h[np.abs(h - g) < tol]
    return float(np.median(near)), int(len(near))


print('%-6s %-5s  %6s  %8s  %8s  %s' % ('clip', 'end', 'rays', 'anchored', 'shipped', 'difference'))
res = {}
for end in ('west', 'east'):
    for cls in ('walk', 'night'):
        src = os.path.join(POSEDIR, '%s-%s-front-far-rays.npy' % (end, cls))
        if not os.path.exists(src):
            print('%-6s %-5s  no saved rays' % (cls, end))
            continue
        R = np.load(src)
        h, n = anchored(R, FACE[end], SHIPPED[end])
        if h is None:
            print('%-6s %-5s  %6d  only %d rays land near this edge, refused' % (cls, end, len(R), n))
            continue
        res.setdefault(end, {})[cls] = h
        print('%-6s %-5s  %6d  %8.3f  %8.3f  %+.3f m' % (cls, end, n, h, SHIPPED[end], h - SHIPPED[end]))

print('')
for end, v in res.items():
    if 'walk' in v and 'night' in v:
        d = abs(v['walk'] - v['night'])
        print('%s end: day %.3f against night %.3f, %.0f mm apart' % (end, v['walk'], v['night'], 1000 * d))
        # THE BAR HAS TO ALLOW FOR HOW THIN THE NIGHT SAMPLE IS. The day set carries hundreds of rays and
        # the night set tens, and a consensus peak on tens of rays is worth about the tolerance it is
        # counted with. So agreement inside 0.06 m is agreement; past that is a real disagreement.
        print('   %s' % ('the edge reads the same under two completely different lighting states, so it '
                         'is stone and not a boundary the lights drew' if d <= 0.06 else
                         'the two lighting states disagree by more than the thin night sample explains, '
                         'so this edge is suspect'))
    else:
        print('%s end: only one lighting state usable, so no comparison' % end)
