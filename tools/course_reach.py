# 2026-09-10: FIND THE FRAME WHERE THE ASHLAR RUNS ALL THE WAY DOWN TO THE DECK.
#
# tools/wall_courses.py counted the end wall in its own stone and got 16.8 courses, 5.15 m, from the
# canopy junction down to THE BOTTOM EDGE OF THE FRAME, with the deck still below it. This file draws
# that same distance as 13.5 less 8.340 = 5.16 m. So the count is already all but used up, and the bound
# it left behind is sharp: ONE more course down there, 0.306 m, and the deck is not on 8.340 but on about
# 8.03.
#
# THAT MATTERS MORE SINCE YESTERDAY. tools/deck_pair.py could not measure the deck absolutely, but the
# raw eye heights on the east deck sit about 0.26 m lower over 8.340 than a carried phone should, which
# points the same way and by about the same amount. Two weak hints in the same direction are worth one
# proper look.
#
# SO THE JOB IS TO FIND A BETTER FRAME, and that is a search rather than a measurement. A frame is useful
# when its run of joints STOPS INSIDE THE PICTURE instead of running off the bottom edge, because a run
# that stops inside the picture has found a real bottom to the wall. This sweeps the balcony clips, reads
# a strip down the middle of each frame with the same joint finder wall_courses.py uses, and ranks frames
# by whether the ashlar terminates in shot and how many courses it spans.
#
# WHAT THIS TOOL IS NOT. It does not measure anything. It picks candidates, and the candidates then have
# to be looked at, because a run of joints can stop for reasons that are not a deck: a shadow, a handrail,
# a person, the top of a cabinet. Calling a termination a deck without looking would be exactly the kind
# of claim this repo has spent the day retracting.
#   python tools/course_reach.py <clip> [step] [max]
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
CLIP = sys.argv[1]
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 4
MAXF = int(sys.argv[3]) if len(sys.argv) > 3 else 400
MINSEP = 22
X0, X1, Y0, Y1 = 0.10, 0.90, 0.04, 1.00
# THE QUALITY GATE, WHICH THE FIRST RUN OF THIS DID NOT HAVE AND BADLY NEEDED. Without it the finder
# returned 86 "courses" spanning 26.59 m of wall in a single frame, with the gaps between them scattering
# 33 to 86 per cent. It was reading every dark line in the picture. wall_courses.py only ever trusted a
# strip when four of seven agreed on a pitch to 2.5 per cent, and ashlar is regular, so an irregular run
# is not ashlar. A strip must now hold its pitch to MAXSPREAD or it is thrown away.
MAXSPREAD = 0.15
MINJOINTS = 8
NSTRIP = 9
STOPMARGIN = 2.5


def joints(prof):
    k = 61
    med = np.array([np.median(prof[max(0, i - k // 2):i + k // 2 + 1]) for i in range(len(prof))])
    hp = prof - med
    rows = []
    for i in range(2, len(hp) - 2):
        if hp[i] < -1.2 and hp[i] <= hp[i - 1] and hp[i] < hp[i + 1] and hp[i] <= hp[i - 2] \
                and hp[i] < hp[i + 2]:
            if not rows or i - rows[-1] >= MINSEP:
                rows.append(i)
            elif hp[i] < hp[rows[-1]]:
                rows[-1] = i
    return rows


src = '%s/%s/images' % (B2, CLIP)
names = sorted(os.listdir(src))[::STEP][:MAXF]
print('%s: reading %d of %d frames, every %dth' % (CLIP, len(names), len(os.listdir(src)), STEP))
out = []
closest = []
for nm in names:
    im = cv2.imread(os.path.join(src, nm), cv2.IMREAD_GRAYSCALE)
    if im is None:
        continue
    H, W = im.shape[:2]
    gy0, gy1 = int(Y0 * H), int(Y1 * H)
    g = cv2.GaussianBlur(im.astype(np.float64), (5, 5), 0)
    best = None
    for xc in np.linspace(X0 * W + 20, X1 * W - 20, NSTRIP):
        c0, c1 = int(xc) - 14, int(xc) + 14
        rows = joints(g[gy0:gy1, c0:c1].mean(axis=1))
        if len(rows) < 8:
            continue
        gaps = np.diff(np.array(rows))
        keep = gaps[np.logical_and(gaps > MINSEP, gaps < 4 * np.median(gaps))]
        if len(keep) < MINJOINTS:
            continue
        pitch = float(np.median(keep))
        spread = float(np.percentile(keep, 75) - np.percentile(keep, 25)) / pitch
        # HOW CLOSE THE BEST STRIP IN THE WHOLE CLIP GETS IS RECORDED EVEN WHEN NOTHING PASSES, because
        # a negative from a search that was aimed badly is worth nothing, and the only way to tell the
        # difference is to see whether the best spread found is near the gate or nowhere near it.
        closest.append((spread, nm, len(keep), pitch))
        if spread > MAXSPREAD:
            continue
        # DOES THE RUN STOP INSIDE THE PICTURE. The last joint has to sit clear of the bottom of the
        # window by more than a course, or the wall simply left the frame and the count is a lower bound
        # like the one this is trying to improve on.
        stops = (gy1 - (gy0 + rows[-1])) > STOPMARGIN * pitch
        span = (rows[-1] - rows[0]) / pitch
        if best is None or (stops, span) > (best[0], best[1]):
            best = (stops, span, pitch, spread, gy0 + rows[0], gy0 + rows[-1], len(rows), int(xc), H)
    if best:
        out.append((nm,) + best)

if closest:
    closest.sort()
    print('   the most regular strip found anywhere in this clip holds its pitch to %.0f per cent over'
          % (100 * closest[0][0]))
    print('   %d gaps, in %s. The gate is %.0f per cent.'
          % (closest[0][2], closest[0][1], 100 * MAXSPREAD))
if not out:
    sys.exit('   NO FRAME IN THIS CLIP HOLDS A REGULAR PITCH over %d joints inside %.0f per cent, and the '
             'line above says whether that is the gate being tight or the ashlar not being there. If the '
             'best strip is nowhere near the gate then this clip has no clean run to count and the deck '
             'stays where it is.' % (MINJOINTS, 100 * MAXSPREAD))
term = [o for o in out if o[1]]
print('   %d frames gave a usable run, %d of them stop inside the picture' % (len(out), len(term)))
print('')
print('   frame                  courses   pitch px  spread   first  last   of H   stops in shot')
for o in sorted(out, key=lambda o: (-o[1], -o[2]))[:14]:
    nm, stops, span, pitch, spread, r0, r1, n, xc, H = o
    print('   %-22s %6.1f    %6.1f   %4.0f%%   %5d %5d  %5d   %s'
          % (nm, span, pitch, 100 * spread, r0, r1, H, 'yes' if stops else 'no'))
print('')
print('   ONE COURSE IS 0.306 m, so the longest run that STOPS IN SHOT spans %.2f m of wall.'
      % ((max([o[2] for o in term]) * 0.306) if term else 0.0))
print('   THAT IS A CANDIDATE AND NOT A RESULT. A run of joints stops for many reasons that are not a')
print('   deck: a shadow, a rail, a person, the top of a cabinet. The frames above have to be looked at')
print('   before any of them is called a floor.')
