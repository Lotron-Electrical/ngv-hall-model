# 2026-09-10: A BODY CANNOT PASS THROUGH GLASS, AND 118 CAMERAS STOOD BELOW THE TOP OF IT.
#
# WHAT THE FILE SAYS ABOUT THE GALLERY FRONT. Each end gallery is closed off from the hall by a stone
# upstand on the face, deck to deck + 0.755 (gallery-parapet), and a glass barrier above it up to deck +
# railTops (gallery-rail), 1.525 m on the east. The provenance above records that railTops is "NOT
# MEASURABLE FROM THIS ARCHIVE": no tone, no opaque cap, and no occlusion leverage because glass blocks
# no sightline. Three instruments were spent on it and a note was left so a fourth would not be built.
#
# THIS IS NOT A FOURTH INSTRUMENT ON THE TOP OF THE GLASS. It is the other occlusion argument, the one
# that does not need a sightline at all and has held up everywhere it has been used in this file: A BODY
# CANNOT BE INSIDE A SOLID. body_in_wall.py put 250 cameras through drawn openings and none through
# brick. The same logic applies to a glass barrier, because a phone is a body too: a camera whose height
# is BELOW the top of the glass must be on the deck side of the glass. It cannot be in front of it. That
# says nothing about where the top is (a camera above the top can be anywhere, a man leans out), but it
# says a great deal about where the PLANE is: every camera below the top is a point the glass cannot be
# behind. And the archive has a lot of them, because the east deck was filmed with the phone held low.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. A deck camera is one standing over an end gallery (u inside the gallery span, widened by 1.0 m
#      toward the hall so a lean is not thrown away) with its height between deck + 0.3 and the head.
#      Only the registered sets are used; the pan sets carry 0.10 to 0.32 m of position error and this
#      argument lives on 0.1 m.
#   2. A camera BELOW the drawn top of the glass that stands more than POSERR (0.100 m, the same figure
#      body_in_wall.py used for the jambs) in front of the drawn face plane is a CONTRADICTION: it is
#      through the glass.
#   3. THE NULL is the same test with the glass plane moved back from the face by 0.25 and 0.50 m. If the
#      real plane does not beat the moved ones by a wide margin, the cameras are not telling us where it
#      is.
#   4. THE BOUND is the only number claimed: the glass plane can sit no further back from the hall than
#      the 5th percentile of the below-top cameras plus POSERR, because 95% of them would otherwise be
#      through it. It is one-sided by construction: a plane further FORWARD than the face contradicts
#      nothing here.
#   5. And the deck itself is read the way corridor_floor.py read the corridor floor: the tallest tenth
#      of each capture less the carry range measured on the hall floor, 1.521 to 1.966 m, is a bracket
#      the drawn deck must lie inside. Above the bracket refutes; below is no verdict.
#
# WHAT IT CANNOT DO. It cannot see the top of the glass, and it does not try. It cannot tell a wrong
# plane from a wrong pose beyond POSERR, and it speaks only for the stretch of deck the cameras stood
# on, d 3.98 to 7.50 and 13.04 to 14.33 on the east.
#   python tools/body_at_rail.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECKCL = ('day4k', 'b3', 'b7s', 'b6g', 'b6s', 'b4', 'b1', 'b5')
FLOORCL = ('walk', 'night')
POSERR = 0.100
NULLS = (0.25, 0.50)
PLO, PHI = 10, 90
MINF = 10
LEAN = 1.0

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(k):
    return float(re.search(r'\b' + k + r':\s*(-?[0-9.]+)', BLOCK).group(1))


def endw_side(k, side):
    m = re.search(r'\b' + k + r':\{[^}]*\b' + side + r':\s*(-?[0-9.]+)', BLOCK)
    return float(m.group(1))


DECK = float(re.search(r'floors:\[[0-9.]+,\s*([0-9.]+)\]', BLOCK).group(1))
HEAD = endw('head')
ENDS = {
    'west': dict(face=endw('west') + endw('face'), wall=endw('west'), s=-1,
                 top=DECK + endw_side('railTops', 'west'), ups=DECK + endw_side('upstands', 'west')),
    'east': dict(face=endw('east') - endw('face'), wall=endw('east'), s=+1,
                 top=DECK + endw_side('railTops', 'east'), ups=DECK + endw_side('upstands', 'east')),
}


def cams(cn):
    fr = U.load_class(cn)
    P = np.array([c.center - O for k, (c, ip) in sorted(fr.items())])
    if len(P) == 0:
        return np.zeros((0, 3))
    return np.stack([P @ HU, P @ HD, P[:, 1]], axis=1)


def on_deck(C, e):
    u, d, h = C[:, 0], C[:, 1], C[:, 2]
    lo, hi = sorted((e['face'] - e['s'] * LEAN, e['wall']))
    m = np.logical_and(u >= lo, u <= hi)
    m = np.logical_and(m, np.logical_and(d > 0.0, d < 15.364))
    m = np.logical_and(m, np.logical_and(h > DECK + 0.3, h < HEAD))
    return C[m]


def infront(C, e, plane):
    """distance each camera stands in FRONT of the plane (toward the hall), positive = through it."""
    return -e['s'] * (C[:, 0] - plane)


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   A camera whose height is below the top of the glass must be on the deck side of the glass.')
    print('   One standing more than %.3f m in front of the drawn face plane while below the drawn top' % POSERR)
    print('   (deck + railTops) is through the glass and is a CONTRADICTION. The null moves the plane')
    print('   back by %s m. The bound claimed is one-sided: the plane can sit no further back than the'
          % ' and '.join('%.2f' % n for n in NULLS))
    print('   5th percentile of the below-top cameras plus %.3f m. The deck is bracketed by the tallest' % POSERR)
    print('   tenth of each capture less the carry range measured on the hall floor.')
    print('')
    pool = []
    for cn in FLOORCL:
        C = cams(cn)
        h = C[:, 2]
        h = h[np.logical_and(h < 3.0, np.logical_and(C[:, 0] > -1, C[:, 0] < 53))]
        pool.append(h)
    pool = np.concatenate(pool)
    clo, chi = float(np.percentile(pool, PLO)), float(np.percentile(pool, PHI))
    print('   the carry range on the hall floor: %.3f to %.3f m over %d frames.' % (clo, chi, len(pool)))
    print('')
    allc = {cn: cams(cn) for cn in DECKCL}
    verdicts = []
    for name in ('east', 'west'):
        e = ENDS[name]
        print('   %s gallery: face u %.3f, glass top h %.3f, upstand top h %.3f, deck h %.3f'
              % (name.upper(), e['face'], e['top'], e['ups'], DECK))
        below, above, per = [], [], []
        for cn in DECKCL:
            C = on_deck(allc[cn], e)
            if len(C) == 0:
                continue
            b = C[C[:, 2] < e['top']]
            a = C[C[:, 2] >= e['top']]
            below.append(b)
            above.append(a)
            per.append((cn, len(C), len(b), len(a), float(np.percentile(C[:, 2], PHI)) if len(C) >= MINF else None))
            print('      %-6s %4d on the deck, %4d below the glass top, %4d above; u %.2f to %.2f, h %.2f to %.2f'
                  % (cn, len(C), len(b), len(a), C[:, 0].min(), C[:, 0].max(), C[:, 2].min(), C[:, 2].max()))
        if not per:
            print('      nobody stands on this deck. Nothing is read.')
            print('')
            continue
        B = np.concatenate(below) if below else np.zeros((0, 3))
        if len(B) < MINF:
            print('      only %d cameras below the glass top: too few to read the plane.' % len(B))
        else:
            f = infront(B, e, e['face'])
            bad = int((f > POSERR).sum())
            print('      %d cameras below the glass top. %d stand more than %.3f m in front of the drawn face:'
                  % (len(B), bad, POSERR))
            print('      %s' % ('NO CONTRADICTION' if bad == 0 else 'CONTRADICTION, listed below'))
            if bad:
                for row in B[f > POSERR][np.argsort(-f[f > POSERR])][:8]:
                    print('         u %.3f (%.3f m in front) d %.2f h %.3f' % (row[0], -e['s'] * (row[0] - e['face']), row[1], row[2]))
            print('      the furthest anyone below the top stands in front of the face: %.3f m; the nearest '
                  'behind it: %.3f m' % (f.max(), -f.min()))
            for n in NULLS:
                fn = infront(B, e, e['face'] + e['s'] * n)
                print('      NULL, plane moved back %.2f m: %d of %d through it (%.0f%%)'
                      % (n, int((fn > POSERR).sum()), len(B), 100.0 * (fn > POSERR).mean()))
            # the 5th percentile of how far toward the hall the below-top cameras stand, as a u value
            uq = float(np.percentile(B[:, 0], 5 if e['s'] > 0 else 95))
            ubound = uq + e['s'] * POSERR
            print('      THE BOUND: the glass plane sits no further back than u %.3f (5th percentile of the'
                  % ubound)
            print('      below-top cameras %.3f, plus %.3f m pose error); drawn on %.3f, so it is %.3f m'
                  % (uq, POSERR, e['face'], abs(ubound - e['face'])))
            print('      of room behind the drawn plane and none in front of it that this can see.')
            verdicts.append((name, len(B), bad, ubound))
        print('      deck bracket from the tallest tenth less the carry range:')
        for cn, n, nb, na, tall in per:
            if tall is None:
                print('         %-6s %4d frames, too few to read' % (cn, n))
                continue
            lo, hi = tall - chi, tall - clo
            if lo <= DECK <= hi:
                tag = 'consistent'
            elif lo > DECK:
                tag = 'REFUTED, deck is higher by at least %.3f m' % (lo - DECK)
            else:
                tag = 'no verdict, phone lowered'
            print('         %-6s tallest tenth %.3f, deck between %.3f and %.3f: %s' % (cn, tall, lo, hi, tag))
        print('')
    if not verdicts:
        print('   NO END HAS ENOUGH CAMERAS BELOW THE GLASS TOP. Nothing is concluded about the plane.')
        return
    for name, n, bad, ub in verdicts:
        e = ENDS[name]
        print('   %s: %d cameras below the glass top, %d through the drawn plane; the plane is no further'
              % (name.upper(), n, bad))
        print('   back than u %.3f, %.3f m behind the drawn face.' % (ub, abs(ub - e['face'])))


if __name__ == '__main__':
    main()
