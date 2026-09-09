# 2026-09-09: move the north openings onto the jambs that were measured, tools/jamb_lines.py, and ONLY
# the ones that were measured.
#
# Nine vertical lines were peeled out of the hall-floor imagery with no window around the drawn values,
# four of one polarity and five of the other, each fitted from cameras spread thirty metres along the hall
# and each agreeing with its own rays to between 9 and 18 mm. Every one of them sits EAST of the drawn
# jamb, by between 0.044 and 0.227 m, median 0.147.
#
# WHY THAT IS A POSITION AND NOT A DETECTOR BIAS, which is the only thing that could fake it. A brightness
# step detector can be biased, but the bias points INTO the dark side: it would push a west jamb east and
# an east jamb west, narrowing every opening while leaving its centre alone. Both polarities here move the
# same way. Only the wall moving can do that. The narrowing that a bias would cause is also visible and it
# is small: the four openings measured end to end come out 1.191 m against a drawn 1.212, about 10 mm per
# edge, and that part is NOT applied.
#
# THE FIRST VERSION OF THIS MOVED ALL TWELVE AND A HARD BOUND CAUGHT IT, which is the whole reason the
# bounds file exists. Reasoning that the openings are one rigid set, it applied the median to every one of
# them. Opening 11 then failed a check that predates today: rays measured passing THROUGH that opening
# occupy u 40.948 to 41.674, and a ray that arrived is not an estimate, it is proof that nothing stood in
# its way, so that jamb cannot be further east than 40.948. The uniform move put it on 41.053. The nine
# measured lines all lie between u 20.0 and 34.9, so opening 11 was never measured at all; it was
# extrapolated, and the extrapolation was refuted by an arrival.
# So the move is applied to the five openings the lines actually cover and to nothing else. The rest stay
# exactly as drawn, and the step in the rhythm that leaves is not a claim about the building, it is the
# edge of what has been measured, which is the honest thing for it to be.
import re

import numpy as np

OFFS = [0.145, 0.227, 0.160, 0.147, 0.044, 0.117, 0.200, 0.143, 0.171]
SHIFT = round(float(np.median(OFFS)), 3)
BASE = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.770, 19.983],
        [22.418, 23.631], [26.066, 27.279], [29.816, 31.028], [33.495, 34.706], [37.177, 38.383],
        [40.906, 42.118], [44.526, 45.739]]
MEASURED = (4, 5, 6, 7, 8)          # the openings the nine jamb lines actually land in, u 18.8 to 34.9

print('nine lines: median %+.3f m, mean %+.3f m, spread %.3f m, every one of them positive'
      % (SHIFT, float(np.mean(OFFS)), float(np.ptp(OFFS))))
out = []
for i, (a, b) in enumerate(BASE):
    s = SHIFT if i in MEASURED else 0.0
    out.append('[%.3f,%.3f]' % (a + s, b + s))
new = '[%s]' % ','.join(out)

src = open('index.html', encoding='utf-8').read()
old = re.search(r'const WALLF=\{openings:(\[\[.*?\]\]),', src, re.S).group(1)
open('index.html', 'w', encoding='utf-8', newline='\n').write(src.replace(old, new, 1))
print('openings %s moved %+.3f m east; the other seven are untouched'
      % (', '.join(str(i + 1) for i in MEASURED), SHIFT))
print('opening 11 stays on %.3f because a ray measured passing through it reached u 40.948'
      % BASE[10][0])
