# 2026-09-10: HOW DEEP IS THE REVEAL, MEASURED BY WHERE A LAMP BEHIND IT STOPS BEING VISIBLE.
#
# openDepth is 0.900 m and index.html records where it came from: "reveal 0.9 +-0.3 (cloud, 2014 photo)".
# A third of a metre of stated slop on a number that sets how thick the north wall is, and nothing has
# ever tested it. It is also the last soft thing between the hall and the room behind the wall.
#
# AN OPENING IS A TUBE, AND A TUBE IS AN OCCLUDER WITH A KNOWN SHAPE. Light from something behind the
# wall reaches a lens only if the sightline clears BOTH ends of that tube: the aperture on the hall face
# and the aperture at the back of the reveal. Straight on, both are easy. As the camera moves along the
# hall the sightline goes oblique, and the back aperture cuts the view off while the front one is still
# wide open. WHERE it cuts off depends on one number and that number is the depth of the tube.
#
# AND THERE ARE TWO BRIGHT POINTS BEHIND IT TO WATCH. tools/corridor_lamps.py triangulated two lamps
# inside the room, on u 30.527 and 34.140, and this file draws them. A lamp is not faint signal in a dark
# aperture: it is a specular blob far brighter than anything near it, so whether it arrived is decided by
# a ratio against its own surroundings and not by an edge, a gradient or a fitted line.
#
# THE MEASUREMENT. For every hall camera and each lamp, predict from the geometry whether the lamp is
# visible for an assumed reveal depth, then look in the photograph and see. Sweep the assumed depth and
# take the one that agrees with the photographs most often.
#
# THE CONTROLS, stated before it runs.
#   THE CURVE MUST PEAK. If agreement is flat across the sweep the tube is not what decides visibility
#   here and no depth is reported, however good the best score looks.
#   THE TWO LAMPS ARE SEPARATE INSTRUMENTS. They sit behind different openings and are seen by different
#   frames, so they are run apart and only agreement between them counts.
#   THE DETECTOR IS CHECKED WHERE THE ANSWER IS KNOWN. Frames whose sightline misses the opening
#   altogether, by more than a metre, must read as not-seen; if they do not, the detector is finding
#   lamps that cannot be there and nothing downstream means anything.
#   python tools/reveal_depth.py
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
CLASSES = ('walk', 'night', 'day4k')


def model():
    src = io.open('index.html', encoding='utf-8').read()

    def g(pat):
        return float(re.search(pat, src).group(1))

    mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
    ml = re.search(r'lamps:\[(.*?)\]\}', src, re.S)
    return {'dNorth': g(r'dNorth:(-?[0-9.]+)'), 'reveal': g(r'openDepth:\s*([0-9.]+)'),
            'sill': g(r'openY:\[([0-9.]+),'), 'head': g(r'openY:\[[0-9.]+,([0-9.]+)\]'),
            'openings': [[float(a), float(b)]
                         for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))],
            'lamps': [[float(a), float(b), float(c)] for a, b, c in
                      re.findall(r'\[([0-9.]+),(-?[0-9.]+),([0-9.]+)\]', ml.group(1))]}


M = model()
DN, SILL, HEAD = M['dNorth'], M['sill'], M['head']
print('THE WALL AND THE LAMPS index.html DRAWS, read at run time')
print('   wall face d %.3f, reveal %.3f deep, openings between h %.3f and %.3f'
      % (DN, M['reveal'], SILL, HEAD))
for i, L in enumerate(M['lamps']):
    print('   lamp %d on u %.3f  d %.3f  h %.3f' % (i + 1, L[0], L[1], L[2]))


def world(u, d, h):
    return O + u * HU + d * HD + np.array([0.0, h, 0.0])


def cross(C, X, dplane):
    """where the segment from the camera to the lamp crosses a plane of constant d, as (u, h)"""
    cd, xd = float((C - O) @ HD), float((X - O) @ HD)
    if abs(xd - cd) < 1e-9:
        return None
    t = (dplane - cd) / (xd - cd)
    P = C + t * (X - C)
    return float((P - O) @ HU), float(P[1] - O[1])


def clears(C, X, op, depth):
    """does the sightline clear both ends of the tube, and by what margin in metres"""
    u0, u1 = op
    m = []
    for dp in (DN, DN - depth):
        c = cross(C, X, dp)
        if c is None:
            return None
        u, h = c
        m.append(min(u - u0, u1 - u, h - SILL, HEAD - h))
    return min(m)


def blob(im, cam, X):
    """is there a bright point where the lamp projects, against the ring around it"""
    x, y, z = cam.project(np.asarray([X]))
    if z[0] <= 0.5:
        return None
    px, py = float(x[0]), float(y[0])
    if not (12 < px < cam.w - 13 and 12 < py < cam.h - 13):
        return None
    core = im[int(py) - 2:int(py) + 3, int(px) - 2:int(px) + 3].astype(float)
    ring = im[int(py) - 12:int(py) + 13, int(px) - 12:int(px) + 13].astype(float)
    if core.size < 9 or ring.size < 100:
        return None
    c, r = float(core.mean()), float(np.median(ring))
    # A LAMP IS BRIGHT IN ABSOLUTE TERMS AS WELL AS RELATIVE ONES, or the brightest noise in a dark
    # aperture is a lamp in every frame.
    return (c > r + 25.0 and c > 60.0), c, r


rows = []
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ch = float(q @ HD), float(q[1])
        if ch > 3.0 or cd < 3.0:
            continue
        im = None
        for li, L in enumerate(M['lamps']):
            X = world(L[0], L[1], L[2])
            op = min(M['openings'], key=lambda o: abs(0.5 * (o[0] + o[1]) - L[0]))
            if im is None:
                im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if im is None:
                    break
            b = blob(im, cam, X)
            if b is None:
                continue
            rows.append((li, k, cam.center, X, op, b[0], b[1], b[2]))

print('')
print('%d lamp-and-frame pairs where the lamp projects into the picture' % len(rows))
if len(rows) < 40:
    raise SystemExit('   too few to measure anything')

# THE DETECTOR IS CHECKED FIRST, on sightlines that miss the opening by more than a metre at the face.
far = []
for li, k, C, X, op, seen, c, r in rows:
    fc = cross(C, X, DN)
    if fc is None:
        continue
    if min(fc[0] - op[0], op[1] - fc[0], fc[1] - SILL, HEAD - fc[1]) < -1.0:
        far.append(seen)
if len(far) >= 20:
    print('   THE DETECTOR CHECK: %d sightlines miss the opening by over a metre and cannot be showing'
          % len(far))
    print('   this lamp. %.0f per cent of them read as a lamp anyway.' % (100.0 * np.mean(far)))
    if np.mean(far) > 0.15:
        raise SystemExit('   THE DETECTOR FIRES WHERE NO LAMP CAN BE. Nothing below this would mean '
                         'anything, so no depth is reported.')
else:
    print('   THE DETECTOR CHECK could not run: only %d sightlines miss the opening widely.' % len(far))

# BEFORE THE SWEEP, THE SAME DATA ANSWERS A QUESTION NOBODY HAD ASKED: are the lamps where this file
# puts them. corridor_lamps.py TRIANGULATED these two points and the model then hung the corridor ceiling
# and depth on the higher of them, but nothing ever went back and checked them against every frame. That
# is a straight prediction: at the drawn reveal depth the geometry says the lamp either is or is not down
# the tube, and the photograph either shows a bright point there or does not.
vis = [(pr, r[5]) for r, pr in ((r, clears(r[2], r[3], r[4], M['reveal']) > 0) for r in rows)]
tp = sum(1 for p, s in vis if p and s)
fn = sum(1 for p, s in vis if p and not s)
fp = sum(1 for p, s in vis if not p and s)
tn = sum(1 for p, s in vis if not p and not s)
print('')
print('   THE LAMPS THEMSELVES, CHECKED AGAINST EVERY FRAME AT THE DRAWN DEPTH:')
print('      the geometry says VISIBLE in %d pairs, and a lamp is actually there in %d of them (%.0f per cent)'
      % (tp + fn, tp, 100.0 * tp / max(tp + fn, 1)))
print('      it says HIDDEN in %d pairs, and a lamp shows anyway in %d of them (%.0f per cent)'
      % (fp + tn, fp, 100.0 * fp / max(fp + tn, 1)))
if tp + fn >= 12 and tp >= 0.6 * (tp + fn) and fp <= 0.15 * (fp + tn):
    print('      THE TRIANGULATED LAMPS STAND UP. When the model says you can see one down an opening you')
    print('      usually can, and when it says you cannot you almost never do. The corridor ceiling rests')
    print('      on the higher of these two points, so this is the first check that point has ever had.')
elif tp + fn < 12:
    print('      NOT ENOUGH SIGHTLINES REACH A LAMP to check them this way: %d pairs is not a test.'
          % (tp + fn))
else:
    print('      THE LAMPS DO NOT PREDICT WELL, and since the corridor ceiling rests on the higher of')
    print('      them that is worth chasing rather than filing.')

DEPTHS = np.arange(0.10, 2.21, 0.05)

# ONLY THE PAIRS THE QUESTION CAN DECIDE ARE ALLOWED TO ANSWER IT, and the first run of this got that
# wrong in a way worth keeping on the record. It scored every pair at every depth and came back 95.8 per
# cent agreement at ALL of them, flat to a tenth of a point. The reason is arithmetic: 152 of the 225
# sightlines miss the aperture by over a metre, so they are invisible whatever the tube depth is, and a
# large majority that cannot change swamps the small minority that can. A score dominated by the easy
# cases measures how easy they are.
# So each pair is now predicted across the WHOLE sweep first, and only the pairs whose prediction
# actually changes somewhere in it are scored. Those are the ones standing at the edge of the tube.
pred = {}
for i, (a, k, C, X, op, seen, cc, rr) in enumerate(rows):
    ps = []
    for W in DEPTHS:
        m = clears(C, X, op, W)
        ps.append(None if m is None else (m > 0))
    pred[i] = ps
live = [i for i in pred if len(set(p for p in pred[i] if p is not None)) > 1]
print('')
print('   %d of the %d pairs change their prediction somewhere across the sweep. Those are the ones'
      % (len(live), len(rows)))
print('   standing at the edge of the tube, and they are the only ones scored.')
if len(live) < 20:
    print('')
    print('   NO LEVERAGE, and that is the finding rather than a failure. Almost every sightline to these')
    print('   lamps either goes straight down an opening or misses it by a mile, so the depth of the')
    print('   reveal never decides anything. Measuring it needs a camera standing where the aperture edge')
    print('   just cuts the lamp, and nobody stood there. Nothing changes.')
    raise SystemExit(0)
print('')
print('   assumed depth   lamp 1 agrees   lamp 2 agrees   both')
best = []
for wi, W in enumerate(DEPTHS):
    sc = []
    for li in (0, 1):
        ok = tot = 0
        for i in live:
            if rows[i][0] != li or pred[i][wi] is None:
                continue
            tot += 1
            ok += int(pred[i][wi] == rows[i][5])
        sc.append(ok / float(tot) if tot else float('nan'))
    both = np.nanmean(sc)
    best.append((both, float(W), sc[0], sc[1]))
    if abs(W * 100 - round(W * 100)) < 1e-6 and int(round(W * 100)) % 20 == 0:
        print('      %.2f m        %5.1f per cent   %5.1f per cent   %5.1f'
              % (W, 100 * sc[0], 100 * sc[1], 100 * both))
best.sort(reverse=True)
top, W, s1, s2 = best[0]
flat = top - min(b[0] for b in best)
print('')
print('   THE BEST AGREEMENT IS %.1f per cent AT A REVEAL %.2f m DEEP (lamp 1 %.1f, lamp 2 %.1f).'
      % (100 * top, W, 100 * s1, 100 * s2))
print('   across the whole sweep agreement moves %.1f points, from %.1f to %.1f.'
      % (100 * flat, 100 * min(b[0] for b in best), 100 * top))
print('   index.html draws %.3f m, stated as plus or minus 0.3 from a 2014 photograph.' % M['reveal'])
b1 = sorted(best, key=lambda b: -b[2])[0][1]
b2 = sorted(best, key=lambda b: -b[3])[0][1]
print('   taken alone lamp 1 prefers %.2f m and lamp 2 prefers %.2f m' % (b1, b2))
if flat < 0.08:
    print('   REFUSED: agreement barely moves across the whole sweep, so visibility here is not decided')
    print('   by the depth of the tube and this cannot measure it. Nothing changes.')
elif abs(b1 - b2) > 0.40:
    print('   REFUSED: the two lamps prefer depths %.2f m apart, so they are not measuring one wall.'
          % abs(b1 - b2))
    print('   Nothing changes.')
elif abs(W - M['reveal']) <= 0.30:
    print('   THE DRAWN DEPTH SURVIVES. The best fit is %.2f m against the drawn %.3f, inside the slop'
          % (W, M['reveal']))
    print('   the drawn figure already carries, and the two lamps agree to %.2f m. This does not sharpen'
          % abs(b1 - b2))
    print('   the number; it is the first evidence of any kind that it is the right one.')
else:
    print('   THE DRAWN DEPTH IS OUTSIDE ITS OWN STATED SLOP: best %.2f m against a drawn %.3f plus or'
          % (W, M['reveal']))
    print('   minus 0.3, with the two lamps agreeing to %.2f m. That is worth acting on.' % abs(b1 - b2))
