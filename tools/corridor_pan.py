# 2026-09-09: DOES ANY PAN-CHAINED FRAME STAND BEHIND THE NORTH WALL, and does any look INTO the corridor
# rather than back out of it.
#
# The corridor behind the brick wall is the last part of the model resting on nothing measured: its width
# comes from the 1968 plan and its ceiling was inferred from a lamp. A census of the whole archive found
# 1,128 registered cameras and not one inside the corridor, the deepest sitting just under half a metre in
# and looking back into the hall. That census could only count frames that had poses, and until today two
# thirds of Lloyd's balcony footage had none.
#
# So the question is worth asking again of the frames that just gained poses. Two things are printed: every
# frame north of the wall's inner face, and separately every frame that is BOTH north of it and looking
# north, because a camera in the opening looking back at the hall says nothing about the room behind it.
# The opening reveal is 0.9 m deep, so a camera between the face and that depth is inside the reveal and
# anything deeper is in the corridor proper.
#   python tools/corridor_pan.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DNORTH = -0.090
REVEAL = 0.9

# the pan classes name themselves: each is its clip's name with a p, so the list cannot fall out of date
PAN = sorted(k for k in U.CLASSES if k.endswith('p') and k[:-1] in U.CLASSES)

rows = []
for cls in PAN:
    try:
        frames = U.load_class(cls)
    except Exception as e:
        print(cls, 'could not load', e)
        continue
    for stem, (cam, _path) in frames.items():
        q = cam.center - O
        look = cam.R.T @ np.array([0.0, 0.0, 1.0])
        rows.append((cls, stem, float(q @ HU), float(q @ HD), float(cam.center[1] - O[1]),
                     float(look @ HD), float(look[1])))
print(len(rows), 'posed frames across', len(PAN), 'pan classes')

behind = [r for r in rows if r[3] < DNORTH]
print('')
print(len(behind), 'stand north of the wall inner face, d below', DNORTH)
if behind:
    depth = np.array([r[3] for r in behind])
    print('   deepest', round(float(depth.min()), 3), 'which is',
          round(float(DNORTH - depth.min()), 3), 'm past the face; the reveal is', REVEAL, 'm deep')
    for r in sorted(behind, key=lambda z: z[3])[:12]:
        print('   ', r[0], r[1], 'u', round(r[2], 2), 'd', round(r[3], 3), 'h', round(r[4], 2),
              '| looking across', round(r[5], 2), 'down', round(r[6], 2))

looking = [r for r in behind if r[5] < -0.4]
print('')
print(len(looking), 'of those are ALSO looking north, into the room rather than back out of it')
for r in sorted(looking, key=lambda z: z[3])[:12]:
    print('   ', r[0], r[1], 'u', round(r[2], 2), 'd', round(r[3], 3), 'h', round(r[4], 2),
          '| looking across', round(r[5], 2), 'down', round(r[6], 2))

deep = [r for r in rows if r[3] < DNORTH - REVEAL]
print('')
print(len(deep), 'stand past the reveal, in the corridor proper')
if not deep:
    print('   NOTHING. The pan poses reach into the opening and stop there, so the corridor width and')
    print('   ceiling remain unmeasured and index.html must keep saying so.')
