# 2026-09-09: what does the gallery deck actually rest on? Count it, do not assert it.
#
# 8.34 is the most load-bearing number on these balconies. The solid upstand, the rail, the fascia, the
# floor and the ceiling below are all drawn as offsets from it, so every balcony height in this model is
# that number plus something. It has never been measured. Tonight the photometric route was tried and
# closed: tools/run_soffit_edge.py walked a ladder over the slab soffit at both ends, which is the one
# part of that structure a camera on the hall floor can see, and the west returned a feasibility of 0.37
# standard deviations per metre against a bar the east end once failed on 0.13, while the east returned
# four detections above the contrast bar. Dark stone under dark stone over a dim gallery. There is no step
# there to find, at either end.
#
# SO THE DECK RESTS ON CAMERA POSITIONS, AND THIS SAYS EXACTLY WHICH ONES AND HOW TIGHT THEY ARE. A lens
# that stood on a floor is above that floor: that is rigorous and assumption-free, and it gives an upper
# bound and nothing else. Turning it into a bracket needs one thing this archive cannot measure, how high
# a lens sits above the feet carrying it, so that assumption is stated in the open with the range it
# spans rather than buried in a number.
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UMIN, UMAX, FACE = 0.344, 51.906, 3.85
WFACE, EFACE = UMIN + FACE, UMAX - FACE
DECK, LOWER, SLAB = 8.34, 6.33, 0.26
# a handheld or head-mounted lens sits somewhere in this range above the floor its owner stands on. It is
# the one quantity here that cannot be measured from the imagery, so it is named rather than assumed away.
LENS_LO, LENS_HI = 1.05, 1.75
CLASSES = ['walk', 'night', 'day4k', 'b1', 'b1p', 'b3', 'b3p', 'b4', 'b5', 'b5p', 'b7s', 'b7sp',
           'b6g', 'b6gp']

lenses = []
for cls in CLASSES:
    try:
        for stem, (cam, _ip) in U.load_class(cls).items():
            q = cam.center - O
            lenses.append((cls, stem, float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])))
    except Exception:
        continue
print('%d posed lenses across %d classes' % (len(lenses), len(set(k[0] for k in lenses))))

on_deck = [k for k in lenses
           if (UMIN <= k[2] <= WFACE or EFACE <= k[2] <= UMAX) and DECK < k[4] < DECK + 2.6]
on_lower = [k for k in lenses
            if (UMIN <= k[2] <= WFACE or EFACE <= k[2] <= UMAX) and LOWER < k[4] < LOWER + 2.0]
print('')
for label, group, floor in (('the TOP deck, drawn %.2f' % DECK, on_deck, DECK),
                            ('the LOWER deck, drawn %.2f' % LOWER, on_lower, LOWER)):
    print('%s' % label.upper())
    if len(group) < 4:
        print('   %d lenses stand on it, too few to bound anything' % len(group))
        continue
    hs = np.array([k[4] for k in group])
    lo = float(hs.min())
    low = min(group, key=lambda z: z[4])
    print('   %d lenses stand on it, from %d classes, lens heights %.3f to %.3f'
          % (len(group), len(set(k[0] for k in group)), lo, float(hs.max())))
    print('   the lowest is %s %s on h %.3f' % (low[0], low[1], lo))
    print('   RIGOROUS, no assumption: the floor is below the lowest lens, so it is under %.3f.' % lo)
    print('   That is %+.3f m of room above the drawn %.2f, which is a bound and not a measurement.'
          % (lo - floor, floor))
    print('   WITH THE ONE ASSUMPTION NAMED, a lens %.2f to %.2f m above its feet puts this floor'
          % (LENS_LO, LENS_HI))
    print('   between %.3f and %.3f. The drawn %.2f %s inside that.'
          % (lo - LENS_HI, lo - LENS_LO, floor,
             'sits' if lo - LENS_HI <= floor <= lo - LENS_LO else 'does NOT sit'))
    print('')

print('AND THE TWO DECKS TOGETHER SAY SOMETHING NEITHER SAYS ALONE, if both carry lenses: the gap')
print('between them is drawn %.2f m, and a lens-height assumption cancels out of a DIFFERENCE the same'
      % (DECK - LOWER))
print('way a common drift cancelled out of the openings and the lower tier this evening.')
if len(on_deck) >= 4 and len(on_lower) >= 4:
    dlo = float(np.min([k[4] for k in on_deck]))
    llo = float(np.min([k[4] for k in on_lower]))
    print('   lowest lens on each: %.3f and %.3f, a difference of %.3f m against a drawn %.3f.'
          % (dlo, llo, dlo - llo, DECK - LOWER))
    print('   THAT IS NOT A MEASUREMENT EITHER, and the reason is worth being clear about: the two')
    print('   minima come from different people in different captures, so the assumption does not')
    print('   cancel, it merely changes into an assumption that two strangers were the same height.')
    print('   It is reported because it is the closest this archive comes, and it agrees to %.0f mm.'
          % (1000 * abs((dlo - llo) - (DECK - LOWER))))
else:
    print('   one of the two decks carries too few lenses, so that difference cannot be formed.')
