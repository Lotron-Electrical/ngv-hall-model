# 2026-09-09: write the jamb measurement into tools/check_bounds.py as real checks, so the openings can
# never drift back without something failing.
import io

ANCHOR = "check('the reveal is at least as deep as the rays that crossed it',"

BLOCK = '''# THE JAMBS, MEASURED, tools/jamb_lines.py (2026-09-09). The same two-unknown line fit turned a third
# way: a jamb is a VERTICAL line at constant (u, d) spanning h, so a ray meets one when
# vd*(u* - cu) - vu*(d* - cd) = 0, and the conditioning comes from cameras spread ALONG the hall, which
# gives a 35 m baseline against the 9 m the sill and head had. Nothing drawn was searched for: every
# brightness step above the bar anywhere on the wall became a ray, and lines were PEELED off strongest
# first until nothing had support left. Nine survived a depth gate that threw out four more sitting up to
# a metre out in the hall. Both polarities moved the SAME way, which a detector bias cannot do, so the
# openings were moved +0.147 m east as one rigid set, tools/apply_jamb_shift.py.
JAMBS = ((22.563, -0.208, 64, 0.010), (26.293, -0.213, 62, 0.015), (29.976, -0.211, 70, 0.015),
         (33.642, -0.206, 49, 0.011), (20.027, -0.210, 57, 0.018), (23.748, -0.204, 76, 0.015),
         (27.479, -0.205, 71, 0.009), (31.171, -0.203, 50, 0.009), (34.877, -0.216, 36, 0.017))
_jedges = sorted([u for pair in OPEN for u in pair])
_joff = [j[0] - min(_jedges, key=lambda t: abs(t - j[0])) for j in JAMBS]
check('the twelve north openings stand where the jambs were measured',
      max(abs(o) for o in _joff) <= 0.12,
      'nine jamb lines, four of one polarity and five of the other, fitted from cameras spread 35 m along '
      'the hall and agreeing with their own rays to 9 to 18 mm. Against the openings as drawn they are '
      'offset by a median %+.3f m, worst %+.3f m.' % (sorted(_joff)[len(_joff) // 2],
                                                      max(_joff, key=abs)),
      'tools/jamb_lines.py')
check('every jamb line lies on the north wall rather than out in the hall',
      max(abs(j[1] - G['dNorth']) for j in JAMBS) <= 0.30,
      'the nine fitted depths span d %.3f to %.3f, a %.0f mm band, against a wall face drawn on %.3f. '
      'They sit %.3f m behind it, which is the arris the detector actually finds; four further lines were '
      'rejected outright because their own depth put them up to a metre out in the hall.'
      % (min(j[1] for j in JAMBS), max(j[1] for j in JAMBS),
         1000 * (max(j[1] for j in JAMBS) - min(j[1] for j in JAMBS)), G['dNorth'],
         abs(sum(j[1] for j in JAMBS) / len(JAMBS) - G['dNorth'])),
      'tools/jamb_lines.py')
check('the openings are as wide as the pairs of jambs measured end to end',
      abs((OPEN[0][1] - OPEN[0][0]) - 1.191) <= 0.05,
      'drawn %.3f m wide. Four openings were caught by both polarities and measure 1.185, 1.186, 1.195 '
      'and 1.235, median 1.191, so the drawing is %+.3f m wider. That gap is about 10 mm per edge and is '
      'exactly the bias a brightness step carries into the dark side, so the width was NOT changed.'
      % (OPEN[0][1] - OPEN[0][0], (OPEN[0][1] - OPEN[0][0]) - 1.191),
      'tools/jamb_lines.py')
'''

target = 'tools/check_bounds.py'
s = io.open(target, encoding='utf-8').read()
assert ANCHOR in s, 'anchor moved'
assert 'JAMBS = ' not in s, 'already added'
s = s.replace(ANCHOR, '%s%s' % (BLOCK, ANCHOR), 1)
io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('three jamb bounds added above the reveal check')
