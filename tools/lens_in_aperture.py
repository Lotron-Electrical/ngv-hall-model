# 2026-09-09: the openings tested by where people stood, with no detector anywhere in it.
#
# NOBODY STANDS INSIDE A SOLID. That principle settled the east parapet earlier today and it applies to
# the north wall with more force, because three clips were shot from INSIDE its apertures: b1 in opening 5,
# b5 in opening 6, b4 in opening 11, 317 posed lenses between them and their pans, every one at gallery
# height and within half a metre of the wall plane. A lens that is inside an opening is a point that was
# not inside masonry, and that is a hard one-sided bound on the jamb either side of it. No pixels, no
# contrast threshold, no polarity: just a position that has to be in a hole.
#
# AND IT IS THE FIRST INDEPENDENT TEST OF THE JAMB MOVE. The twelve openings were shifted east this
# evening on nine fitted lines, and openings 5, 6 and 11 are exactly the three the operator stood in. If
# the shift is right the lenses stay inside; if it pushed a jamb past somebody's head, that shows up here
# and nowhere else. The lenses were never used to derive the shift, so this is a real check and not a
# restatement of it.
#
# WHAT COUNTS AS A VIOLATION IS SET BY THE POSES THEMSELVES, not by whatever makes the answer pleasant.
# b1 misses itself by 0.061 m in the near field, b5 by 0.066 and b4 by 0.067 (tools/pose_selfcheck.py), so
# a lens sitting a couple of centimetres outside a jamb is inside its own uncertainty and says nothing.
# The bar used here is the clip's own self-miss.
import os
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
SELFMISS = {'b1': 0.061, 'b1p': 0.068, 'b4': 0.067, 'b5': 0.066, 'b5p': 0.069}
CLASSES = os.environ.get('CLASSES', 'b1 b1p b4 b5 b5p').split()

src = open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:(\[\[.*?\]\]),', src, re.S)
OPEN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEAD = float(re.search(r'openY:\[[0-9.]+,\s*([0-9.]+)\]', src).group(1))
DNORTH = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
print('the model draws %d openings, sill %.3f head %.3f, wall face d %.3f'
      % (len(OPEN), SILL, HEAD, DNORTH))

inside = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        print('%-4s could not be loaded' % cls)
        continue
    for stem, (cam, ip) in frames.items():
        q = cam.center - O
        cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
        if not (SILL < ch < HEAD):
            continue                       # only lenses at aperture height can be in an aperture
        # AND ONLY LENSES BEHIND THE FACE PLANE, which the first run of this got wrong and a violation
        # caught. It allowed anything within a metre of the wall, so it counted b4 frames sitting 0.87 m
        # OUT in the hall, leaning back to shoot along the wall, and then reported one of them as 0.241 m
        # inside the east jamb of opening 11. A lens in front of the face is not in the hole at all and no
        # jamb constrains it. Only a lens between the face and the back of the reveal is standing in an
        # aperture, and only that lens is evidence about where the jambs are.
        if cd > DNORTH or cd < -1.5:
            continue
        k = min(range(len(OPEN)), key=lambda i: abs(cu - 0.5 * (OPEN[i][0] + OPEN[i][1])))
        inside.setdefault(k, []).append((cls, stem, cu, cd, ch))

print('')
print('%d lenses sit at aperture height within the wall zone, spread over %d openings'
      % (sum(len(v) for v in inside.values()), len(inside)))
print('')
bad = []
for k in sorted(inside):
    lo, hi = OPEN[k]
    rec = inside[k]
    us = np.array([r[2] for r in rec])
    ds = np.array([r[3] for r in rec])
    hs = np.array([r[4] for r in rec])
    wmarg = float(us.min() - lo)            # positive = clear of the west jamb
    emarg = float(hi - us.max())            # positive = clear of the east jamb
    wclip = rec[int(np.argmin(us))][0]
    eclip = rec[int(np.argmax(us))][0]
    print('opening %2d  u %.3f to %.3f, %3d lenses from %s'
          % (k + 1, lo, hi, len(rec), ', '.join(sorted({r[0] for r in rec}))))
    print('            lenses occupy u %.3f to %.3f, d %+.3f to %+.3f, h %.3f to %.3f'
          % (us.min(), us.max(), ds.min(), ds.max(), hs.min(), hs.max()))
    print('            clearance to the west jamb %+.3f m (%s, bar %.3f), to the east %+.3f m (%s)'
          % (wmarg, wclip, SELFMISS.get(wclip, 0.07), emarg, eclip))
    for marg, side, clip in ((wmarg, 'west', wclip), (emarg, 'east', eclip)):
        if marg < -SELFMISS.get(clip, 0.07):
            bad.append((k + 1, side, marg, clip))
    # THE REVEAL, WHICH COMES FREE. The deepest lens between a pair of jambs was standing in the reveal,
    # so the reveal is at least that deep. It is a floor and not a value, and it is stated as one.
    print('            the deepest lens sits %.3f m behind the wall face, so the reveal is at least that'
          % max(0.0, DNORTH - float(ds.min())))

print('')
if bad:
    for k, side, marg, clip in bad:
        print('VIOLATION: opening %d, a %s lens is %.3f m into the %s jamb, past its own %.3f m self-miss'
              % (k, clip, -marg, side, SELFMISS.get(clip, 0.07)))
else:
    print('NO LENS IS INSIDE A JAMB. Every one of them stands in a hole, within its own pose error, so')
    print('the openings as drawn survive a test built only out of where people put the camera.')

allrec = [r for v in inside.values() for r in v]
if allrec:
    dmin = min(r[3] for r in allrec)
    print('')
    print('across all of them the deepest lens is %s at d %+.3f, a floor of %.3f m on the reveal depth,'
          % (min(allrec, key=lambda r: r[3])[1], dmin, DNORTH - dmin))
    print('which is weaker than the 0.9 m the traced rays already give and so changes nothing')
