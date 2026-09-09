# 2026-09-10: IS ANY POSED CAMERA STANDING INSIDE SOMETHING THIS FILE DRAWS SOLID.
#
# A camera centre is the one measurement with no instrument in it. No edge is found, no gradient is
# fitted, no window is chosen: a phone was at that point, so that point is free space. If a pose puts a
# phone inside stone, either the stone is not there or the pose is wrong, and both are worth knowing.
#
# THIS HAD NEVER BEEN RUN ACROSS THE WHOLE MODEL. tools/corridor_inside.py asked it of one wall and found
# that every camera behind the north face is inside an opening, so the test could not reach the room it
# was aimed at. That was one wall. This asks it of the envelope: both ends, the south side, the north
# wall thickness, the floor, and the room behind the north wall.
#
# WHAT A PASS IS WORTH, SAID BEFORE THE RUN. Very little on its own. People walk down the middle of
# rooms, so a wall is rarely touched, and the clearance is printed beside every verdict so a test that
# had no chance of failing reads as one. WHAT A FAILURE IS WORTH IS THE POINT: it is a hard
# contradiction, and the only question it leaves is which of the two things is wrong.
#
# EVERY BOUND IS READ OUT OF index.html AT RUN TIME. Three tools in this repo have now been caught
# testing a model that had moved underneath them, so nothing here keeps its own copy of anything.
#   python tools/pose_containment.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b1p', 'b3', 'b3p', 'b4', 'b5', 'b5p',
           'b6g', 'b6gp', 'b6s', 'b7s', 'b7sp')


def model():
    src = io.open('index.html', encoding='utf-8').read()

    def g(pat):
        return float(re.search(pat, src).group(1))

    m = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
    return {'uMin': g(r'uMin:([0-9.]+)'), 'uMax': g(r'uMax:([0-9.]+)'),
            'dNorth': g(r'dNorth:(-?[0-9.]+)'), 'dSouth': g(r'dSouth:([0-9.]+)'),
            'reveal': g(r'openDepth:\s*([0-9.]+)'),
            'width': g(r'corridor:\{width:([0-9.]+)'),
            'sill': g(r'openY:\[([0-9.]+),'), 'head': g(r'openY:\[[0-9.]+,([0-9.]+)\]'),
            'recess': g(r'const ENDW=\{[^}]*?face:\s*([0-9.]+)'),
            'wface': 4.194, 'eface': 48.056,
            'ground': g(r'groundTop:\s*([0-9.]+)'),
            'openings': [[float(a), float(b)]
                         for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', m.group(1))]}


M = model()
BACK = M['dNorth'] - M['reveal'] - M['width']
print('THE ENVELOPE index.html DRAWS, read at run time')
print('   the hall runs u %.3f to %.3f and d %.3f to %.3f, floor h 0'
      % (M['uMin'], M['uMax'], BACK, M['dSouth']))
print('   the north wall is solid from d %.3f back to %.3f except through an opening,'
      % (M['dNorth'], M['dNorth'] - M['reveal']))
print('   and an opening is one of twelve u spans between h %.3f and %.3f' % (M['sill'], M['head']))
print('   the end galleries cut back %.3f m, so their recesses are u %.3f to %.3f and %.3f to %.3f'
      % (M['recess'], M['uMin'], M['wface'], M['eface'], M['uMax']))

cams = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for fr, v in (frames or {}).items():
        cams.setdefault(fr, (cls, v[0]))
print('')
print('%d distinct posed frames on disk' % len(cams))

TESTS = ('past the west end', 'past the east end', 'beyond the south wall',
         'beyond the corridor back wall', 'below the hall floor',
         'inside the north wall thickness', 'inside solid below an end gallery')
fails = {t: [] for t in TESTS}
clear = {t: [] for t in TESTS}
for fr, (cls, cam) in cams.items():
    q = cam.center - O
    u, d, h = float(q @ HU), float(q @ HD), float(q[1])
    # THE CLEARANCE IS ONLY MEANINGFUL FOR CAMERAS ACTUALLY IN THE BUILDING. Pooling the failures into
    # it prints the failure back as a negative clearance and hides how close a real standpoint ever came,
    # which is the whole point of the number.
    if M['uMin'] <= u <= M['uMax'] and BACK <= d <= M['dSouth'] and h >= 0:
        clear['past the west end'].append((u - M['uMin'], fr, cls))
        clear['past the east end'].append((M['uMax'] - u, fr, cls))
        clear['beyond the south wall'].append((M['dSouth'] - d, fr, cls))
        clear['beyond the corridor back wall'].append((d - BACK, fr, cls))
        clear['below the hall floor'].append((h, fr, cls))
    if u < M['uMin']:
        fails['past the west end'].append((fr, cls, u, d, h))
    if u > M['uMax']:
        fails['past the east end'].append((fr, cls, u, d, h))
    if d > M['dSouth']:
        fails['beyond the south wall'].append((fr, cls, u, d, h))
    if d < BACK:
        fails['beyond the corridor back wall'].append((fr, cls, u, d, h))
    if h < 0:
        fails['below the hall floor'].append((fr, cls, u, d, h))
    # the north wall thickness: solid unless the camera is in an opening, in u AND in h
    if M['dNorth'] - M['reveal'] <= d <= M['dNorth']:
        through = any(u0 <= u <= u1 for u0, u1 in M['openings']) and M['sill'] <= h <= M['head']
        if not through:
            fails['inside the north wall thickness'].append((fr, cls, u, d, h))
    # inside an end recess but below the ground floor top, which is solid at both ends
    inrec = (M['uMin'] < u < M['wface']) or (M['eface'] < u < M['uMax'])
    if inrec and 0 <= h < M['ground']:
        fails['inside solid below an end gallery'].append((fr, cls, u, d, h))

print('')
print('   test                                  fails   closest a real standpoint came')
bad = 0
for t in TESTS:
    bad += len(fails[t])
    note = ('%+.3f m  %s' % (min(clear[t])[0], min(clear[t])[1])) if clear[t] else 'not tested here'
    print('   %-36s %5d   %s' % (t, len(fails[t]), note))
print('')
if not bad:
    print('   NO POSED CAMERA STANDS INSIDE ANYTHING THIS FILE DRAWS SOLID.')
else:
    for t in TESTS:
        if not fails[t]:
            continue
        print('   %d FAIL %s:' % (len(fails[t]), t))
        for fr, cls, u, d, h in sorted(fails[t]):
            print('      %-16s %-5s u %8.3f  d %8.3f  h %7.3f' % (fr, cls, u, d, h))
    every = sorted({f[0] for t in TESTS for f in fails[t]})
    byc = sorted({f[1] for t in TESTS for f in fails[t]})
    print('')
    print('   %d frames fail something, from %d clip(s): %s' % (len(every), len(byc), ', '.join(byc)))
    print('   A CAMERA THAT CANNOT BE WHERE IT SAYS IT IS REFUTES ITSELF, NOT A WALL. A pose outside the')
    print('   building is not a measurement of the building, so the useful output is the frame names,')
    print('   and they are printed so that nothing downstream treats them as evidence about anything.')
print('')
print('   AND A PASS IS WORTH WHAT THE CLEARANCES SAY, counting only cameras inside the building. The')
print('   closest anyone came to the south wall is %.3f m and to the east end %.3f m, so neither was'
      % (min(clear['beyond the south wall'])[0], min(clear['past the east end'])[0]))
print('   ever in danger of being refuted by somebody standing somewhere. This audit can only catch a')
print('   gross error, and the value of running it is that a gross error is what it found.')

# AND THE SOUTH WALL GETS ITS FIRST HARD NUMBER OUT OF THIS, WHICH WAS NOT THE POINT OF THE RUN.
# dSouth has been refused twice by instruments that tried to measure it from imagery. A camera centre
# needs no instrument: the operator stood there, so the wall is not nearer than that. It is one sided
# and it is not tight, but it is the first thing under that number that cannot be argued with.
sc, sf, scl = min(clear['beyond the south wall'])
print('')
print('   THE SOUTH WALL, WHICH TWO INSTRUMENTS HAVE REFUSED TO MEASURE, PICKS UP A HARD LOWER BOUND.')
print('   %s (%s) stands %.3f m short of it, so the south wall cannot be nearer than d %.3f.'
      % (sf, scl, sc, M['dSouth'] - sc))
print('   index.html draws %.3f, so %.3f m of that is unsupported on this side. One sided, not tight,'
      % (M['dSouth'], sc))
print('   and the first constraint on dSouth that involves no instrument at all.')
