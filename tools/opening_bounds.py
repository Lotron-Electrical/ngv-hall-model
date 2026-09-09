# 2026-09-09: A CAMERA CANNOT BE INSIDE A WALL. The openings measured by where a person actually stood.
#
# Every measurement of the north openings so far has been photometric: find the jamb edge in a picture and
# compare it with the drawn one. That instrument had to have a follow bias fitted out of it twice, because
# a finder started from the drawn line partly echoes it, and the residual gain is still 0.37.
#
# This is a different kind of evidence entirely and it cannot echo anything. 116 of the newly recovered pan
# poses stand INSIDE an opening, meaning north of the wall's inner face and inside the 0.9 m reveal. A body
# holding a phone occupies real space, so every one of those camera positions is a point the wall is NOT.
# The along-hall spread of the cameras in one opening is therefore a LOWER BOUND on that opening's width,
# and their extremes bound where its jambs can be. No edge is detected, no line is projected, and the drawn
# table is used only to say which opening a camera is in, never to find it.
#
# WHAT IT CAN AND CANNOT SETTLE. It can catch an opening that is drawn too narrow or in the wrong place,
# because a camera would then sit in solid stone. It cannot catch one drawn too WIDE, because nobody is
# obliged to lean on the very edge, and it cannot see a jamb the operator never went near. So a violation
# is a finding and a clean pass is only a consistency check. Both are reported as such.
# The pose position error is 0.02 to 0.10 m by clip, and a phone is held roughly 0.15 m in front of the
# body, so a camera is treated as clearing a jamb only when it is outside by more than that allowance.
#   python tools/opening_bounds.py
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH = -0.090
ALLOW = 0.15          # pose error plus the reach of a hand, the margin a violation has to beat

src = open('index.html', encoding='utf-8').read()
m = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
if not m:
    raise SystemExit('could not read the openings table out of index.html')
OPEN = [[float(x) for x in p.split(',')] for p in re.findall(r'\[([-0-9.]+,[-0-9.]+)\]', m.group(1))]
print('read', len(OPEN), 'openings from index.html')

PAN = sorted(k for k in U.CLASSES if k.endswith('p') and k[:-1] in U.CLASSES)
inside = []
for cls in PAN:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for stem, (cam, _p) in frames.items():
        q = cam.center - O
        cd = float(q @ HD)
        if cd < DNORTH:
            inside.append((cls, stem, float(q @ HU), cd, float(cam.center[1] - O[1])))
print(len(inside), 'cameras stand inside the wall thickness')
print('')

for k, (u0, u1) in enumerate(OPEN):
    mine = [r for r in inside if u0 - 1.0 < r[2] < u1 + 1.0]
    if len(mine) < 5:
        continue
    us = np.array([r[2] for r in mine])
    clips = sorted(set(r[0] for r in mine))
    print('opening', k + 1, 'drawn u', u0, 'to', u1, 'width', round(u1 - u0, 3))
    print('   ', len(mine), 'cameras from', clips, 'span u', round(float(us.min()), 3), 'to',
          round(float(us.max()), 3), 'which is', round(float(us.max() - us.min()), 3), 'm of it')
    west = float(us.min()) - u0
    east = u1 - float(us.max())
    print('    nearest camera to the west jamb', round(west, 3), 'm inside it; to the east jamb',
          round(east, 3), 'm inside it')
    bad = []
    if west < -ALLOW:
        bad.append('a camera stands ' + str(round(-west, 3)) + ' m WEST of the drawn west jamb')
    if east < -ALLOW:
        bad.append('a camera stands ' + str(round(-east, 3)) + ' m EAST of the drawn east jamb')
    if bad:
        for b in bad:
            print('    VIOLATION:', b, 'which is more than the', ALLOW, 'm allowance')
        print('    the opening cannot be where it is drawn, or cannot be that narrow')
    else:
        print('    no violation: every camera lies within the drawn opening, so the table is consistent')
        print('    with where a person could physically stand, though a jamb nobody approached is untested')
    print('')
