# 2026-09-09: confirm the biggest change shipped today with an instrument that uses no light at all.
#
# The west solid parapet moved 0.484 m behind its face this evening on two instruments that agree: the
# near-far station scan put its top on u 3.710 with 5 mm of half-to-half agreement against 63 mm at the
# end of the sweep on a null of 4, and the arrival cap independently forbade a solid anywhere past 4.010.
# Both of those are photometric. Both read brightness on a wall. If there is a systematic fault in how
# this archive reads brightness on that particular end, both would carry it.
#
# THERE IS A THIRD INSTRUMENT AND IT SHARES NOTHING WITH THEM. A posed camera centre is a place a lens
# physically was. Nobody stands inside a solid. So if any lens in this archive sits in the volume the
# model used to draw as solid stone, between the old face plane and the new one, at the height of that
# parapet, the recess is confirmed by occupancy rather than by photometry, and by geometry that never
# touches a pixel value.
#
# THE EAST END IS THE CONTROL AGAIN, and it is a real control because it can fail. The east parapet was
# measured flush this evening, so the equivalent volume behind ITS face is solid stone and should contain
# nothing. If lenses turn up in both bands the test is measuring something else, probably pose error, and
# it says nothing about the west.
#
# AND THE OLD MODEL HAS TO ANSWER FOR IT. Any lens found in the west band was standing inside the parapet
# as this model drew it until this evening. The occupancy audit did not catch that, because it checks the
# walls and not the gallery parapets, and that gap is worth naming whatever this test returns.
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK, SLAB = 8.34, 0.26
# each end: the face plane, the plane the solid now stands on, and the sign pointing from the hall inward
BANDS = {'west': (4.194, 3.710, -1.0), 'east': (48.056, 48.056, +1.0)}
# the parapet's own height band, deck to the measured top, plus the fascia below it
HLO, HHI = DECK - SLAB, DECK + 0.76
DLO, DHI = 0.0, 15.4
CLASSES = ['walk', 'night', 'day4k', 'b1', 'b1p', 'b3', 'b4', 'b5', 'b5p', 'b7s', 'b6g', 'b6gp']

lenses = []
for cls in CLASSES:
    try:
        for stem, (cam, _ip) in U.load_class(cls).items():
            q = cam.center - O
            lenses.append((cls, stem, float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])))
    except Exception:
        continue
print('%d posed lenses across %d classes' % (len(lenses), len(set(l[0] for l in lenses))))
print('')

found = {}
for end, (uface, usolid, sign) in BANDS.items():
    lo, hi = (min(uface, usolid), max(uface, usolid)) if usolid != uface else (uface, uface + 0.484 * sign)
    lo, hi = min(lo, hi), max(lo, hi)
    hits = [l for l in lenses
            if lo <= l[2] <= hi and HLO <= l[4] <= HHI and DLO <= l[3] <= DHI]
    found[end] = hits
    print('%s END: the band from u %.3f to %.3f, h %.2f to %.2f, the whole hall width'
          % (end.upper(), lo, hi, HLO, HHI))
    print('   %s' % ('this is the volume the model drew as solid parapet until this evening'
                     if end == 'west' else
                     'this is the volume the model still draws as solid, and it is the control'))
    print('   %d lenses stand in it' % len(hits))
    for cls, stem, cu, cd, ch in sorted(hits, key=lambda x: x[2])[:12]:
        print('      %-6s %-14s u %.3f  d %.2f  h %.3f' % (cls, stem, cu, cd, ch))
    if len(hits) > 12:
        print('      and %d more' % (len(hits) - 12))

print('')
w, e = len(found['west']), len(found['east'])
if w >= 3 and e == 0:
    print('THE RECESS IS CONFIRMED BY OCCUPANCY. %d lenses physically occupied the volume this model drew'
          % w)
    print('as solid stone until this evening, and the east control, whose parapet was measured flush by')
    print('the same scan, contains none. Nobody stands inside a solid, so the west solid is not on its')
    print('face. That is a third instrument agreeing with the station scan and the arrival cap, and it')
    print('shares nothing with either: it reads no pixel value at all, only where a lens was.')
    print('')
    print('AND IT NAMES A GAP IN THE AUDIT. Every one of those lenses was inside the drawn parapet all')
    print('day and the occupancy audit reported a worst excursion of 2 mm, because it checks the walls')
    print('and not the gallery parapets. The parapets are now on the list of solids it should check.')
elif w == 0 and e == 0:
    print('NEITHER BAND CONTAINS A LENS, so this instrument has nothing to say about either end. That is a')
    print('refusal and not a contradiction: no camera in this archive stood close enough to that parapet')
    print('at that height, so occupancy cannot confirm or deny what the photometry found.')
elif e > 0:
    print('BOTH BANDS CONTAIN LENSES, %d west and %d east, so this test is not measuring what it was meant'
          % (w, e))
    print('to. The east parapet was measured flush, so its band is solid stone and should be empty. Lenses')
    print('in it mean the poses put cameras inside masonry at that height generally, and a west count on')
    print('top of that background says nothing. Withdrawn.')
else:
    print('ONLY %d LENS IN THE WEST BAND, which is too few to rest anything on. One camera can be one bad')
    print('pose; the recess keeps standing on the station scan and the arrival cap, and this adds nothing.')
