# 2026-09-09: NOBODY STOOD IN A WALL. Every posed camera in the archive tested against the model's solids.
#
# Every measurement in this project so far has been an EDGE measurement: find a line in a picture, compare
# it with the drawn line. That family of instruments has needed a follow bias fitted out of it twice, and
# three separate results have had to be withdrawn when the instrument turned out to be reading the model
# back. This is a different kind of evidence and it has none of that failure mode.
#
# A registered camera is a point in space where a person and a phone physically were. The model says which
# points are stone. The two cannot both be right where they disagree, and the test needs no edge detector,
# no search window and no drawn line to start from. It is also the only test that covers the balconies, the
# long walls and the corridor in one pass, because it asks the same question of all of them.
#
# WHAT IT CAN PROVE AND WHAT IT CANNOT. A camera inside a solid is a hard contradiction: either the solid
# is in the wrong place or it should not be there. A clean pass proves only that nothing is drawn ACROSS
# somewhere a person went; a wall drawn a metre too far into a room nobody entered passes happily. So a
# violation is a finding and a pass is a bound, and both are reported as what they are.
#
# THE ALLOWANCE. A pose carries error: centimetres for the accepted frames, 0.02 to 0.10 m for the pan
# ones. A phone is also held ahead of the body, so the camera can legitimately sit a little inside a
# surface the person is leaning over. Only excursions past the allowance are called violations, and the
# distribution of the small ones is printed too, because a systematic 40 mm bias across hundreds of
# cameras is itself a finding even when no single camera breaks the rule.
#   python tools/occupancy_audit.py
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
ALLOW = 0.20

src = open('index.html', encoding='utf-8').read()


def grab(pattern, default=None):
    m = re.search(pattern, src)
    if m is None:
        if default is None:
            raise SystemExit('could not read ' + pattern)
        return default
    return float(m.group(1))


mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(x) for x in p.split(',')] for p in re.findall(r'\[([-0-9.]+,[-0-9.]+)\]', mo.group(1))]
OPENY = [grab(r'openY:\[([0-9.]+),'), grab(r'openY:\[[0-9.]+,\s*([0-9.]+)\]')]
DN = grab(r'dNorth:(-?[0-9.]+)')
DS = grab(r'dSouth:([0-9.]+)')
UMIN = grab(r'uMin:([0-9.]+)')
UMAX = grab(r'uMax:([0-9.]+)')
print('north face d', DN, 'south face d', DS, 'ends u', UMIN, 'to', UMAX)
FLOORS = [grab(r'floors:\[([0-9.]+),'), grab(r'floors:\[[0-9.]+,\s*([0-9.]+)\]')]
SLAB = grab(r'slab:([0-9.]+)')
FACE = grab(r'face:([0-9.]+)')
WFACE = UMIN + FACE
EFACE = UMAX - FACE
OPENDEPTH = grab(r'openDepth:([0-9.]+)')
CWIDTH = grab(r'corridor:\{width:([0-9.]+)')
print('openings', len(OPEN), 'sill', OPENY[0], 'head', OPENY[1])
print('gallery floors', FLOORS, 'slab', SLAB, 'parapet faces u', round(WFACE, 3), 'and', round(EFACE, 3))
print('reveal', OPENDEPTH, 'corridor width', CWIDTH)
print('')


def in_opening(u, y):
    if not (OPENY[0] < y < OPENY[1]):
        return False
    return any(a <= u <= b for a, b in OPEN)


rows = []
for cls in sorted(U.CLASSES):
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for stem, (cam, _p) in frames.items():
        q = cam.center - O
        rows.append((cls, stem, float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])))
print(len(rows), 'posed cameras across', len(set(r[0] for r in rows)), 'classes')
print('')

tests = []
for cls, stem, cu, cd, cy in rows:
    # NORTH WALL. Solid north of its inner face except where an opening is cut through it.
    if cd < DN and not in_opening(cu, cy):
        tests.append(('north wall', DN - cd, cls, stem, cu, cd, cy))
    # SOUTH WALL. Solid south of its inner face, and it is glazed rather than pierced.
    if cd > DS:
        tests.append(('south wall', cd - DS, cls, stem, cu, cd, cy))
    # THE TWO ENDS. Solid beyond the end-wall inner surfaces.
    if cu < UMIN:
        tests.append(('west end wall', UMIN - cu, cls, stem, cu, cd, cy))
    if cu > UMAX:
        tests.append(('east end wall', cu - UMAX, cls, stem, cu, cd, cy))
    # THE FLOOR. Nobody stands below it.
    if cy < 0.0:
        tests.append(('below the hall floor', -cy, cls, stem, cu, cd, cy))
    # THE END GALLERY SLABS. Between an end wall and its parapet face the two decks are solid concrete from
    # the slab soffit up to the walking surface. A camera in there is the most likely place for a real error
    # to show, because it is exactly the volume a one-storey-down pose alias would put a balcony camera in.
    for fl in FLOORS:
        if UMIN <= cu <= WFACE or EFACE <= cu <= UMAX:
            if fl - SLAB < cy < fl and 0.0 < cd < DS:
                tests.append(('an end gallery slab', min(cy - (fl - SLAB), fl - cy), cls, stem, cu, cd, cy))
    # THE CORRIDOR'S OWN WALLS. Its back wall stands one width past the reveal; past that is outside the
    # building's modelled volume altogether.
    if cd < DN - OPENDEPTH - CWIDTH:
        tests.append(('past the corridor back wall', (DN - OPENDEPTH - CWIDTH) - cd, cls, stem, cu, cd, cy))

if not tests:
    print('NO CAMERA IS INSIDE ANY SOLID, not even by a millimetre.')
else:
    kinds = sorted(set(t[0] for t in tests))
    for kind in kinds:
        mine = [t for t in tests if t[0] == kind]
        depth = np.array([t[1] for t in mine])
        over = [t for t in mine if t[1] > ALLOW]
        print(kind + ':', len(mine), 'cameras are inside it, by', round(float(depth.min()), 3), 'to',
              round(float(depth.max()), 3), 'm, median', round(float(np.median(depth)), 3))
        print('   ', len(over), 'of them beat the', ALLOW, 'm allowance and are real contradictions')
        for t in sorted(mine, key=lambda z: -z[1])[:8]:
            print('    ', t[2], t[3], 'in by', round(t[1], 3), 'm | u', round(t[4], 2), 'd', round(t[5], 3),
                  'h', round(t[6], 2))
        print('')

print('WHAT A CLEAN RESULT MEANS. It bounds the model where people walked and nowhere else. The corridor')
print('behind the north wall has never had a camera in it, so nothing here tests its width or its ceiling.')
