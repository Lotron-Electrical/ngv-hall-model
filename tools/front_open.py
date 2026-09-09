# 2026-09-09: THE BALCONY FRONT IS OPEN ABOVE ITS UPSTAND, AND THAT IS WHAT IDENTIFIES THE MEASURED EDGE.
#
# Two numbers on these balconies have been sitting side by side looking like a contradiction. From the deck
# the arrivals cap a SOLID front on 8.818. From the hall floor a horizontal edge fits on 9.799 west and
# 9.865 east, split-validated to 10 and 15 mm. A solid front cannot be both.
#
# THE OPERATOR SETTLES IT WITHOUT ANY MORE INSTRUMENTS. His lens stands at h 9.56 to 9.74 on the west deck,
# which is BELOW 9.799, and 0.86 m behind the face. If the front were solid up to that edge, a lens below
# the top of it could see nothing but the upper hall and the ceiling: every downward sightline would end on
# stone. The photographs are full of hall floor with people sitting on it, and the arrivals cross the face
# plane as low as 8.70. So the front passes light from 8.70 up past the lens and on to the top edge, which
# is what an open balustrade does and a parapet does not.
#
# AND THE DETECTOR PARITY NAMES THE EDGE. It was told to find a BRIGHT-BELOW, DARK-ABOVE step: lit balcony
# front underneath, dark recess over it. That is the top of the lit front. The opposite feature, the top of
# the dark recess, has the opposite parity and was never eligible.
#
# So the three readings are one object: a low solid upstand, an open rail above it, and the top of that
# rail where the hall floor sees it. This prints the arithmetic rather than asserting it.
#   python tools/front_open.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
DECK = 8.34
ENDS = {'west': (4.194, +1.0, 9.020, 9.799, 8.703, 8.818),
        'east': (48.056, -1.0, 9.110, 9.865, 8.735, 9.078)}
CLASSES = ('b7sp', 'b7s', 'b3p', 'b3', 'b6gp', 'b6g')

seen = {}
for cls in CLASSES:
    try:
        for k, v in U.load_class(cls).items():
            seen.setdefault(k, v)
    except Exception:
        pass

for end in ('west', 'east'):
    uf, out, solid, edge, lowest, cap = ENDS[end]
    lens = []
    for stem, (cam, _ip) in seen.items():
        q = cam.center - O
        cu, ch = float(q @ HU), float(cam.center[1] - O[1])
        if ch < 8.7 or abs(cu - uf) > 4.2 or (cu - uf) * out > 0.35:
            continue
        if (uf - cu) * out < 0.6:
            continue                                   # only the lenses set back from the face
        lens.append((stem, cu, ch, abs(cu - uf)))
    if len(lens) < 4:
        print('%s: only %d set-back lenses' % (end, len(lens)))
        continue
    LH = np.array([r[2] for r in lens])
    LD = np.array([r[3] for r in lens])
    print('')
    print('%s END, %d lenses set back %.2f to %.2f m from the face'
          % (end.upper(), len(lens), float(LD.min()), float(LD.max())))
    print('   the lens sits between h %.3f and %.3f; the measured top edge is %.3f'
          % (float(LH.min()), float(LH.max()), edge))
    print('   %d of those %d lenses are BELOW that edge, the lowest by %.3f m'
          % (int((LH < edge).sum()), len(lens), edge - float(LH.min())))
    worst = float(LH.min())
    dd = float(LD[int(np.argmin(LH))])
    print('   if the front were solid to %.3f, the lowest sightline out of the lowest lens would RISE at'
          % edge)
    print('   %+.3f, so that camera could not see the hall floor at all, at any distance'
          % ((edge - worst) / dd))
    print('   the arrivals from these same cameras cross the face as low as h %.3f, %.3f m BELOW the lens'
          % (lowest, worst - lowest))
    print('   itself. Light came through the front, so the front is open there.')
    print('   solid drawn to %.3f, capped by the arrivals on %.3f, open rail measured to %.3f'
          % (solid, cap, edge))
    print('   that is an upstand of at most %.3f and a rail top of %.3f above the deck %.3f'
          % (cap - DECK, edge - DECK, DECK))
