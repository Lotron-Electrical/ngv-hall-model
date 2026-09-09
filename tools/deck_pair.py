# 2026-09-10: ARE THE TWO GALLERY DECKS AT THE SAME HEIGHT, ASKED SO THAT NOTHING SOFT IS LEFT IN IT.
#
# ENDW.floors[1] is 8.340 at BOTH ends and it has never been measured at either. The obvious route is the
# poses: people stood on those decks, so deck = eye height minus however high a phone is carried. That
# route is dead and this run shows why in one line. THREE CLIPS STAND ON THE SAME EAST DECK and their
# median eye heights are 9.606, 9.786 and 9.884. Two hundred and seventy-eight millimetres apart, on one
# floor. Carry height is not a constant, it is a habit, and it changes between clips by more than any
# number this would be trying to measure.
#
# SO ASK THE DIFFERENCE INSTEAD OF THE HEIGHT. One clip, b7s, walks onto the EAST gallery and the WEST
# gallery in the same session. Same person, same phone, same way of holding it, minutes apart. Subtract
# the two medians and the carry height cancels exactly, along with the device, the person and the habit.
# What is left is the difference between the two decks, and this file says that difference is zero.
#
# THE CONTROL IS THE NOISE FLOOR AND IT IS MEASURED, NOT ASSUMED. The same clip on the same gallery is
# split in half, by where along the gallery the operator stood and again odd against even frame, and
# those halves are differenced the same way. That says how big a difference this method invents when the
# true answer is known to be zero. A gap between the ends only means something if it is bigger than that.
#
# WHAT IT CANNOT DO. It cannot give the height of either deck. It compares them. If both are wrong by the
# same amount this says nothing at all, and that limit is the price of removing the carry height.
#   python tools/deck_pair.py
import io
import re
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
WFACE, EFACE = 4.194, 48.056
CLASSES = ('b3', 'b3p', 'b5', 'b5p', 'b6g', 'b6gp', 'b7s', 'b7sp', 'day4k', 'b1', 'b1p', 'b4')


def drawn():
    src = io.open('index.html', encoding='utf-8').read()
    return float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', src).group(1))


DECK = drawn()
print('index.html draws both gallery decks on h %.3f' % DECK)

byclip = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for k, v in (frames or {}).items():
        q = v[0].center - O
        u, d, h = float(q @ HU), float(q @ HD), float(q[1])
        if not (8.9 < h < 10.9) or not (0.5 < d < 14.9):
            continue
        side = 'east' if u > EFACE else ('west' if u < WFACE else None)
        if side:
            byclip.setdefault(cls, {'east': [], 'west': []})[side].append((h, d, k))

print('')
print('   clip      east frames   median      west frames   median      east minus west')
both = []
east_all = []
for cls in sorted(byclip):
    E, W = byclip[cls]['east'], byclip[cls]['west']
    em = float(np.median([x[0] for x in E])) if E else float('nan')
    wm = float(np.median([x[0] for x in W])) if W else float('nan')
    if len(E) >= 4:
        east_all.append((cls, em, len(E)))
    gap = '%+.3f m' % (em - wm) if (len(E) >= 4 and len(W) >= 4) else 'one side only'
    print('   %-8s %8d     %7.3f    %8d     %7.3f      %s'
          % (cls, len(E), em, len(W), wm, gap))
    if len(E) >= 4 and len(W) >= 4:
        both.append((cls, E, W, em - wm))

print('')
if len(east_all) >= 3:
    hs = [e[1] for e in east_all]
    print('   WHY THE ABSOLUTE ROUTE IS DEAD: %d clips stand on the SAME east deck and their median eye'
          % len(east_all))
    print('   heights run %.3f to %.3f, a spread of %.0f mm on one floor. Carry height is a habit, not a'
          % (min(hs), max(hs), 1000 * (max(hs) - min(hs))))
    print('   constant, and it moves further between clips than anything worth measuring.')
if not both:
    raise SystemExit('   no clip stands on both galleries, so the difference cannot be taken')


def halves(rows):
    """the same gallery split two ways, to say what this method invents when the answer is zero"""
    byd = sorted(rows, key=lambda r: r[1])
    n = len(byd) // 2
    a = abs(np.median([r[0] for r in byd[:n]]) - np.median([r[0] for r in byd[n:]]))
    b = abs(np.median([r[0] for r in rows[0::2]]) - np.median([r[0] for r in rows[1::2]]))
    return float(a), float(b)


print('')
print('   THE CONTROL, the same clip on the same gallery split in half:')
floors = []
for cls, E, W, gap in both:
    for side, rows in (('east', E), ('west', W)):
        if len(rows) < 6:
            continue
        a, b = halves(rows)
        floors.append(max(a, b))
        print('      %-6s %-5s  split by position %.0f mm, odd against even %.0f mm'
              % (cls, side, 1000 * a, 1000 * b))
if not floors:
    print('      too few frames on any one side to split, so there is no measured noise floor')
    raise SystemExit(0)
noise = max(floors)
gaps = [abs(g) for _, _, _, g in both]
print('')
print('   THE NOISE FLOOR IS %.0f mm, the worst this method invents when the true difference is zero.'
      % (1000 * noise))
print('   THE TWO DECKS DIFFER BY %s mm across %d clip(s).'
      % (' and '.join('%.0f' % (1000 * g) for g in gaps), len(both)))
# b7s AND b7sp ARE NOT TWO WITNESSES. One is a larger posed set of the same footage, so they are counted
# as one clip and said to be one, rather than quoted as agreement between independent runs.
print('   b7s and b7sp are the same footage posed twice, so this is ONE clip and not two, and it is')
print('   reported that way rather than as two instruments agreeing.')
if max(gaps) <= noise:
    print('')
    print('   THE TWO DECKS ARE AT THE SAME HEIGHT so far as this can tell, and the difference this file')
    print('   draws is zero. The gap measured is smaller than the gap the method invents on a known')
    print('   answer, so what is confirmed is the SYMMETRY and not either height. Every soft term, the')
    print('   carry height, the device and the person, cancelled in the subtraction rather than being')
    print('   assumed away, which is the only reason this is worth anything.')
else:
    print('')
    print('   THE ENDS DISAGREE BY MORE THAN THE NOISE FLOOR: %.0f mm against %.0f. The model draws them'
          % (1000 * max(gaps), 1000 * noise))
    print('   level, so one of the two decks is out, and the difference is real even though neither')
    print('   height is measured by this.')
