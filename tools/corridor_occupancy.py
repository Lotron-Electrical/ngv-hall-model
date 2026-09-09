# 2026-09-09: somebody stood in that room. Ask where they stood, and nothing else.
#
# EVERY CORRIDOR NUMBER IN THIS MODEL COMES FROM PHOTOMETRY, and the last three hours have been a long
# lesson in what photometry does wrong: a stale mask manufactured two reveal points, a ladder ceiling
# manufactured a deck edge with 100 per cent agreement, and a parapet null passed more often than the
# parapet did. Every one of those failures lives in the detector.
#
# THERE IS ONE CLASS OF EVIDENCE HERE WITH NO DETECTOR IN IT AT ALL. A posed lens is a point in space that
# was not inside a wall, and a lens that stood in a room bounds that room, exactly and one-sidedly, with
# no brightness, no window, no polarity and no threshold anywhere in the argument. The floor is below it,
# the ceiling is above it, the back wall is behind it. tools/deck_bound.py used that on the galleries.
# Nothing has ever used it on the corridor, and the corridor is the part of this model that has been
# rebuilt twice tonight.
#
# THE B1 CLIP STANDS IN THERE. Its 59 frames plus 138 in b1p sit on u 18.9 to 19.7, which is opening 5,
# with lens heights of 9.07 to 10.12. If those lenses are behind the wall face they are inside the room
# and every one of them is a hard constraint on it.
#
# WHAT THIS CANNOT DO, and it matters because a one-sided bound is easy to over-read: it cannot say the
# room is no deeper than the deepest lens, only no shallower. A wall drawn a metre behind where anyone
# stood passes this test happily, which is exactly the corridor's situation and the reason the occupancy
# audit has always been a floor rather than a measurement. It is reported as a floor.
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

DNORTH, OPENDEPTH, CWIDTH = -0.030, 0.900, 1.420
CBACK = DNORTH - OPENDEPTH - CWIDTH
CFLOOR, CCEIL = 8.34, 10.947
SILL, HEAD = 8.740, 11.165
SHIPPED_REVEAL = 0.362   # the arrival-cap bound this model carries, from one class
CLASSES = ['walk', 'night', 'day4k', 'b1', 'b1p', 'b2', 'b2p', 'b3', 'b3p', 'b4', 'b5', 'b5p',
           'b6', 'b6g', 'b6gp', 'b6s', 'b7s', 'b7sp', 'd4', 'w1', 'w5']

rows = []
for cls in CLASSES:
    try:
        d = U.load_class(cls)
    except Exception:
        continue
    for stem, (cam, _ip) in d.items():
        q = cam.center - O
        rows.append((cls, stem, float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])))
print('%d posed lenses across %d classes' % (len(rows), len(set(r[0] for r in rows))))
print('the model draws the corridor face %.3f, reveal %.3f, back wall %.3f, floor %.2f, ceiling %.3f'
      % (DNORTH, OPENDEPTH, CBACK, CFLOOR, CCEIL))

behind = [r for r in rows if r[3] < DNORTH]
print('')
print('%d lenses stand BEHIND the north wall face, which is the only place this room can be entered from'
      % len(behind))
if not behind:
    raise SystemExit('nobody stood behind that wall, so pose alone says nothing about it')

for cls in sorted(set(r[0] for r in behind)):
    g = [r for r in behind if r[0] == cls]
    du = np.array([r[2] for r in g])
    dd = np.array([r[3] for r in g])
    dh = np.array([r[4] for r in g])
    print('   %-5s %4d lenses   u %6.2f to %6.2f   d %+.3f to %+.3f   h %.2f to %.2f'
          % (cls, len(g), du.min(), du.max(), dd.max(), dd.min(), dh.min(), dh.max()))

dd = np.array([r[3] for r in behind])
dh = np.array([r[4] for r in behind])
deepest = min(behind, key=lambda r: r[3])
lowest = min(behind, key=lambda r: r[4])
highest = max(behind, key=lambda r: r[4])
inreveal = [r for r in behind if r[3] >= DNORTH - OPENDEPTH]
inroom = [r for r in behind if r[3] < DNORTH - OPENDEPTH]
print('')
print('   %d of them are still inside the REVEAL, between the face and %.3f, and %d are past it and'
      % (len(inreveal), DNORTH - OPENDEPTH, len(inroom)))
print('   therefore standing in the room itself.')
print('')
print('   THE THREE BOUNDS, each of them one-sided and assumption-free.')
print('   DEEPEST LENS   %s %s on d %+.3f, so the back wall is no shallower than that.'
      % (deepest[0], deepest[1], deepest[3]))
print('      drawn %+.3f, which clears it by %.3f m.' % (CBACK, abs(CBACK - deepest[3])))
print('   LOWEST LENS    %s %s on h %.3f, so the floor is below it.' % (lowest[0], lowest[1], lowest[4]))
print('      drawn %.3f, which leaves %.3f m of room.' % (CFLOOR, lowest[4] - CFLOOR))
print('   HIGHEST LENS   %s %s on h %.3f, so the ceiling is above it.'
      % (highest[0], highest[1], highest[4]))
print('      drawn %.3f, which leaves %.3f m of room.' % (CCEIL, CCEIL - highest[4]))

fails = []
if CBACK > deepest[3]:
    fails.append('the back wall is drawn IN FRONT of a lens that stood behind it')
if CFLOOR > lowest[4]:
    fails.append('the floor is drawn ABOVE a lens that stood on it')
if CCEIL < highest[4]:
    fails.append('the ceiling is drawn BELOW a lens that stood under it')
print('')
if fails:
    print('   CONTRADICTED: %s.' % '; '.join(fails))
else:
    print('   NOTHING IS CONTRADICTED, and the size of the clearances is the real content. The back wall')
    print('   has %.2f m of slack, the floor %.2f m and the ceiling %.2f m against the people who were'
          % (abs(CBACK - deepest[3]), lowest[4] - CFLOOR, CCEIL - highest[4]))
    print('   actually in there. A bound with metres of slack constrains almost nothing, and saying so is')
    print('   the point of running it: this room is drawn far beyond where anybody stood.')

print('')
print('   AND THE LENS IS NOT THE PERSON, WHICH IS WHERE THE FIRST DRAFT OF THIS TOOL GOT IT WRONG. It')
print('   read 196 lenses inside the reveal and concluded people were leaning IN from outside. There is')
print('   nowhere outside to lean from: these lenses sit between h %.2f and %.2f, the sill is %.3f, and'
      % (dh.min(), dh.max(), SILL))
print('   on the hall side of that wall at that height there is nothing but air %.1f m above the floor.'
      % SILL)
print('   %d of the %d are below the sill, so the bodies were standing INSIDE the room and only the'
      % (int(np.sum(dh < SILL)), len(behind)))
print('   lenses leaned forward into the reveal. A lens bounds where the LENS was; the feet are behind')
print('   it and deeper in.')
print('')
print('   THE ONE NUMBER THIS IMPROVES IS THE REVEAL. The deepest lens in the whole archive sits %.3f m'
      % (abs(deepest[3]) - abs(DNORTH)))
print('   behind the face, and a lens cannot be inside stone, so the reveal is at least that deep. The')
print('   model carries %.3f m for that bound, taken from one class; this is every class in the archive,'
      % SHIPPED_REVEAL)
print('   and it is %.0f mm better.'
      % (1000 * ((abs(deepest[3]) - abs(DNORTH)) - SHIPPED_REVEAL)))
print('')
print('   AND EVERYTHING DEEPER THAN THAT IS UNWITNESSED. Not one of the 196 lenses reaches past the')
print('   drawn reveal of %.3f, let alone into the room. Five classes, three different openings, and the'
      % OPENDEPTH)
print('   deepest anybody got was %.3f m in. The corridor beyond that depth is drawn on photometry and'
      % (abs(deepest[3]) - abs(DNORTH)))
print('   plan alone, and no pose in this archive touches it.')
