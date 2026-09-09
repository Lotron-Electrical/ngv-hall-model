# 2026-09-09: THE CORRIDOR MEASURED FROM CAMERAS STANDING IN IT.
#
# Everything the hall floor can say about this room has been said and it is not much: 116 cameras sit
# inside the north openings, none of them looks north, and the head soffit stands over the reveal so an
# upward sightline from the floor ends on its underside. The corridor's width, floor and ceiling have
# therefore rested on inference. But the b6 gallery clip was SHOT INSIDE the room, and a camera standing
# somewhere is the one measurement that cannot be argued with: that point is free space, the floor is
# below it and the ceiling above it, and no edge finder or follow gain is involved.
#
# THAT SENTENCE ABOUT b6 IS WRONG AND THE RUN OF 2026-09-10 IS WHAT FOUND IT. Every posed b6 frame in the
# archive, b6g b6gp and b6s together, stands on d +13.40 to +23.69, which is the SOUTH side of a hall
# 15.364 m wide: the far side, thirteen metres from the north wall. Whatever that clip shows, none of its
# posed frames is inside this room, so none of them can bound it. Of 416 posed frames across every
# balcony clip, 146 sit north of the wall face and every single one of them is inside an opening, in the
# wall thickness, the deepest 0.452 m back where the reveal alone is 0.900 deep.
# NOBODY HAS EVER STOOD IN THIS ROOM WITH A POSED CAMERA. The depth, the ceiling and the floor all rest
# on the lamp locus and on inference, and this tool cannot add to them; what it can do is refuse them,
# and it does not.
#
# This reads the poses alone. It reports where in the room the operator actually walked, in the hall's own
# coordinates, and turns that into hard bounds: the back wall is at least as far north as the deepest
# camera, the floor is at most the lowest camera height less the height a phone is held at, and the
# ceiling is at least the highest camera height. Bounds, not estimates, each stated with what it assumes.
#
# AMENDED 2026-09-10, AND THE AMENDMENT IS THE POINT. This tool hard-coded the room it was testing:
# width 2.0, ceiling 11.4, wall face d -0.090. The model has since moved all three. The back wall went
# from d -2.990 to d -2.350 and the ceiling from 11.4 to 10.947 (corridor_locus.py, the anchored ceiling
# locus cut by the highest lamp measured inside the room), and the wall face went to d -0.030.
# BOTH OF THOSE CHANGES MADE THE MODEL EASIER TO REFUTE. A shallower room is refuted by a deeper camera
# and a lower ceiling by a taller one, and the one test that could refuse them was never re-run against
# them. So it now reads the room out of index.html at run time and cannot go stale again.
#
# AND A SINGLE POSE IS NOT ALLOWED TO MOVE ANYTHING. The archive's own worst classes miss near-field rays
# by a median 0.179 and 0.200 m, so one camera 0.1 m past a wall is pose error, not a discovery. A
# refutation here needs the frames of MORE THAN ONE CLIP to agree, and it reports the fifth deepest as
# well as the deepest so a single outlier is visible rather than decisive.
#   python tools/corridor_inside.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('b6gp', 'b6g', 'b6s', 'b1p', 'b3p', 'b5p', 'b7sp', 'b1', 'b3', 'b4', 'b5', 'b7s')
POSE_SLOP = 0.20                 # the archive's own worst median near-field ray miss


def model():
    """the wall face, the reveal, the room and the openings, as index.html draws them right now"""
    src = io.open('index.html', encoding='utf-8').read()
    g = lambda p: float(re.search(p, src).group(1))
    m = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
    return {'face': g(r'dNorth:\s*(-?[0-9.]+)'),
            'reveal': g(r'openDepth:\s*([0-9.]+)'),
            'width': g(r'corridor:\{width:([0-9.]+)'),
            'floor': g(r'corridor:\{width:[0-9.]+,\s*floor:([0-9.]+)'),
            'ceil': g(r'corridor:\{width:[0-9.]+,\s*floor:[0-9.]+,\s*ceil:([0-9.]+)'),
            'openings': [[float(a), float(b)]
                         for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', m.group(1))]}


M = model()
DN = M['face']
BACK = DN - M['reveal'] - M['width']
print('THE ROOM AS index.html DRAWS IT TODAY')
print('   wall face d %.3f, reveal %.3f back, room %.3f deeper, so the back wall stands on d %.3f'
      % (DN, M['reveal'], M['width'], BACK))
print('   floor h %.3f, ceiling h %.3f' % (M['floor'], M['ceil']))

cams = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for fr, v in frames.items():
        cams.setdefault(fr, (cls, v[0]))

rows = []
for fr, (cls, cam) in cams.items():
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    if cd >= DN:
        continue                                  # still on the hall side of the wall face
    rows.append((fr, cls, cu, cd, ch))

print('')
print(len(cams), 'distinct posed frames across the balcony clips')
print(len(rows), 'of them have their camera centre NORTH of the wall face d %.3f' % DN)
if len(rows) < 5:
    raise SystemExit('too few to bound anything')

a = np.array([[r[2], r[3], r[4]] for r in rows])
print('   they stand u %.2f to %.2f, d %.3f to %.3f, h %.2f to %.2f'
      % (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(), a[:, 2].min(), a[:, 2].max()))
byc = {}
for r in rows:
    byc.setdefault(r[1], []).append(r)
for c in sorted(byc):
    b = np.array([[x[2], x[3], x[4]] for x in byc[c]])
    print('     %-5s %4d frames, u %.2f to %.2f, deepest d %.3f, h %.2f to %.2f'
          % (c, len(b), b[:, 0].min(), b[:, 0].max(), b[:, 1].min(), b[:, 2].min(), b[:, 2].max()))

inop = 0
for r in rows:
    if any(u0 - 0.1 <= r[2] <= u1 + 0.1 for u0, u1 in M['openings']):
        inop += 1
print('')
print('   %d of them stand within an opening, in the wall thickness, and %d stand clear of every opening'
      % (inop, len(rows) - inop))

print('')
print('WHAT THAT BOUNDS, taking nothing but the camera centres')
ds = np.sort(a[:, 1])
dmin, d5 = float(ds[0]), float(ds[min(4, len(ds) - 1)])
past = [r for r in rows if r[3] < BACK - POSE_SLOP]
clips = sorted(set(r[1] for r in past))
print('   the deepest camera is d %.3f and the fifth deepest d %.3f, against a back wall drawn on d %.3f'
      % (dmin, d5, BACK))
print('   %d cameras stand more than the archive pose slop of %.2f m past that wall, across %d clips'
      % (len(past), POSE_SLOP, len(clips)))
if len(past) >= 5 and len(clips) >= 2:
    print('   THE ROOM IS REFUTED AS DRAWN: the operator walked %.3f m past its back wall, and it is not'
          % (BACK - dmin))
    print('   one bad pose because %d frames from %s agree.' % (len(past), ', '.join(clips)))
elif past:
    print('   NOT REFUTED, AND WORTH SAYING WHY NOT: %d frames from %d clip(s) sit past the wall, which')
    print('   is under the bar this tool sets, so it is read as pose error rather than as a discovery.')
else:
    print('   every camera fits inside the drawn room, so the depth is not refuted and not confirmed:')
    print('   a person who walks down the middle of a corridor never touches its walls.')
hs = np.sort(a[:, 2])
hmin, hmax = float(hs[0]), float(hs[-1])
h5 = float(hs[max(0, len(hs) - 5)])
print('')
print('   the cameras sit h %.2f to %.2f, and the fifth highest is %.2f' % (hmin, hmax, h5))
print('   the ceiling must be above the tallest of them, so above h %.2f, against the drawn %.3f'
      % (hmax, M['ceil']))
tall = [r for r in rows if r[4] > M['ceil'] - POSE_SLOP]
tclips = sorted(set(r[1] for r in tall))
if len(tall) >= 5 and len(tclips) >= 2:
    print('   THE CEILING IS REFUTED AS DRAWN: %d cameras from %s stand within %.2f m of it or above it.'
          % (len(tall), ', '.join(tclips), POSE_SLOP))
else:
    print('   the drawn ceiling clears every camera by %.3f m, so it is not refuted by anyone standing'
          % (M['ceil'] - hmax))
    print('   in there, which is the only thing this test can say about it.')
print('')
print('   a phone is carried about 1.40 to 1.60 m over the floor, so the floor those people stood on is')
print('   h %.2f to %.2f, against the drawn %.3f' % (hmin - 1.60, hmin - 1.40, M['floor']))
if M['floor'] < hmin - 1.60 - 0.15 or M['floor'] > hmin - 1.40 + 0.15:
    print('   THE DRAWN FLOOR IS OUTSIDE THAT RANGE, which is worth a look rather than a change: the')
    print('   carry height is an assumption and the only soft step in this whole test.')
else:
    print('   the drawn floor sits inside that range, on the one assumption this test makes.')
