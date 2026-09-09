# 2026-09-09: add the where-people-stood check on the openings, and record what the corridor route
# actually died of.
import io

ANCHOR = "check('the reveal is at least as deep as the rays that crossed it',"

BLOCK = '''# THE OPENINGS TESTED BY WHERE PEOPLE STOOD, tools/lens_in_aperture.py (2026-09-09). No detector, no
# contrast threshold, no polarity: three clips were shot from INSIDE north apertures, and 167 of their
# posed lenses sit at aperture height BEHIND the wall face, which means each one is a point that was not
# inside masonry. That is a hard one-sided bound on the jamb either side of it, and it is independent of
# the nine fitted lines the openings were moved on, so it is a real check on that move rather than a
# restatement of it. The bar is each clip's own near-field self-miss, tools/pose_selfcheck.py.
# The first version of this test allowed any lens within a metre of the wall and promptly reported a
# violation, because it counted b4 frames sitting 0.87 m OUT in the hall leaning back to shoot along the
# wall. A lens in front of the face is not in the hole and no jamb constrains it. Corrected, nothing fails.
APERTURE = ((5, 89, 19.364, 19.707, 0.068, 'b1'), (6, 73, 23.164, 23.655, 0.069, 'b5'),
            (11, 5, 41.179, 41.990, 0.067, 'b4'))
_worst, _worstn = 9.9, ''
for _k, _n, _umin, _umax, _bar, _clip in APERTURE:
    _lo, _hi = OPEN[_k - 1]
    for _m, _side in ((_umin - _lo, 'west'), (_hi - _umax, 'east')):
        if _m < _worst:
            _worst, _worstn = _m, 'opening %d %s jamb, %s' % (_k, _side, _clip)
check('nobody stood inside a jamb',
      all(min(OPEN[k - 1][1] - umax, umin - OPEN[k - 1][0]) >= -bar
          for k, n, umin, umax, bar, clip in APERTURE),
      '167 posed lenses sit at aperture height behind the wall face, in openings 5, 6 and 11. Against the '
      'openings as the model now draws them the tightest clearance is %+.3f m at the %s, and the bar '
      'there is that clip\\'s own %.3f m self-miss. This is the only test of the jamb move that uses no '
      'pixels at all.' % (_worst, _worstn, 0.069),
      'tools/lens_in_aperture.py')
check('the reveal is at least as deep as the lens that stood in it',
      G['openDepth'] >= 0.362 - 1e-9,
      'openDepth %.3f. b1_000057 sits 0.362 m behind the wall face between a measured pair of jambs and '
      'above the measured sill, so it was standing in the reveal and the reveal is at least that deep. '
      'That is a floor and not a value, and it is weaker than the 0.9 m the traced rays already give, so '
      'nothing moves on it.' % G['openDepth'],
      'tools/lens_in_aperture.py')
'''

target = 'tools/check_bounds.py'
s = io.open(target, encoding='utf-8').read()
assert ANCHOR in s, 'anchor moved'
assert 'APERTURE = ' not in s, 'already added'
s = s.replace(ANCHOR, '%s%s' % (BLOCK, ANCHOR), 1)

OLDNOTE_HEAD = "for line in ('the corridor floor 8.34, its back wall d -2.09"
i = s.index(OLDNOTE_HEAD)
j = s.index("tools/corridor_lines.py',", i) + len("tools/corridor_lines.py',\n")
NEWNOTE = ("for line in ('the corridor floor 8.34, its back wall d -2.09 and its ceiling 11.4, and there "
           "are now TWO'\n"
           "             ' counted reasons rather than an absence. FROM THE HALL FLOOR the opening is a "
           "collimator:'\n"
           "             ' seeing the whole height ladder through a 1.2 m slot forces the lens far back, "
           "so the'\n"
           "             ' usable set collapses from an 8.64 m baseline to 1.59 m. The same detector, "
           "rays and fit'\n"
           "             ' reproduce the measured opening head to 23 mm with the two halves of the wall "
           "agreeing to'\n"
           "             ' 41 mm, then disagree by 573 mm two metres further back, tools/corridor_lines.py. "
           "FROM'\n"
           "             ' INSIDE THE OPENINGS there is no imagery at all: 317 posed lenses stand in north "
           "apertures'\n"
           "             ' and not one of them points into the room. The most inward-facing frame in the "
           "whole set'\n"
           "             ' still has its axis 0.38 of the way toward the hall. The operator stood in the "
           "holes and'\n"
           "             ' filmed the room he had come from, tools/opening_facing.py',\n")
s = '%s%s%s' % (s[:i], NEWNOTE, s[j:])
io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('aperture bounds added and the corridor note rewritten')
