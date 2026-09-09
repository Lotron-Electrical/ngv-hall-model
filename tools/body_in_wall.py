# 2026-09-10: A BODY CANNOT BE INSIDE A BRICK WALL. THE OPERATOR AS A PROBE OF THE OPENINGS.
#
# WHERE THIS CAME FROM. tools/eye_height.py tried to use the operator's carry height as one constant across
# the archive and its control killed it: the two hall-floor captures put the camera 1.789 m and 1.600 m
# above the same floor, 189 mm apart on 789 and 99 frames, which is many times the uncertainty of either
# median. He did not carry the phone the same way on the two days, so that route is closed. But the same
# table showed something the height test could not use: SIXTY-SEVEN POSED FRAMES sit between 9.6 and 10.0 m
# with no modelled floor beneath them at all, just south of the wall plane. That is a man leaning out
# through an opening with the phone in front of him.
#
# AND THAT IS AN OCCLUSION ARGUMENT, WHICH IS THE ONLY CLASS THIS PROJECT HAS FOUND THAT HOLDS UP. Light
# either arrived or it did not; a body either fits or it does not. Every camera that stands INSIDE the
# thickness of the north wall, between the back of the reveal and the wall face, and between the sill and
# the head, must be inside one of the twelve openings, because the wall is solid brick everywhere else. If
# a posed camera lands on a modelled pier, then either that pier is not there or the pose is wrong.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. A camera enters the test only if it stands within the wall slab in d and within the opening band in
#      h, and between the ends of the wall in u. Nothing else is looked at.
#   2. THE NULL IS AN INVENTED SET OF OPENINGS: the same twelve widths, on the same pitch, shifted along
#      the wall so they land on the modelled piers. The invented set covers exactly the same fraction of
#      the wall, so a camera that lands in a real opening by chance lands in an invented one just as often.
#   3. The model's openings are CORROBORATED only if the real hit rate beats the invented rate, and beats
#      it by more than the spread of the invented rate over the shifts tried.
#   4. Any camera inside the slab that lands on a modelled pier is named, with the distance to the nearest
#      opening edge, because that is the case that would matter.
#
# WHAT IT CANNOT DO. It cannot prove an opening exists where no camera ever went, and there are twelve
# openings and only a few clips. A pose is not a body: the phone is held out in front, so a camera can be
# in the opening while the man is behind it, which helps this test rather than hurting it. And the solver's
# own position error, quoted as 24 to 100 mm on these clips, is small against a pier 2.4 m wide but is not
# nothing.
#   python tools/body_in_wall.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s',
           'b1p', 'b3p', 'b5p', 'b7sp')
DMARGIN = 0.10     # metres of slack either side of the wall thickness
HMARGIN = 0.05     # and at the sill and head
SHIFTS = (0.5, 0.25, 0.75, 0.35, 0.65)

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [(float(a), float(b)) for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DEPTH = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEAD = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
DR = DN - DEPTH
UMIN, UMAX = OPEN[0][0] - 0.5, OPEN[-1][1] + 0.5
PITCH = (OPEN[-1][0] - OPEN[0][0]) / (len(OPEN) - 1)


def hits(us, holes):
    return np.array([any(a <= u <= b for a, b in holes) for u in us])


def count_in(us, a, b):
    return int(np.logical_and(us >= a, us <= b).sum())


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   A camera enters this test only if it stands INSIDE the thickness of the north wall: d from')
    print('   %.3f to %.3f with %.2f m of slack, h from %.3f to %.3f with %.2f m, and u between the ends'
          % (DR, DN, DMARGIN, SILL, HEAD, HMARGIN))
    print('   of the wall. The wall is solid brick everywhere but the twelve openings, so every one of')
    print('   those cameras must be inside an opening or the model is wrong about where the holes are.')
    print('   THE NULL IS AN INVENTED SET OF OPENINGS: the same twelve widths on the same %.3f m pitch,'
          % PITCH)
    print('   shifted so they land on the modelled piers, covering exactly the same fraction of the wall.')
    print('   The model is corroborated only if the real hit rate beats the invented one by more than the')
    print('   invented rate varies over the shifts tried.')
    print('')
    cover = sum(b - a for a, b in OPEN) / (UMAX - UMIN)
    print('   the twelve openings cover %.1f per cent of the wall between u %.2f and u %.2f, so a camera'
          % (100 * cover, UMIN, UMAX))
    print('   dropped in at random lands in one about that often.')

    rows = []
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception:
            continue
        for k, (cam, ip) in sorted(fr.items()):
            q = cam.center - O
            u, d, h = float(q @ HU), float(q @ HD), float(q[1])
            if not (DR - DMARGIN <= d <= DN + DMARGIN):
                continue
            if not (SILL - HMARGIN <= h <= HEAD + HMARGIN):
                continue
            if not (UMIN <= u <= UMAX):
                continue
            rows.append((cn, k, u, d, h))
    if not rows:
        sys.exit('   NOT ONE POSED CAMERA STANDS INSIDE THE WALL. This test has nothing to work with and '
                 'nothing is concluded.')

    us = np.array([r[2] for r in rows])
    real = hits(us, OPEN)
    print('')
    print('   %d posed cameras stand inside the wall, from %d captures.'
          % (len(rows), len({r[0] for r in rows})))
    print('   %d of them are inside a modelled opening: %.1f per cent.'
          % (int(real.sum()), 100 * real.mean()))

    nulls = []
    for frac in SHIFTS:
        inv = [(a + frac * PITCH, b + frac * PITCH) for a, b in OPEN]
        nulls.append(float(hits(us, inv).mean()))
    print('   the invented openings, shifted by %s of a pitch, are hit %s per cent of the time.'
          % (', '.join('%.2f' % f for f in SHIFTS), ', '.join('%.0f' % (100 * v) for v in nulls)))
    nm, nsp = float(np.mean(nulls)), float(max(nulls) - min(nulls))
    print('   that is %.1f per cent on average with a spread of %.1f.' % (100 * nm, 100 * nsp))

    margin = real.mean() - nm
    print('')
    if margin <= nsp:
        print('   THE REAL OPENINGS DO NOT BEAT THE INVENTED ONES BY MORE THAN THE INVENTED ONES VARY.')
        print('   This test does not corroborate where the holes are, and nothing is concluded from it.')
    else:
        print('   THE MODEL\'S OPENINGS BEAT THE INVENTED ONES BY %.1f POINTS against a spread of %.1f, so'
              % (100 * margin, 100 * nsp))
        print('   the holes are where the operator actually walked and leaned, not merely where a')
        print('   plausible pattern would put them. THIS IS AN OCCLUSION ARGUMENT AND IT IS THE STRONGEST')
        print('   KIND AVAILABLE HERE: a man cannot stand inside brickwork.')

    miss = [r for r, ok in zip(rows, real) if not ok]
    print('')
    if not miss:
        print('   AND NOT ONE CAMERA LANDS ON A MODELLED PIER. Every single body that entered the wall')
        print('   entered it through a hole this file draws.')
    else:
        print('   %d CAMERAS LAND ON A MODELLED PIER, which is the case that would matter:' % len(miss))
        for cn, k, u, d, h in sorted(miss, key=lambda r: r[2])[:14]:
            gap = min(min(abs(u - a), abs(u - b)) for a, b in OPEN)
            print('      %-5s %-14s u %7.3f d %+6.3f h %6.3f, %.3f m from the nearest opening edge'
                  % (cn, k, u, d, h, gap))
        gaps = [min(min(abs(r[2] - a), abs(r[2] - b)) for a, b in OPEN) for r in miss]
        print('   they sit %.3f m from an opening edge at the median, and the solver quotes its own'
              % float(np.median(gaps)))
        print('   position error as 24 to 100 mm on these clips. A miss smaller than that is the pose;')
        print('   a miss much larger than that is the wall.')

    per = {}
    for (cn, k, u, d, h), ok in zip(rows, real):
        e = per.setdefault(cn, [0, 0])
        e[0] += 1
        e[1] += 1 if ok else 0
    print('')
    print('   and by capture, so that no single clip is carrying the answer:')
    for cn, (n, g) in sorted(per.items(), key=lambda t: -t[1][0]):
        print('      %-6s %4d cameras in the wall, %4d of them in an opening, %.0f per cent'
              % (cn, n, g, 100.0 * g / n))
    print('')
    print('   WHICH OPENINGS THE ARCHIVE ACTUALLY VISITED, because this can only speak for those:')
    for i, (a, b) in enumerate(OPEN):
        n = count_in(us, a, b)
        print('      opening %2d  u %7.3f to %7.3f   %s'
              % (i, a, b, ('%d cameras stood in it' % n) if n else 'never entered'))

    # AND THE SAME ARGUMENT BOUNDS THE JAMBS, which is the part that could move geometry. A camera inside
    # the thickness of this wall is inside a REAL hole, whatever the model says, so the real hole reaches
    # at least as far as that camera does. Assign every one of them to the nearest modelled opening and the
    # spread of each group is a floor under that opening's width, one-sided and rigorous: the hole can be
    # wider than this, never narrower. A jamb is only CONTRADICTED where a camera stands beyond it by more
    # than the solver's own position error, quoted as 24 to 100 mm on these clips, and the loose end of
    # that range is the one used so this cannot manufacture a fault.
    POSERR = 0.100
    print('')
    print('   AND WHAT THE BODIES SAY ABOUT THE JAMBS. A camera inside this wall is inside a real hole,')
    print('   so the hole reaches at least as far as the camera does. Every camera goes to its nearest')
    print('   modelled opening and the spread of that group is a FLOOR under the width of that opening:')
    print('   the hole can be wider, never narrower. A jamb is contradicted only where a camera stands')
    print('   beyond it by more than %.0f mm, the loose end of the position error the solver quotes.'
          % (1000 * POSERR))
    print('')
    print('   opening   modelled span     bodies span       width drawn / needed   verdict')
    moved = []
    for i, (a, b) in enumerate(OPEN):
        mine = [u for u in us if min(abs(u - a), abs(u - b)) ==
                min(min(abs(u - x), abs(u - y)) for x, y in OPEN)]
        if len(mine) < 3:
            continue
        lo, hi = float(min(mine)), float(max(mine))
        west = a - lo
        east = hi - b
        need = hi - lo
        bad = max(west, east) > POSERR
        if bad:
            moved.append((i, west, east, len(mine)))
        print('   %7d   %7.3f %7.3f   %7.3f %7.3f   %6.3f / %6.3f        %s'
              % (i, a, b, lo, hi, b - a, need,
                 ('WEST JAMB OUT by %.3f m' % west) if west > POSERR else
                 ('EAST JAMB OUT by %.3f m' % east) if east > POSERR else 'holds'))
    print('')
    if not moved:
        print('   EVERY JAMB HOLDS. Not one body reached past a modelled jamb by more than the pose error,')
        print('   so nothing here asks for a millimetre of change, and the openings the archive visited')
        print('   are wide enough and no wider than they need to be. THAT IS A ONE-SIDED RESULT and it is')
        print('   worth saying so: this cannot show an opening is too WIDE, only too narrow.')
    else:
        print('   %d OPENINGS ARE TOO NARROW FOR WHAT STOOD IN THEM:' % len(moved))
        for i, west, east, n in moved:
            print('      opening %2d, %d bodies: the west jamb must move %+.3f m and the east %+.3f m'
                  % (i, n, max(0.0, west), max(0.0, east)))
        print('   That is a floor, not a measurement of the jamb: the hole must be at least this wide and')
        print('   may be wider, and nothing here says where the far side of it is.')


if __name__ == '__main__':
    main()
