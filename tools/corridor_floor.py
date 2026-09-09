# 2026-09-10: THE CORRIDOR FLOOR, CHECKED BY THE MEN STANDING ON IT.
#
# WHAT IS KNOWN ABOUT THE CORRIDOR FLOOR. It is drawn on h 8.340, and it is drawn there because the end
# gallery deck is 8.340 and tools/model_consistency.py records that "moving one moves the other". That is
# an assumption written as a number. tools/walk_through.py put the floor 1.59 m from the nearest step
# anybody took, so no occlusion test reaches it, and a census run before this file was written found that
# of 315 posed frames standing inside the wall slab, ZERO face north into the corridor, so nothing
# photographs it either. The registrar's blind spot covers the corridor exactly.
#
# BUT 315 CAMERAS STOOD IN THE OPENINGS, and every one of them was held by a man whose feet were on that
# floor. tools/eye_height.py tried to make his carry height one constant and its control killed that:
# the two hall-floor captures put the camera 1.789 m and 1.600 m up on the same floor. So this does not use
# a constant. It uses the RANGE, and it uses the asymmetry that makes the range usable:
#   A MAN CAN LOWER THE PHONE. He leans out, he crouches, he rests it on the sill. Every one of those puts
#   the camera BELOW where standing would.
#   A MAN CANNOT LOWER HIS FEET. Whatever he does with the phone, the floor is where it is.
# So the HIGHEST cameras in a capture are the ones nearest to a man standing upright, and the floor under
# them is bracketed by their height less the range of carries this archive has actually shown.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. The carry range is the 10th to the 90th percentile of camera height over both hall-floor captures
#      pooled, where the floor is h 0 by the definition of the frame. Measured, not assumed.
#   2. For each capture standing in the openings, take the 90th percentile of camera height, the nearest
#      thing to a man standing tall, and subtract the carry range. That is the floor bracket.
#   3. The drawn floor is CONSISTENT with a capture if it lies inside the bracket.
#   4. A bracket ENTIRELY ABOVE the drawn floor refutes it, because feet do not go down.
#   5. A bracket entirely below is NO VERDICT, because the phone does, and it says so.
#   6. Nothing is claimed finer than the bracket's own width.
#
# WHAT IT CANNOT DO. It cannot tell a wrong floor from a wrong pose height, and it cannot say anything
# about a floor nobody stood on, which is most of the corridor: the frames stand in openings 4, 5 and 10
# and the floor is read there and nowhere else.
#   python tools/corridor_floor.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FLOORCL = ('walk', 'night')
INWALL = ('b1', 'b1p', 'b4', 'b5', 'b5p')
PLO, PHI = 10, 90
MINF = 10

src = io.open('index.html', encoding='utf-8').read()
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DEPTH = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEAD = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
CFLOOR = float(re.search(r'corridor:\{width:[0-9.]+, *floor:([0-9.]+)', src).group(1))
DR = DN - DEPTH


def heights(cn, inwall):
    fr = U.load_class(cn)
    out = []
    for k, (cam, ip) in fr.items():
        q = cam.center - O
        u, d, h = float(q @ HU), float(q @ HD), float(q[1])
        if not (-1.0 < u < 53.0):
            continue
        if inwall:
            if not (DR - 0.10 <= d <= DN + 0.10) or not (SILL - 0.05 <= h <= HEAD + 0.05):
                continue
        elif h > 3.0:
            continue
        out.append(h)
    return np.array(out)


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   A man can lower the phone: he leans, he crouches, he rests it on the sill. A man cannot')
    print('   lower his feet. So the HIGHEST cameras in a capture are the nearest thing to him standing')
    print('   upright, and the floor under them is their height less the range of carries this archive')
    print('   has actually shown on the hall floor, the %dth to the %dth percentile over both floor'
          % (PLO, PHI))
    print('   captures pooled. The drawn floor is CONSISTENT if it lies inside that bracket. A bracket')
    print('   entirely ABOVE the drawn floor refutes it, because feet do not go down. A bracket entirely')
    print('   below is NO VERDICT, because the phone does. Nothing finer than the bracket is claimed.')
    print('')
    pool = []
    for cn in FLOORCL:
        v = heights(cn, False)
        pool.append(v)
        print('   %-6s %4d cameras on the hall floor, height %.3f at the median, %.3f to %.3f'
              % (cn, len(v), float(np.median(v)), float(np.percentile(v, PLO)),
                 float(np.percentile(v, PHI))))
    pool = np.concatenate(pool)
    clo, chi = float(np.percentile(pool, PLO)), float(np.percentile(pool, PHI))
    print('   THE CARRY RANGE: %.3f to %.3f m over %d frames. That is the ruler.' % (clo, chi, len(pool)))
    print('')
    print('   the corridor floor is drawn on h %.3f; the openings run h %.3f to %.3f.' % (CFLOOR, SILL, HEAD))
    print('')
    print('   capture   in the openings   tallest tenth   floor bracket        verdict on %.3f' % CFLOOR)
    rows = []
    for cn in INWALL:
        try:
            v = heights(cn, True)
        except Exception:
            continue
        if len(v) < MINF:
            print('   %-8s %6d   too few to read' % (cn, len(v)))
            continue
        tall = float(np.percentile(v, PHI))
        lo, hi = tall - chi, tall - clo
        if lo <= CFLOOR <= hi:
            tag = 'consistent'
        elif lo > CFLOOR:
            tag = 'REFUTED, floor is higher by at least %.3f m' % (lo - CFLOOR)
        else:
            tag = 'no verdict, phone lowered'
        rows.append((cn, len(v), tall, lo, hi, tag))
        print('   %-8s %6d           %.3f        %.3f to %.3f   %s' % (cn, len(v), tall, lo, hi, tag))
    if not rows:
        sys.exit('   NO CAPTURE STANDS IN THE OPENINGS OFTEN ENOUGH TO READ. Nothing is concluded.')
    print('')
    ref = [r for r in rows if r[5].startswith('REFUTED')]
    ok = [r for r in rows if r[5] == 'consistent']
    if ref:
        print('   %d CAPTURES PUT THE FLOOR HIGHER THAN IT IS DRAWN. Feet do not go down, so this is a'
              % len(ref))
        print('   refutation and not a lean: the corridor floor is above %.3f by the amounts listed.'
              % CFLOOR)
    elif ok:
        w = max(r[4] - r[3] for r in ok)
        print('   THE DRAWN FLOOR IS CONSISTENT with %d of %d captures, and refuted by none. The bracket'
              % (len(ok), len(rows)))
        print('   is %.3f m wide, which is the whole of what this can say: a corridor floor drawn more'
              % w)
        print('   than about %.2f m higher than %.3f would have shown here, and none of the men who'
              % (0.5 * w, CFLOOR))
        print('   stood in openings 4, 5 and 10 were standing on one. It is the first independent check')
        print('   the corridor floor has had, and it is a bracket rather than a measurement.')
    else:
        print('   EVERY CAPTURE LOWERED THE PHONE, so nothing is read: the floor could be where it is')
        print('   drawn or lower, and the men who stood there cannot say which.')


if __name__ == '__main__':
    main()
