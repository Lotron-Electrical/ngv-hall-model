# 2026-09-09: THE CORRIDOR MEASURED FROM CAMERAS STANDING IN IT.
#
# Everything the hall floor can say about this room has been said and it is not much: 116 cameras sit
# inside the north openings, none of them looks north, and the head soffit stands over the reveal so an
# upward sightline from the floor ends on its underside. The corridor's width 2.0, floor 8.34 and ceiling
# 11.4 have therefore rested on inference. But the b6 gallery clip was SHOT INSIDE the room, and a camera
# standing somewhere is the one measurement that cannot be argued with: that point is free space, the
# floor is below it and the ceiling above it, and no edge finder or follow gain is involved.
#
# This reads the poses alone. It reports where in the room the operator actually walked, in the hall's own
# coordinates, and turns that into hard bounds: the back wall is at least as far north as the deepest
# camera, the floor is at most the lowest camera height less the height a phone is held at, and the ceiling
# is at least the highest camera height. Bounds, not estimates, and each one stated with what it assumes.
#   python tools/corridor_inside.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.090                      # the north wall's inner face
DRAWN_WIDTH, DRAWN_FLOOR, DRAWN_CEIL = 2.0, 8.34, 11.4
OPENINGS = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.770, 19.983],
            [22.418, 23.631], [26.066, 27.279], [29.816, 31.028], [33.495, 34.706], [37.177, 38.383],
            [40.906, 42.118], [44.526, 45.739]]
CLASSES = ('b6gp', 'b6g', 'b6s', 'b1p', 'b3p', 'b5p', 'b7sp', 'b1', 'b3', 'b4', 'b5', 'b7s')

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
    fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
    fu, fd = float(fwd @ HU), float(fwd @ HD)
    rows.append((fr, cls, cu, cd, ch, fu, fd, float(fwd[1])))

print(len(cams), 'distinct posed frames across the balcony clips')
print(len(rows), 'of them have their camera centre NORTH of the wall face d %.3f' % DN)
if not rows:
    raise SystemExit('none, so nothing here can measure the room')

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

# a camera inside an opening is standing in the wall's thickness, not in the room behind it
inop = []
for r in rows:
    for u0, u1 in OPENINGS:
        if u0 - 0.1 <= r[2] <= u1 + 0.1:
            inop.append(r)
            break
deep = [r for r in rows if r not in inop]
print('')
print('   %d of them stand within an opening (in the wall thickness), %d stand clear of every opening'
      % (len(inop), len(deep)))

print('')
print('WHAT THAT BOUNDS, taking nothing but the camera centres')
dmin = float(a[:, 1].min())
print('   the deepest camera is d %.3f, which is %.3f m north of the wall face.' % (dmin, DN - dmin))
print('   the room is drawn %.2f m deep, so its back wall is drawn on d %.3f.' % (DRAWN_WIDTH, DN - DRAWN_WIDTH))
if DN - dmin > DRAWN_WIDTH:
    print('   THE OPERATOR WALKED PAST THE DRAWN BACK WALL. The room is deeper than 2.00 m.')
else:
    print('   every camera fits inside the drawn room, so the width is not refuted and not confirmed:')
    print('   a person who walks down the middle of a corridor never touches its walls.')
hmin, hmax = float(a[:, 2].min()), float(a[:, 2].max())
print('   the cameras sit h %.2f to %.2f. A phone is carried about 1.40 to 1.60 m over the floor, so' % (hmin, hmax))
print('   the floor those people stood on is h %.2f to %.2f, against the drawn %.2f.'
      % (hmin - 1.60, hmin - 1.40, DRAWN_FLOOR))
print('   the ceiling is above the tallest of them, so it is higher than h %.2f, against the drawn %.2f.'
      % (hmax, DRAWN_CEIL))
