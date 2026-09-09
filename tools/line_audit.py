# 2026-09-10: WHICH OF THE LINES THIS MODEL DRAWS ARE ACTUALLY THERE IN THE PHOTOGRAPHS? ALL OF THEM, ONCE.
#
# WHY A GLOBAL AUDIT AND NOT ANOTHER SINGLE NUMBER. Every run for days has taken one quantity, built an
# instrument for it, and come back with confirm or refuse. That is the right way to move a number, but it
# cannot tell you WHICH number to go after next, so the order of the work has been my hunches. This asks
# the archive one question about every horizontal line in the balconies, the walls and the corridor at the
# same time, and ranks them. The output is not a correction; it is a work list with evidence attached.
#
# THE MEASUREMENT. A line the model draws in the right place sits on a real edge: the wall above it does
# not read the same as the wall below it. So for each line, sample along its length, read the wall 60 mm
# above and 60 mm below IN THE WORLD, and take the size of the step. Perspective takes care of itself
# because the samples are placed in metres and projected, never measured in pixels.
#
# THE TRAP THIS PROJECT HAS ALREADY FALLEN INTO, AND THE CONTROL FOR IT. tools/follow_test.py measured
# that the old edge finder partly FOLLOWED the line the model drew: the same 25 frames settled on h 9.039
# when the model said 8.90 and on 9.093 when it said 9.02, so roughly 45 per cent of that answer was the
# model agreeing with itself. Nothing here searches for an edge, so nothing can follow one. But a wall
# that is busy everywhere would make every line look supported, so the CONTROL is the identical
# measurement at heights OFFSET from the drawn line by 0.15 to 0.60 m, in the same frames on the same
# samples, skipping any offset that lands on another drawn line. That measures how big a step this wall
# hands you for free, and a line only counts if it beats its own control.
#
# WHAT IT CANNOT DO, AND THE BOTTOM OF THE LIST HAS TO BE READ WITH THIS IN MIND. It cannot say where a
# line should be, only whether there is an edge where it is. A line drawn on a real edge that belongs to
# something else scores well. It says nothing about vertical lines and nothing about depth. And a line
# nobody can see scores nothing whether it is right or wrong, so a low score on few readings means
# UNTESTED, not refuted.
#   python tools/line_audit.py
import io
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b1p', 'b3', 'b3p', 'b4', 'b5', 'b5p', 'b7s', 'b7sp')
STEP = 0.06                        # how far above and below the line the wall is read
OFFS = [-0.60, -0.45, -0.30, -0.15, 0.15, 0.30, 0.45, 0.60]
MINN = 40

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(key):
    return float(re.search(r'\b' + key + r':\s*(-?[0-9.]+)', BLOCK).group(1))


mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DS = endw('dSouth')
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEADY = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
DEPTH = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
CW = float(re.search(r'corridor:\{width:([0-9.]+)', src).group(1))
CFL = float(re.search(r'corridor:\{width:[0-9.]+, *floor:([0-9.]+)', src).group(1))
CCE = float(re.search(r'corridor:\{width:[0-9.]+, *floor:[0-9.]+, *ceil:([0-9.]+)', src).group(1))
DECK = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1))
LOWDECK = float(re.search(r'floors:\[([0-9.]+),', BLOCK).group(1))
SLAB = endw('slab')
WFACE, EFACE = endw('west') + endw('face'), endw('east') - endw('face')
RT = re.search(r'railTops:\{west:([0-9.]+), *east:([0-9.]+)\}', BLOCK)
UPS = re.search(r'upstands:\{west:([0-9.]+), *east:([0-9.]+)\}', BLOCK)

# EVERY HORIZONTAL LINE IN THE THREE THINGS THE GOAL NAMES. A 'wall' line runs along u at a fixed d; an
# 'end' line runs along d at a fixed u. Each carries the stretch it is sampled over, so an opening line is
# only read across the openings and an end line only across the gallery.
LINES = []
for u0, u1 in OPEN:
    LINES.append(('north opening sill', 'wall', DN, SILL, u0 + 0.10, u1 - 0.10))
    LINES.append(('north opening head', 'wall', DN, HEADY, u0 + 0.10, u1 - 0.10))
    LINES.append(('corridor floor', 'wall', DN - DEPTH - CW, CFL, u0 + 0.20, u1 - 0.20))
    LINES.append(('corridor ceiling', 'wall', DN - DEPTH - CW, CCE, u0 + 0.20, u1 - 0.20))
for side, uF, rt, ups in (('west', WFACE, float(RT.group(1)), float(UPS.group(1))),
                          ('east', EFACE, float(RT.group(2)), float(UPS.group(2)))):
    for nm, hv in (('ground wall top', endw('groundTop')),
                   ('lower deck', LOWDECK),
                   ('top slab soffit', DECK - SLAB),
                   ('top deck', DECK),
                   ('solid upstand top', DECK + ups),
                   ('glass rail top', DECK + rt),
                   ('gallery head', endw('head')),
                   ('end wall top', endw('top'))):
        LINES.append(('%s %s' % (side, nm), 'end', uF, hv, 1.0, DS - 1.0))
# NEGATIVE CONTROLS: LINES THAT ARE NOT THERE. Without them a score of 0.75 has nothing to be compared
# with. These are heights on the same walls where this file draws nothing at all, put through the exact
# same measurement. Whatever they score is what a line that does not exist looks like, and any drawn line
# scoring the same is, photometrically, indistinguishable from one I made up.
for u0, u1 in OPEN:
    LINES.append(('INVENTED north wall 7.00', 'wall', DN, 7.00, u1 + 0.30, u1 + 1.30))
    LINES.append(('INVENTED north wall 12.30', 'wall', DN, 12.30, u1 + 0.30, u1 + 1.30))
LINES.append(('INVENTED west end 10.30', 'end', WFACE, 10.30, 1.0, DS - 1.0))
LINES.append(('INVENTED east end 10.30', 'end', EFACE, 10.30, 1.0, DS - 1.0))
LINES.append(('INVENTED west end 6.00', 'end', WFACE, 6.00, 1.0, DS - 1.0))
LINES.append(('INVENTED east end 6.00', 'end', EFACE, 6.00, 1.0, DS - 1.0))
print('%d line segments to audit, over %d named lines' % (len(LINES), len(set(t[0] for t in LINES))))
print('each is read %.0f mm above and below itself, in metres, against its own offset control'
      % (1000 * STEP))

DRAWN = sorted(set(round(t[3], 3) for t in LINES))
TAGS = [('line', 0.0)]
for _o in OFFS:
    TAGS.append(('ctl', _o))


def clear_of_other_lines(v, base):
    return all(abs(v - w) > 0.12 for w in DRAWN if abs(w - base) > 1e-9)


def sample(im, cam, kind, fixed, v, a0, a1):
    ts = np.linspace(a0, a1, 9)
    if kind == 'wall':
        pts = np.array([O + t * HU + fixed * HD + np.array([0.0, v, 0.0]) for t in ts])
    else:
        pts = np.array([O + fixed * HU + t * HD + np.array([0.0, v, 0.0]) for t in ts])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 2, x < cam.w - 3, y > 2, y < cam.h - 3])
    if ok.sum() < 5:
        return None
    return np.array([float(im[int(y[i]), int(x[i])]) for i in np.nonzero(ok)[0]])


acc = {}
ctrl = {}
for t in LINES:
    acc.setdefault(t[0], [])
    ctrl.setdefault(t[0], [])
nf = 0
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ce = float(q @ HD), float(q[1])
        if not (-1.0 < cd < DS + 1.0) or ce > 12.0:
            continue
        im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        nf += 1
        for name, kind, fixed, v0, a0, a1 in LINES:
            for tag, dv in TAGS:
                v = v0 + dv
                if tag == 'ctl' and not clear_of_other_lines(v, v0):
                    continue
                above = sample(im, cam, kind, fixed, v + STEP, a0, a1)
                below = sample(im, cam, kind, fixed, v - STEP, a0, a1)
                if above is None or below is None:
                    continue
                n = min(len(above), len(below))
                mu = 0.5 * (float(np.mean(above[:n])) + float(np.mean(below[:n])))
                if mu < 8:
                    continue
                s = float(np.mean(np.abs(above[:n] - below[:n]))) / mu
                if tag == 'line':
                    acc[name].append(s)
                else:
                    ctrl[name].append(s)

print('')
print('%d frames read' % nf)
print('')
print('   line                       readings   step on it   its control   ratio   verdict')
rows = []
for name in sorted(acc):
    a, b = acc[name], ctrl[name]
    if len(a) < MINN or len(b) < MINN:
        print('   %-26s %8d   too few readings: UNTESTED, not refuted' % (name, len(a)))
        continue
    la, lb = float(np.median(a)), float(np.median(b))
    rows.append((name, len(a), la, lb, la / max(lb, 1e-6)))
for name, n, la, lb, r in sorted(rows, key=lambda t: -t[4]):
    v = 'on a real edge' if r >= 1.30 else ('no better than the wall' if r <= 1.10 else 'weak')
    print('   %-26s %8d   %.4f       %.4f        %.2f    %s' % (name, n, la, lb, r, v))

if len(rows) < 6:
    sys.exit('   too few lines answered to rank anything')
strong = [t for t in rows if t[4] >= 1.30]
weak = [t for t in rows if 1.10 < t[4] < 1.30]
flat = [t for t in rows if t[4] <= 1.10]
print('')
print('   %d lines sit on a real edge, %d are weak, %d are no better than the wall around them.'
      % (len(strong), len(weak), len(flat)))

# THE POSITIVE CONTROL IS INSIDE THE LIST, AND IT DECIDES WHETHER ANY OF THE REST IS READABLE.
sill = [t for t in rows if t[0] == 'north opening sill']
if not sill or sill[0][4] < 1.30:
    print('')
    print('   THE POSITIVE CONTROL FAILS. The north opening sill is the edge of a hole in a wall, the')
    print('   most certain edge in this model and the one confirmed to ten millimetres by an instrument')
    print('   that shares no machinery with the fits that placed it. If it does not come back as an edge')
    print('   here, this is not reading edges and the ranking means nothing. NOTHING IS CONCLUDED.')
    sys.exit(0)
print('   THE POSITIVE CONTROL PASSES: the north opening sill, the edge of a hole and the best measured')
print('   level in this model, scores %.2f times its own control on %d readings.'
      % (sill[0][4], sill[0][1]))

# AND THE OTHER END OF THE SCALE, WHICH IS WHAT MAKES A LOW SCORE MEAN ANYTHING.
inv = [t for t in rows if t[0].startswith('INVENTED')]
if inv:
    iv = float(np.median([t[4] for t in inv]))
    print('')
    print('   THE NEGATIVE CONTROLS, %d lines this file does not draw anywhere, score %.2f at the median '
          % (len(inv), iv))
    print('   and run %.2f to %.2f. THAT is what a line that is not there looks like.'
          % (min(t[4] for t in inv), max(t[4] for t in inv)))
    same = [t for t in rows if not t[0].startswith('INVENTED') and t[4] <= max(t2[4] for t2 in inv)]
    print('   %d of the %d lines this model DOES draw score no higher than the best invented one.'
          % (len(same), len(rows) - len(inv)))
print('')
print('   WHAT THE BOTTOM OF THIS LIST MEANS, EXACTLY. A line scoring near 1.00 has no step in the')
print('   photographs where the model draws one. That is not proof it is misplaced: it can be a line')
print('   between two surfaces of the same tone, or one this wall hides. It IS a statement that the')
print('   drawn position rests on nothing photometric, and that is the queue, in this order:')
for name, n, la, lb, r in sorted(flat, key=lambda t: t[4])[:8]:
    if name.startswith('INVENTED'):
        continue
    print('      %-26s %.2f on %d readings' % (name, r, n))
