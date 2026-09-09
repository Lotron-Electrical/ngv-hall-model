# 2026-09-09: EVERY MEASURED BOUND ON THE BALCONIES, THE WALLS AND THE ROOM BEHIND THEM, AS ONE TEST.
#
# A day of measurement produced a dozen hard bounds and three moved surfaces, and every one of them lives
# as prose in a comment. Prose does not fail when somebody edits a number. The bounds are all of the same
# shape, "this ray arrived so nothing was in its way" or "these points are on that surface", so they can
# be written down once and checked against the shipped geometry on demand. That is what this is: it reads
# the geometry OUT of index.html and tools/tapestries.json exactly as the browser does, evaluates every
# bound the archive has actually produced, and exits non-zero if the sim has drifted outside any of them.
#
# WHAT A PASS MEANS, and it is worth being precise because the temptation is to read it as "the model is
# right". It means the model contradicts nothing the imagery could prove. Several of these bounds are
# one-sided and wide: the opening head has a floor of 10.468 under it and is drawn on 11.35, so a head
# half a metre out would pass. The width of each bracket is printed beside its verdict for that reason,
# and the numbers that remain UNMEASURED are listed afterwards rather than quietly omitted.
#
# Every bound carries the tool that produced it, so a disputed line can be re-derived rather than argued.
#   python tools/check_bounds.py
import json
import re
import sys

src = open('index.html', encoding='utf-8').read()
tap = json.load(open('tools/tapestries.json', encoding='utf-8'))

O = (-54.907447, -1.43545, 3.040286)
HD = (0.219196, 0.0, -0.975681)


def grab(pattern):
    m = re.search(pattern, src)
    if m is None:
        raise SystemExit('could not read ' + pattern)
    return float(m.group(1))


mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(x) for x in p.split(',')] for p in re.findall(r'\[([-0-9.]+,[-0-9.]+)\]', mo.group(1))]
G = {
    'sill': grab(r'openY:\[([0-9.]+),'),
    'head': grab(r'openY:\[[0-9.]+,\s*([0-9.]+)\]'),
    'dNorth': grab(r'dNorth:(-?[0-9.]+)'),
    'dSouth': grab(r'dSouth:([0-9.]+)'),
    'uMin': grab(r'uMin:([0-9.]+)'),
    'uMax': grab(r'uMax:([0-9.]+)'),
    'face': grab(r'face:([0-9.]+)'),
    'openDepth': grab(r'openDepth:([0-9.]+)'),
    'cWidth': grab(r'corridor:\{width:([0-9.]+)'),
    'cCeil': grab(r'corridor:\{width:[0-9.]+,\s*floor:[0-9.]+,\s*ceil:([0-9.]+)'),
    'deck': grab(r'floors:\[[0-9.]+,\s*([0-9.]+)\]'),
    'gHead': grab(r'head:([0-9.]+), soffitDepth'),
    'upWest': grab(r'upstands:\{west:([0-9.]+)'),
    'upEast': grab(r'upstands:\{west:[0-9.]+,\s*east:([0-9.]+)\}'),
    'setWest': grab(r'upstandSet:\{west:([0-9.]+)'),
    'setEast': grab(r'upstandSet:\{west:[0-9.]+,\s*east:([0-9.]+)\}'),
    'endFace': grab(r'top:13.5, face:([0-9.]+)'),
    'endWest': grab(r'const ENDW=\{west:([0-9.]+)'),
    'lowRail': grab(r'slab:0.26, rails:\[([0-9.]+)'),
    'lowUp': grab(r'lowUpstand:([0-9.]+)'),
    'railWest': grab(r'railTops:\{west:([0-9.]+)'),
    'railEast': grab(r'railTops:\{west:[0-9.]+,\s*east:([0-9.]+)\}'),
}
G['cBack'] = G['dNorth'] - G['cWidth']

lamps = re.search(r'lamps:\[(\[.*?\])\]\}', src)
LAMPS = [[float(x) for x in t.split(',')] for t in re.findall(r'\[([-0-9.,]+)\]', lamps.group(1))] if lamps else []
# RE-RUN 2026-09-09 after the openings moved 0.147 m and the wall face moved to -0.030. The aperture
# gate that decides which rays may vote for a lamp depends on both, so the old array was built on
# superseded geometry. Re-run, the three collapse onto one level.
MEASURED_LAMPS = [[30.524, -2.068, 10.942], [34.139, -2.049, 10.935], [42.043, -1.824, 10.908]]
OLD_LAMPS = [[30.642, -1.093, 10.374], [34.139, -2.144, 10.990], [42.043, -1.824, 10.908]]
# the near-far parallax test on each lamp's own ray bundle: measured?, best depth, height, ratio,
# leverage (tools/lamp_v.py)
LAMPV = {8: (True, -2.368, 11.117, 5.6, 5.69), 9: (True, -1.849, 10.807, 3.3, 12.52),
         11: (False, -1.624, 10.793, 1.8, 1.54)}

southtap = []
for t in tap['tapestries']:
    ds = [sum((c[k] - O[k]) * HD[k] for k in range(3)) for c in t['corners']]
    d = sum(ds) / len(ds)
    if d > 8.0:
        southtap.append(d)

fails, notes = [], []


def check(name, ok, detail, source):
    notes.append((ok, name, detail, source))
    if not ok:
        fails.append(name)


# --- the room behind the wall -------------------------------------------------------------------
check('corridor is deep enough for the lamps inside it',
      G['cBack'] <= min(L[1] for L in MEASURED_LAMPS) + 0.062,
      'back wall drawn on d %.3f; the deepest triangulated lamp sits on d %.3f with about 0.05 m ray '
      'agreement, so the wall can be no shallower than %.3f. Clearance %.3f m.'
      % (G['cBack'], min(L[1] for L in MEASURED_LAMPS),
         min(L[1] for L in MEASURED_LAMPS) + 0.062,
         min(L[1] for L in MEASURED_LAMPS) + 0.062 - G['cBack']),
      'tools/corridor_lamp.py')
# THE REVEAL, MEASURED FROM INSIDE FOR THE FIRST TIME (2026-09-09, tools/point_v.py). All eight points the
# corridor blob search ever returned were put through the parallax split, including the five that were
# discarded for not looking like lamps. One of the discarded ones is the best-conditioned measurement this
# archive has behind that wall.
REVEALPT = {'u': 26.483, 'd': -0.659, 'h': 11.359, 'rays': 23, 'ratio': 88.4, 'gapmin': 0.018,
            'gapmax': 2.074, 'null': 0.023}
check('the reveal is at least as deep as the point measured inside it',
      G['openDepth'] >= (G['dNorth'] - REVEALPT['d']) - 1e-9,
      'opening 7 carries a point on u %.3f, d %+.3f, h %.3f from %d rays, whose two camera halves agree '
      'to %.0f mm there and disagree by %.0f mm at the end of the sweep on a null of %.0f. A ratio of '
      '%.1f, where the best corridor lamp gives 5.6 and every line in that room gives under 3. It stands '
      '%.3f m behind the wall face, so the reveal is at least that deep. It is drawn %.2f m. The lower '
      'bound was already 0.362 from a lens that leaned that far in, so this is not the first support for '
      'it; it nearly doubles it, and it does so by a different principle, a triangulated point rather '
      'than a camera position.'
      % (REVEALPT['u'], REVEALPT['d'], REVEALPT['h'], REVEALPT['rays'], 1000 * REVEALPT['gapmin'],
         1000 * REVEALPT['gapmax'], 1000 * REVEALPT['null'], REVEALPT['ratio'],
         G['dNorth'] - REVEALPT['d'], G['openDepth']),
      'tools/point_v.py')
check('the flat reveal soffit is recorded as contradicted, not assumed',
      REVEALPT['h'] > G['head'],
      'the same point stands %.3f m ABOVE the measured opening head, inside the volume the model draws as '
      'solid stone over the reveal. A blob finder found it and masonry does not light up, so the likeliest '
      'reading is a fitting recessed into the soffit rather than a splayed head. One point cannot tell a '
      'recess from a splay, so nothing is redrawn, but this is now a known contradiction rather than an '
      'untested assumption.' % (REVEALPT['h'] - G['head']),
      'tools/point_v.py')
check('the two estimators on a lamp bundle disagree, and the bracket reflects it',
      abs(LAMPV[8][1] - (-2.068)) <= 0.35 and abs(LAMPV[9][1] - (-2.049)) <= 0.35,
      'the parallax minima put the two testable lamps on %.3f and %.3f while their own least-squares '
      'points sit on -2.068 and -2.049. Two estimators on the SAME rays, disagreeing by %.0f and %.0f mm '
      'in opposite directions. That scatter is the honest uncertainty on a lamp depth, and it is why the '
      'deeper of the two does not get to move the back wall.'
      % (LAMPV[8][1], LAMPV[9][1], 1000 * abs(LAMPV[8][1] + 2.068), 1000 * abs(LAMPV[9][1] + 2.049)),
      'tools/lamp_v.py')
check('the lamps agree with each other on a level, which they never did before',
      max(L[2] for L in MEASURED_LAMPS) - min(L[2] for L in MEASURED_LAMPS) <= 0.10,
      'the three heights now span %.0f mm across 11.5 m of corridor, where the array shipped until '
      'tonight spanned %.0f mm in height and %.0f in depth. That array was computed before the openings '
      'moved and before the wall face moved, and the aperture gate depends on both. One of its lamps was '
      'a metre out in depth and 0.57 m out in height. Three lamps on one level 11.5 m apart is what a '
      'corridor is lit like.'
      % (1000 * (max(L[2] for L in MEASURED_LAMPS) - min(L[2] for L in MEASURED_LAMPS)),
         1000 * (max(L[2] for L in OLD_LAMPS) - min(L[2] for L in OLD_LAMPS)),
         1000 * (max(L[1] for L in OLD_LAMPS) - min(L[1] for L in OLD_LAMPS))),
      'tools/corridor_lamp.py')
check('the back wall sits inside the bracket the testable lamps allow',
      min(v[1] for v in LAMPV.values() if v[0]) <= G['cBack'] <= max(v[1] for v in LAMPV.values() if v[0]),
      'a POINT can be tested where a line cannot: a line in that room is separated only by cameras at '
      'different distances and the slot collapses that to a leverage of 1.32, while a point is separated '
      'by the angular spread of the rays that see it. Lamp 8 gives the sharpest signal anything has '
      'produced inside the corridor, its two camera halves agreeing to 6 mm on d %.3f against 242 mm at '
      'the end of the sweep on a null never past 43, a ratio of %.1f on a leverage of %.2f. Lamp 9 '
      'carries a softer minimum on %.3f. Lamp 11 refuses, its leverage only %.2f. So the lamp plane is '
      'bracketed between %.3f and %.3f and the wall drawn on %.3f sits inside it. Bracketed, not pinned, '
      'and nothing is moved on it.'
      % (LAMPV[8][1], LAMPV[8][3], LAMPV[8][4], LAMPV[9][1], LAMPV[11][4],
         min(v[1] for v in LAMPV.values() if v[0]), max(v[1] for v in LAMPV.values() if v[0]),
         G['cBack']),
      'tools/lamp_v.py')
check('the three corridor lamps are drawn where they were measured',
      len(LAMPS) == 3 and all(abs(a - b) < 0.001
                              for L, M in zip(sorted(LAMPS), sorted(MEASURED_LAMPS))
                              for a, b in zip(L, M)),
      '%d lamps in WALLF.corridor' % len(LAMPS),
      'tools/corridor_lamp.py')
check('the corridor ceiling is above its own lamps',
      G['cCeil'] > max(L[2] for L in MEASURED_LAMPS),
      'ceiling drawn on %.3f, the highest lamp measured inside the room on 10.942. Clearance %.3f m. '
      'This is the ONLY constraint on that ceiling and it is one-sided.' % (G['cCeil'], G['cCeil'] - 10.990),
      'tools/corridor_lamp.py')

# --- the openings -------------------------------------------------------------------------------
check('the opening head clears every ray that came through it',
      G['head'] >= 10.468,
      'head drawn on %.3f, the highest surviving ray reaches 10.468 inside the reveal. The bracket is '
      'one-sided and %.3f m wide, so it cannot settle the lean.' % (G['head'], G['head'] - 10.468),
      'tools/opening_bound.py')
check('the opening sill clears every ray that came through it',
      G['sill'] <= 9.683,
      'sill drawn on %.3f, the lowest surviving ray reaches 9.683. Bracket %.3f m wide.'
      % (G['sill'], 9.683 - G['sill']),
      'tools/opening_bound.py')
for oi, bay, (rlo, rhi) in ((8, OPEN[7], (30.009, 30.986)),
                            (9, OPEN[8], (33.736, 34.256)),
                            (11, OPEN[10], (40.948, 41.674))):
    lo, hi = bay
    check('opening %d is wide enough for the rays that passed it' % oi,
          lo <= rlo and hi >= rhi,
          'drawn u %.3f to %.3f; rays occupied %.3f to %.3f, so the jambs have %.3f m and %.3f m to spare.'
          % (lo, hi, rlo, rhi, rlo - lo, hi - rhi),
          'tools/opening_bound.py')
# THE SILL AND THE HEAD AS MEASURED LINES, not one-sided caps (tools/wall_lines.py). The far-edge fit that
# moved the balcony fronts, turned ninety degrees: an opening's sill and head are lines at constant (d, h)
# spanning u, and the conditioning comes from cameras at different distances from the wall, an 8.88 m
# baseline. Two polarities name the two edges, and 97 and 95 per cent of the inliers land inside a drawn
# opening while the openings cover half the wall, so the lines are the openings' own and not the face's.
# ANCHORED TO THE FACE, tools/anchor_to_face.py (2026-09-09). These two were reported from a single
# averaging window each. Put through three windows with the RANSAC band narrowed so all three had to find
# the SAME feature, the sill moved 149 mm in height and 285 mm in depth while the head moved 22 and 26.
# They did not scatter, they SLID: the three sill answers sit on one straight line in the (d, h) plane to
# within 0 mm, which is the degenerate direction of the fit rather than three independent results. The
# rays never separated that edge's depth from its height. Sliding each fit along its own line onto the
# INDEPENDENTLY measured wall face collapses the sill's spread from 149 mm to 0 and the head's from 22
# to 5, and those anchored values are what the model now draws.
# SUPERSEDED THE SAME EVENING, and for the better: the anchor is no longer assumed. tools/depth_v.py
# splits the rays by camera distance and finds a real minimum, and the sill and head land on the SAME
# plane d -0.030 from separate ladders of opposite polarity, so these heights are now read on a MEASURED
# depth rather than slid onto a drawn one. The uncertainty falls from the 0.05 m the drawn plane carried
# to about the 0.02 m step of that sweep, so roughly 14 mm on a sensitivity of 0.69 m per metre.
for name, key, meas, west, east in (('sill', 'sill', 8.740, 8.778, 8.777),
                                    ('head', 'head', 11.165, 11.223, 11.220)):
    check('the opening %s is drawn where the hall floor measures it' % name,
          abs(G[key] - meas) <= 0.006,
          'drawn on %.3f against a measured %.3f, so %+.3f m out. Three averaging windows, each forced '
          'to find the same feature and then slid onto the measured face, give %.3f and %.3f, %.3f m '
          'apart, but that spread was never the accuracy: it was three windows sharing one ASSUMED depth. '
          'The depth is now measured, both edges landing on d -0.030, so these are read on a real plane '
          'and carry roughly 14 mm from the 0.02 m step of that sweep.'
          % (G[key], meas, G[key] - meas, west, east, abs(west - east)),
          'tools/wall_lines.py')
# AND THE PRECISION CLAIMED FOR THIS ONE WAS WRONG, tools/face_depth_scan.py (2026-09-09). Stop fitting
# the depth and SCAN it: fix d, and each ray gives the height directly with nothing left to slide. Swept
# across the head rays the inlier count is flat, staying within 2 per cent of its peak from d -0.190 to
# +0.080, a band 270 mm wide. These rays do not measure the depth of this wall at all; they measure one
# combination of depth and height, 0.69 m of height for every metre of depth. The count does peak exactly
# on the drawn -0.090 and the residual is lowest between -0.08 and -0.02, which is why the drawn value
# stands, but "the sill line puts the face on -0.058 and the head line on -0.107" was never two
# measurements of a depth. It was two arbitrary points on the same slide.
check('the north wall face is where two independent edges put it',
      abs(G['dNorth'] - (-0.030)) <= 0.02,
      'drawn on d %.3f. The near-far split with its own null finds a real minimum for BOTH edges and puts '
      'them on the same plane: the sill on -0.030 with its halves 1 mm apart there against 26 mm by the '
      'far end of its sweep on a null of 3, a ratio of 9.1, and the head on -0.030 with 2 mm against 55 '
      'on a null of 15, a ratio of 3.7. Separate ladders, opposite polarities, a quarter of the rays '
      'between them, one plane. The count-based scan that called this unmeasurable was reading a blunt '
      'statistic: a wrong plane moves every ray the same way before it spreads them, so the consensus '
      'peak follows the error and keeps its rays.'
      % G['dNorth'],
      'tools/depth_v.py')
# THE OPENING SHIFT, AUDITED WITH THE STRONGEST TEST AVAILABLE (2026-09-09, tools/jamb_v.py). Five of the
# twelve north openings were moved 0.147 m east on nine two-unknown jamb fits, and that was the last piece
# of geometry in this model still resting on a fit the near-far split had never seen.
JAMBV = {'minima': 5, 'testable': 8, 'meanlo': -0.021, 'meanhi': 0.027, 'span': 0.18,
         'atfit': -0.005, 'scatter': 0.074, 'shift': 0.147}
check('the opening shift does not rest on the jamb depth, which is the soft direction',
      (JAMBV['meanhi'] - JAMBV['meanlo']) < 0.5 * JAMBV['shift'],
      'sweeping the assumed jamb depth across %.2f m, more than ten times what the nine free fits '
      'disagreed by, moves the MEAN residual between the jamb stations and the edges the model draws only '
      'from %+.0f to %+.0f mm, a range of %.0f mm against a shift of %.0f. Single stations wander far '
      'more than that, up to 456 mm, but the wander is common to all nine and cancels out of the '
      'agreement the openings were actually drawn from. The first version of this check treated one '
      'wandering station as the verdict and would have withdrawn the shift on it.'
      % (JAMBV['span'], 1000 * JAMBV['meanlo'], 1000 * JAMBV['meanhi'],
         1000 * (JAMBV['meanhi'] - JAMBV['meanlo']), 1000 * JAMBV['shift']),
      'tools/jamb_v.py')
check('the north openings carry a stated per-opening accuracy, not just a mean',
      JAMBV['scatter'] <= 0.10,
      'at the fitted depth the mean residual is %+.0f mm, so the set is right in AVERAGE position to five '
      'millimetres, but the nine jambs scatter about it by 51 to %.0f mm. Any claim about ONE opening '
      'edge has to live inside that, and none is made.'
      % (1000 * JAMBV['atfit'], 1000 * JAMBV['scatter']),
      'tools/jamb_v.py')
check('the jamb arris is behind the face by a test that can refuse it',
      JAMBV['minima'] >= 4,
      '%d of the %d testable jambs carry a real near-far minimum in depth, so the arris genuinely stands '
      'behind the wall face. The other three fail their own null or minimise on the edge of the sweep, '
      'and the minima scatter from -0.050 to -0.213 against the 13 mm the free fits agreed to, so the '
      'jamb DEPTH is much softer than it looked and nothing is drawn on it.'
      % (JAMBV['minima'], JAMBV['testable']),
      'tools/jamb_v.py')
check('the corridor back wall stays where the lamps put it, whatever the face does',
      abs(G['cBack'] - (-2.090)) <= 0.01,
      'the back wall is drawn as the face minus the width, so moving the face 0.060 m into the hall moved '
      'it too, and it landed IN FRONT of the deepest triangulated lamp on d -2.144. That wall was never '
      'measured from the face; it was placed by those lamps. So the WIDTH absorbed the move, 2.00 to '
      '2.06, and the wall stayed on %.3f.' % G['cBack'],
      'tools/corridor_lamp.py')
# THE JAMBS, MEASURED, tools/jamb_lines.py (2026-09-09). The same two-unknown line fit turned a third
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
# THE JAMBS PUT THROUGH THE SAME AUDIT THAT CAUGHT THE SILL, and they pass it (2026-09-09,
# tools/jamb_lines.py with HWIN and ANCHORD). The sill turned out to be a degenerate fit: three averaging
# windows slid it 149 mm in height and 285 mm in depth along one straight line. The jambs are the same
# two-unknown fit and they moved ten numbers in this model, so they owed the same test.
# THEY DO NOT SLIDE. Across windows of 20 and 40 samples the jambs common to both read 26.280 against
# 26.293, 33.630 against 33.642, 23.784 against 23.748, 27.492 against 27.479 and 31.185 against 31.171:
# 12 to 36 mm of station, and 2 to 10 mm of depth where the sill moved 285.
# AND THE DEPTH THEY REPORT IS REAL, WHICH THE ANCHORING TEST SETTLES POSITIVELY RATHER THAN BY ASSERTION.
# All nine sit on d -0.203 to -0.216 while the wall face is drawn on -0.090. Forcing the depth onto that
# face and solving for the station alone does not tidy them up, it FRAGMENTS each jamb into two or three
# lines spread over 0.33 m, because rays that really meet an edge 0.117 m further back cannot agree about
# where it is on the wrong plane. The free fit finds one line per jamb with a 10 mm median; the anchored
# one cannot. So the visible jamb arris genuinely stands about 0.117 m behind the drawn face.
JAMBWIN = ((26.280, 26.293), (33.630, 33.642), (23.784, 23.748), (27.492, 27.479), (31.185, 31.171))
check('the jamb fits do not slide with the averaging window',
      max(abs(a - b) for a, b in JAMBWIN) <= 0.05,
      'the five jambs found at both windows of 20 and 40 samples move by at most %.0f mm in station, '
      'against a sill that slid 149 mm in height and 285 mm in depth through the same test. The opening '
      'shift of +0.147 m rests on these, so it rests on numbers that hold still.'
      % (1000 * max(abs(a - b) for a, b in JAMBWIN)),
      'tools/jamb_lines.py')
check('the visible jamb arris is behind the wall face, not on it',
      abs(abs(-0.207 - G['dNorth']) - 0.177) <= 0.03,
      'the nine jamb lines average d -0.207 against a face drawn on %.3f, so the arris the detector finds '
      'stands %.3f m back. That is not a fitting artefact: fixing the depth to the face and solving for '
      'the station alone fragments each jamb into two or three lines spread over 0.33 m, where the free '
      'fit gives one line per jamb with a 10 mm median.' % (G['dNorth'], abs(-0.207 - G['dNorth'])),
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
# THE OPENINGS TESTED BY WHERE PEOPLE STOOD, tools/lens_in_aperture.py (2026-09-09). No detector, no
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
      'there is that clip\'s own %.3f m self-miss. This is the only test of the jamb move that uses no '
      'pixels at all.' % (_worst, _worstn, 0.069),
      'tools/lens_in_aperture.py')
check('the reveal is at least as deep as the lens that stood in it',
      G['openDepth'] >= 0.362 - 1e-9,
      'openDepth %.3f. b1_000057 sits 0.362 m behind the wall face between a measured pair of jambs and '
      'above the measured sill, so it was standing in the reveal and the reveal is at least that deep. '
      'That is a floor and not a value, and it is weaker than the 0.9 m the traced rays already give, so '
      'nothing moves on it.' % G['openDepth'],
      'tools/lens_in_aperture.py')
check('the reveal is at least as deep as the rays that crossed it',
      G['openDepth'] >= 0.9 - 1e-9,
      'openDepth %.3f; rays were traced 0.9 m in and were still inside the aperture.' % G['openDepth'],
      'tools/opening_bound.py')

# --- the end balconies --------------------------------------------------------------------------
check('the east gallery ceiling is under the lamps seen past it',
      G['gHead'] <= 11.633,
      'soffit drawn on %.3f; the tightest ray to a fitting under it crosses the gallery face on 11.633, '
      'and a slab higher than that would have caught the ray. Clearance %.3f m.'
      % (G['gHead'], 11.633 - G['gHead']),
      'tools/gallery_lamp.py')
check('the west gallery ceiling is under the lamp seen past it',
      G['gHead'] <= 11.825,
      'same test on the west end, tightest crossing 11.825. Clearance %.3f m.' % (11.825 - G['gHead']),
      'tools/gallery_lamp.py')
check('the gallery ceiling is above the people who stood under it',
      G['gHead'] >= 10.23,
      'soffit drawn on %.3f; deck cameras stand as high as h 10.23. With the line above, the bracket is '
      '10.230 to 11.633, %.3f m wide.' % (G['gHead'], 11.633 - 10.230),
      'tools/balcony_up.py')
check('the east parapet face is behind the operator who walked past it',
      G['uMax'] - G['face'] <= 48.145,
      'face drawn on u %.3f (uMax %.3f less face %.3f). 163 posed cameras stand on the east deck across '
      'three clips, and the westernmost lens is b3_000125 on u 47.895. A face further west than 48.145 '
      'would have put that lens more than the 0.25 m of a lean over the coping out into the hall, and the '
      'rival line u 48.702 from the silhouette fit would have put 140 of the 163 over the void, a median '
      'of 0.445 m and as much as 0.807 m. Clearance %.3f m.'
      % (G['uMax'] - G['face'], G['uMax'], G['face'], 48.145 - (G['uMax'] - G['face'])),
      'tools/parapet_arrival.py')
check('the east parapet top is under the light that got over it',
      G['deck'] + 0.77 <= 9.363 + 1e-9,
      'top drawn on %.3f, which is the deck %.3f plus 0.770. Of 7,141 rays that reached a deck camera from '
      'a point inside the hall and crossed that face, the 5th percentile crossed on 9.363 and only 1.62%% '
      'crossed below the drawn top, so a parapet drawn there stops almost none of the light that actually '
      'arrived. Bracket 9.110 to 9.363, %.3f m wide.'
      % (G['deck'] + 0.77, G['deck'], 9.363 - (G['deck'] + 0.77)),
      'tools/parapet_arrival.py')
check('the top deck is below every camera that stood on it',
      G['deck'] <= 9.416,
      'deck drawn on %.3f; the lowest camera standing on a gallery is h 9.416.' % G['deck'],
      'tools/balcony_up.py')

# THE HEAD OVER THE TOP GALLERY, MEASURED AT BOTH ENDS, tools/soffit_back.py (2026-09-09). The soffit
# is the ceiling of the end bay: a horizontal surface running from the balcony face back to the end wall.
# Its FRONT edge is a horizontal line at constant (u, h) spanning the hall, which is the fourth
# orientation of the same two-unknown fit, and the parity is the lit one because the gallery back wall
# below it is bright and the soffit underside is 0.37 times that by day.
# The instrument passed a control first: pointed at the balcony front top, an edge two other tools had
# already pinned, it recovered h 9.795 against a measured 9.799 from 306 rays with a 13 mm median.
# endHead is ENDW.head, the ceiling over the top gallery. G['head'] is already taken by the north wall's
# opening head, which is a different object 0.15 m higher, and confusing the two would be easy.
G['endHead'] = grab(r'head:([0-9.]+), soffitDepth:')
HEADFIT = (('east', 48.118, 11.093, 197, 0.024), ('west', 4.258, 11.082, 75, 0.013))
check('the head over the top gallery is drawn where both ends measure it',
      max(abs(G['endHead'] - h) for _s, _u, h, _n, _m in HEADFIT) <= 0.02,
      'drawn on %.3f. East gives %.3f from %d rays with a %.0f mm median and its near and far camera '
      'halves agreeing to 0.07 m; west gives %.3f from %d rays with %.0f mm. The two ends agree with each '
      'other to %.0f mm and both landed BELOW the 11.100 this file used to draw, which is why it moved.'
      % (G['endHead'], HEADFIT[0][2], HEADFIT[0][3], 1000 * HEADFIT[0][4], HEADFIT[1][2], HEADFIT[1][3],
         1000 * HEADFIT[1][4], 1000 * abs(HEADFIT[0][2] - HEADFIT[1][2])),
      'tools/soffit_back.py')
check('the head sits on the face it belongs to',
      max(abs(u - (48.056 if s == 'east' else 4.194)) for s, u, _h, _n, _m in HEADFIT) <= 0.10,
      'the fit returns a station as well as a height, and it puts the head on u %.3f east against a drawn '
      '48.056 and u %.3f west against a drawn 4.194, so 0.062 and 0.064 m out. A line that is really the '
      'soffit front edge has to sit on the balcony face, and it does.'
      % (HEADFIT[0][1], HEADFIT[1][1]),
      'tools/soffit_back.py')

# BOTH BALCONY FRONT TOPS, CONFIRMED BY A SECOND INSTRUMENT, tools/soffit_back.py (2026-09-09). The
# fronts were measured from the hall floor with a single fit and a range test. This is a different tool
# with a different ladder, a peel that takes lines strongest first instead of one winner per column, and
# its own control, and it recovers both of them: west h 9.790 from 354 rays with a 20 mm median against a
# measured 9.799, east h 9.870 from 345 rays with 28 mm against 9.865. Two instruments, four numbers,
# 9 mm and 5 mm apart.
FRONTAGAIN = (('west', 9.790, 9.799, 354), ('east', 9.870, 9.865, 345))
# AND A THIRD TEST ON TOP OF THAT: WINDOW INVARIANCE. A real edge is a step, and where a step is does not
# depend on how many samples are averaged either side of it. A gradual brightening is not a step, but a
# difference-of-means detector still reports a peak inside it and that peak MOVES with the window. Run at
# three windows the front tops hold; the line that was reported 0.2 m above them does not, so it is a
# gradient and was withdrawn rather than drawn. Parity names a feature, the split says one line explains
# it, the range says it lies beyond the plane, and this says it is an edge at all.
WINDOWS = {'west': (9.796, 9.814, 9.790), 'east': (9.874, 9.867, 9.870)}
check('the balcony front tops are the same height at every averaging window',
      max(max(v) - min(v) for v in WINDOWS.values()) <= 0.03,
      'across step windows of 15, 25 and 40 samples the west front reads %s and the east %s, spreads of '
      '%.0f mm and %.0f mm. The line once reported 0.2 m above them moved 44 mm between two of the same '
      'windows, which is how it was identified as a gradient rather than an edge.'
      % (', '.join('%.3f' % v for v in WINDOWS['west']),
         ', '.join('%.3f' % v for v in WINDOWS['east']),
         1000 * (max(WINDOWS['west']) - min(WINDOWS['west'])),
         1000 * (max(WINDOWS['east']) - min(WINDOWS['east']))),
      'tools/soffit_back.py')
# AND A THIRD, WHICH IS NOT A FIT AT ALL, tools/front_anchor.py (2026-09-09). Fix the station and each
# ray gives the height directly, then take the height the most rays agree on. Anchored on the station its
# own fit measured, the day walk gives 9.808 west against a shipped 9.799 and 9.868 east against 9.865.
# TWO MISTAKES ARE RECORDED IN THAT TOOL RATHER THAN TIDIED AWAY. It first took the MEDIAN of the
# anchored heights and came back 0.21 m low at both ends, because the ladder catches several edges and a
# median sits between them instead of on one; a line is found by consensus, not by averaging. And it then
# anchored both ends on the DRAWN face, which put the east 0.12 m low, because the shipped east height was
# derived at u 48.397 and along the median ray 0.34 m of station is worth 0.12 m of height.
# THE POINT OF ANCHORING IS THAT IT LETS THE NIGHT WALK IN. A stone edge reads the same under any light; a
# boundary that is really where the light stops does not, and after dark this hall is lit from below and
# the sides rather than through the stained glass. The night set is only 92 usable rays against the day's
# 600 and spans 15 m of hall against 37, so it can never carry a free two-unknown fit. Anchored, it can.
FRONT3 = (('west', 9.808, 9.799, None), ('east', 9.868, 9.865, 9.834))
check('a third estimator, anchored rather than fitted, gives the same balcony fronts',
      max(abs(a - b) for _s, a, b, _n in FRONT3) <= 0.02,
      'the consensus height at a fixed station gives %.3f west against a shipped %.3f and %.3f east '
      'against %.3f: %.0f mm and %.0f mm. That is a third method on these two numbers, after the single '
      'fit with its range test and the peel.'
      % (FRONT3[0][1], FRONT3[0][2], FRONT3[1][1], FRONT3[1][2],
         1000 * abs(FRONT3[0][1] - FRONT3[0][2]), 1000 * abs(FRONT3[1][1] - FRONT3[1][2])),
      'tools/front_anchor.py')
check('the east balcony front reads the same by day and by night',
      abs(FRONT3[1][1] - FRONT3[1][3]) <= 0.06,
      'the day walk anchors it on %.3f and the night walk on %.3f, %.0f mm apart, from lighting states '
      'that share nothing: daylight through the stained glass overhead against uplights and wall washers '
      'after dark. An edge that survives that is stone, not a boundary the lights drew. The west end '
      'cannot take this test, its night frames yielding 2 detections.'
      % (FRONT3[1][1], FRONT3[1][3], 1000 * abs(FRONT3[1][1] - FRONT3[1][3])),
      'tools/front_anchor.py')

check('the balcony front tops survive a second instrument',
      max(abs(a - b) for _s, a, b, _n in FRONTAGAIN) <= 0.02,
      'the peel gives west %.3f against the single fit on %.3f and east %.3f against %.3f, so %.0f mm '
      'and %.0f mm apart on %d and %d rays. Neither tool was tuned to agree with the other.'
      % (FRONTAGAIN[0][1], FRONTAGAIN[0][2], FRONTAGAIN[1][1], FRONTAGAIN[1][2],
         1000 * abs(FRONTAGAIN[0][1] - FRONTAGAIN[0][2]),
         1000 * abs(FRONTAGAIN[1][1] - FRONTAGAIN[1][2]), FRONTAGAIN[0][3], FRONTAGAIN[1][3]),
      'tools/soffit_back.py')

# --- the long walls -----------------------------------------------------------------------------
# THE TWO PARAPET TOPS AGAINST THE LIGHT THAT GOT OVER THEM, at matched lens setback so the ends are the
# same experiment. Only lenses at least 0.6 m behind the face are used: a lens almost on the coping cannot
# send a ray across the face plane low enough to test anything, and the first east run was 140 b3 frames
# standing 0.2 m from the stone, which is why its 1.62 % was never comparable with the west's 24.30 %.
# AND THE TOLERANCE IS SET BY A STATED RULE, not by whichever number makes the suite green. The bar is
# 1.5 times the LARGER of two measured quantities: the method's systematic, which is its overshoot at the
# EAST end where the face is settled, and the clip's own near-field self-consistency.
#   the east overshoot is 0.032 m with the frozen focal and 0.072 m with it scaled by 0.965
#   b7s, the only clip standing on either deck a metre back from the face, misses itself by 0.173 m with
#   the frozen focal and 0.091 m at the focal that suits it best (tools/focal_probe.py)
# So the bar is 1.5 x 0.091 = 0.137 m. Last night this file used b7s's 0.173 m and let the west pass. That
# was too cautious: the 0.173 is inflated by a lens the registration never refined for that clip, and the
# west overshoot of 0.202 m survives the whole focal sweep, moving to 0.242 m rather than away.
POSE_MISS = 0.091
# The 5th percentile crossing height against the assumed face station, both ends at the matched 0.6 m
# setback, tools/gallery_arrival.py. These are the curves, not a single number, which is the whole point.
CAP = {
    'west': ((3.394, 9.544), (3.594, 9.370), (3.794, 9.189), (3.994, 9.002), (4.194, 8.818),
             (4.394, 8.632), (4.594, 8.446), (4.794, 8.261), (4.994, 8.073), (5.194, 7.886)),
    'east': ((47.056, 8.541), (47.256, 8.650), (47.456, 8.762), (47.656, 8.872), (47.856, 8.975),
             (48.056, 9.078), (48.256, 9.183), (48.456, 9.289), (48.656, 9.401), (48.856, 9.502)),
}
# where the upstand-top line fit puts each end: face station, height, inliers, median residual
# superseded as a STATION by tools/end_face_scan.py, which measures the plane one unknown at a
# time and checks itself against a null split. Kept here as the free two-unknown fit it was.
TOPFIT = {'west': (3.760, 9.082, 3545, 0.017), 'east': (48.005, 9.067, 3973, 0.011)}
# station, height, near-far spread at the minimum, worst near-far on the sweep, worst null
SCAN = {('west', 'solid'): (3.710, 9.097, 0.005, 0.063, 0.004),
        ('west', 'rail'): (4.210, 9.796, 0.001, 0.021, 0.014),
        ('east', 'solid'): (48.055, 9.095, 0.005, 0.175, 0.038),
        ('east', 'rail'): (48.047, 9.798, 0.001, 0.049, 0.004)}


def cap_at(side, uf):
    xs = [p[0] for p in CAP[side]]
    ys = [p[1] for p in CAP[side]]
    if uf <= xs[0]:
        return ys[0]
    if uf >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= uf <= xs[i + 1]:
            t = (uf - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


DRAWNFACE = {'west': 4.194, 'east': 48.056}
# THE OPENING HEAD LEAN, ANSWERED (2026-09-09, tools/head_lean.py).
LEAN = {'head': 0.079, 'sill': 0.052, 'corr': 0.96, 'tall5': 0.038, 'tall4': 0.017,
        'mean5': 2.436, 'mean4': 2.430, 'tilt': 0.0028, 'worst': 3}
check('the opening head lean is common to the sill, so it is the instrument and not the openings',
      LEAN['tall5'] < 0.5 * LEAN['head'],
      'the five openings with rays on both edges give heads spreading %.0f mm and sills spreading %.0f, '
      'correlating %+.2f. Their DIFFERENCE, which cancels anything that moves both, spreads only %.0f mm. '
      'Opening %d carries most of it, standing 73 mm high on its head and 38 mm high on its sill, high on '
      'both, which is the common-mode signature. A real difference in how the openings were built would '
      'show in the head and not in the sill.'
      % (1000 * LEAN['head'], 1000 * LEAN['sill'], LEAN['corr'], 1000 * LEAN['tall5'], LEAN['worst']),
      'tools/head_lean.py')
check('the openings are drawn the height they were measured',
      abs((G['head'] - G['sill']) - LEAN['mean4']) <= 0.02,
      'the model draws %.3f m from its own measured sill and head. The invariant measures %.3f across the '
      'four openings that agree with each other, spread %.0f mm, and %.3f across all five, spread %.0f. '
      'So the drawing is %.0f mm out on the tight set, inside the 14 mm those two heights already carry.'
      % (G['head'] - G['sill'], LEAN['mean4'], 1000 * LEAN['tall4'], LEAN['mean5'],
         1000 * LEAN['tall5'], 1000 * abs((G['head'] - G['sill']) - LEAN['mean4'])),
      'tools/head_lean.py')
check('the twelve heads belong on one level, and are drawn on one',
      LEAN['tilt'] < 0.005,
      'a straight line through the heads that answer tilts %.1f mm per metre of hall and none of them '
      'sits more than 20 mm off it. That is one tilt across 30 m, well under what the pose self-check '
      'allows, so there is no case for drawing the heads at different heights and none is made.'
      % (1000 * LEAN['tilt']),
      'tools/head_lean.py')
# THE LOWER TIER, fitted for the first time (2026-09-09, tools/run_low_band.py, tools/low_gap.py).
LOWGAP = {'gap': 0.310, 'spread': 0.022, 'span': 1.60, 'hmove': 0.298, 'solid': 341, 'rail': 91,
          'westsolid': 0, 'westrail': 5, 'ratio_solid': 1.7, 'ratio_rail': 1.6}
check('the lower rail is drawn on the one lower-tier quantity that is measured',
      abs((G['lowRail'] - G['lowUp']) - LOWGAP['gap']) <= 0.02,
      'neither lower-tier height is a number: both fits fail the near-far test, their gap falling '
      'monotonically to a minimum on the EDGE of the sweep with worst-to-best ratios of %.1f and %.1f '
      'where the top tier gave 12 to 70. But both loci carry almost the same slope, so a drift common to '
      'them cancels out of their DIFFERENCE: across %.2f m of assumed station the two heights move %.3f m '
      'while the gap moves %.3f. The rail stands %.3f m over the solid, drawn %.3f, and the %.2f upstand '
      'it is measured from does not move because nothing here measured it.'
      % (LOWGAP['ratio_solid'], LOWGAP['ratio_rail'], LOWGAP['span'], LOWGAP['hmove'],
         LOWGAP['spread'], LOWGAP['gap'], G['lowRail'] - G['lowUp'], G['lowUp']),
      'tools/low_gap.py')
check('the lower tier was found by two detectors that cannot find each other edge',
      LOWGAP['solid'] >= 100 and LOWGAP['rail'] >= 50,
      'the solid top came from %d rays on the shade polarity and the rail top from %d on the lit '
      'polarity. A detector told to find a dark-below-light edge cannot return a light-below-dark one, so '
      'the gap between them is two independent findings and not one detector reporting its own window '
      'twice.' % (LOWGAP['solid'], LOWGAP['rail']),
      'tools/run_low_band.py')
check('the west lower tier is refused rather than guessed',
      LOWGAP['westsolid'] + LOWGAP['westrail'] < 40,
      'pointed a metre and a half below the band it measured at the top, the same instrument returns %d '
      'detections above the contrast bar for the west lower solid and %d for the west lower rail. There '
      'is nothing down there to fit, so the lower tier has no cross-check and everything drawn on it '
      'comes from one end.' % (LOWGAP['westsolid'], LOWGAP['westrail']),
      'tools/run_low_band.py')
check('the east end is the control for the station scan, and it passed',
      abs(SCAN[('east', 'solid')][0] - DRAWNFACE['east']) <= 0.02
      and abs(SCAN[('east', 'rail')][0] - DRAWNFACE['east']) <= 0.02,
      'the one-unknown station scan was run on both ends without being told where the answer should be. '
      'At the east it puts the solid upstand top on u %.3f and the rail top on %.3f, %.0f mm apart, from '
      'separate ray sets and separate ladders, against a face the model draws on %.3f. An instrument that '
      'lands on an independently drawn plane to a millimetre at the end it was not aimed at is entitled to '
      'be believed at the end it was.'
      % (SCAN[('east', 'solid')][0], SCAN[('east', 'rail')][0],
         1000 * abs(SCAN[('east', 'solid')][0] - SCAN[('east', 'rail')][0]), DRAWNFACE['east']),
      'tools/end_face_scan.py')
for side, feat in (('west', 'solid'), ('east', 'solid'), ('east', 'rail')):
    st, ht, mn, mx, nl = SCAN[(side, feat)]
    check('the %s %s station beats its own null split' % (side, feat),
          mx > 3.0 * nl,
          'near and far cameras agree to %.0f mm on u %.3f and disagree by %.0f mm at the far end of the '
          'sweep. The null split, odd rays against even, never exceeds %.0f mm over the same sweep, so the '
          'V is a fact about the building and not about the tracker recentring. Ratio %.1f against a bar '
          'of 3.' % (1000 * mn, st, 1000 * mx, 1000 * nl, mx / nl),
          'tools/end_face_scan.py')
check('the west rail station is measured but NOT shipped, because it failed its null',
      True,
      'its minimum sits on u %.3f beside a drawn %.3f, which is agreement, but its near-far spread only '
      'reaches %.0f mm against a null of %.0f, a ratio of %.1f under the bar of 3. A number a null could '
      'have produced is not a measurement, so the west rail stays where it was drawn and this is recorded '
      'as the reason rather than as a result.'
      % (SCAN[('west', 'rail')][0], DRAWNFACE['west'], 1000 * SCAN[('west', 'rail')][3],
         1000 * SCAN[('west', 'rail')][4], SCAN[('west', 'rail')][3] / SCAN[('west', 'rail')][4]),
      'tools/end_face_scan.py')
FACEU = {'west': G['endWest'] + G['endFace'], 'east': 51.906 - G['endFace']}
for side, sk in (('west', 'setWest'), ('east', 'setEast')):
    drawn_solid = FACEU[side] - (1 if side == 'west' else -1) * G[sk]
    check('the %s solid upstand is drawn on the station that was measured' % side,
          abs(drawn_solid - SCAN[(side, 'solid')][0]) <= 0.02,
          'the model now stands it on u %.3f, face %.3f set back %.3f, against a measured %.3f.'
          % (drawn_solid, FACEU[side], G[sk], SCAN[(side, 'solid')][0]),
          'tools/end_face_scan.py')
check('a solid parapet is not drawn where the light got past it',
      cap_at('west', SCAN[('west', 'solid')][0]) >= SCAN[('west', 'solid')][1] - 1.5 * POSE_MISS,
      'the arrival cap is a curve in the assumed station, and on the west face it reads %.3f while the '
      'locus there is %.3f, so a solid on the drawn face stands %.3f m into light that reached a camera '
      'on the deck. Moved back to the measured %.3f the cap reads %.3f and the top %.3f, clear by %.3f. '
      'The cap and the near-far V are different instruments that share no assumption, and they agree the '
      'west solid is not on its face.'
      % (cap_at('west', DRAWNFACE['west']), 8.955, 8.955 - cap_at('west', DRAWNFACE['west']),
         SCAN[('west', 'solid')][0], cap_at('west', SCAN[('west', 'solid')][0]),
         SCAN[('west', 'solid')][1],
         cap_at('west', SCAN[('west', 'solid')][0]) - SCAN[('west', 'solid')][1]),
      'tools/end_face_scan.py + tools/gallery_arrival.py')
check('read at their own measured stations the two ends agree on the solid parapet height',
      abs(SCAN[('west', 'solid')][1] - SCAN[('east', 'solid')][1]) <= 0.02,
      'west %.3f and east %.3f, %.0f mm apart, where the free fits left %.0f mm. The model draws %.3f and '
      '%.3f over a deck of %.3f.'
      % (SCAN[('west', 'solid')][1], SCAN[('east', 'solid')][1],
         1000 * abs(SCAN[('west', 'solid')][1] - SCAN[('east', 'solid')][1]),
         1000 * abs(TOPFIT['west'][1] - TOPFIT['east'][1]), G['upWest'], G['upEast'], G['deck']),
      'tools/end_face_scan.py')
for side, upk in (('west', 'upWest'), ('east', 'upEast')):
    check('the %s upstand height is drawn on its own measured station value' % side,
          abs((G['deck'] + G[upk]) - SCAN[(side, 'solid')][1]) <= 0.01,
          'drawn %.3f against a measured %.3f.' % (G['deck'] + G[upk], SCAN[(side, 'solid')][1]),
          'tools/end_face_scan.py')
for side, upk, npts in (('east', 'upEast', 1941), ('west', 'upWest', 3371)):
    uf, htop, ninl, med = TOPFIT[side]
    cap = cap_at(side, uf)
    over = htop - cap
    drawn_top = G['deck'] + G[upk]
    check('the %s parapet top clears the light that got over it, on the same face' % side,
          over <= 1.5 * POSE_MISS,
          'the upstand-top line fit puts this end on face u %.3f and height %.3f, from %d inliers with a '
          '%.0f mm median. The %d arrivals that reached a camera on that deck from inside the building '
          'give a 5th percentile of %.3f on that same face, so the top stands %+.3f m into light that '
          'arrived, against a bar of %.3f m. The model draws the top on %.3f, deck %.3f plus an upstand '
          'of %.3f. The old form of this check read the cap on the DRAWN face instead of the measured '
          'one, which is how the west came to fail it by 0.202 m: that cap moves 0.19 m for every 0.20 m '
          'the face moves, so the face choice decided the verdict.'
          % (uf, htop, ninl, 1000 * med, npts, cap, over, 1.5 * POSE_MISS, drawn_top, G['deck'],
             G[upk]),
          'tools/west_far.py + tools/gallery_arrival.py')
check('the two ends agree on how tall the solid upstand is',
      abs((TOPFIT['west'][1] - G['deck']) - (TOPFIT['east'][1] - G['deck'])) <= 0.10,
      'fitted separately from cameras 37 m apart with opposite views, the two ends give upstands of '
      '%.3f and %.3f m above the deck, %.0f mm apart. The model draws %.3f west and %.3f east.'
      % (TOPFIT['west'][1] - G['deck'], TOPFIT['east'][1] - G['deck'],
         1000 * abs(TOPFIT['west'][1] - TOPFIT['east'][1]), G['upWest'], G['upEast']),
      'tools/west_far.py')
for side, upk in (('west', 'upWest'), ('east', 'upEast')):
    # SUPERSEDED, and the failure is the point. This compared the drawn height against the FREE fit, whose
    # height was read at a station the station scan has since shown to be wrong by 50 mm at both ends. Read
    # at the measured station the same rays give 9.097 and 9.095, and the model was moved onto those, so
    # the old form now fails by 15 and 28 mm. The bar is widened to the height the station shift is worth,
    # and the tight check lives in the scan bound above.
    check('the %s upstand height agrees with the older free fit within the station shift' % side,
          abs((G['deck'] + G[upk]) - TOPFIT[side][1]) <= 0.04,
          'drawn top %.3f against the free fit %.3f, %+.3f m out. The free fit read its height on u %.3f '
          'and the scan reads the same rays on %.3f, and the locus carries about 0.25 m of height per '
          'metre of station, so a shift of that size is expected and is not a disagreement.'
          % (G['deck'] + G[upk], TOPFIT[side][1], (G['deck'] + G[upk]) - TOPFIT[side][1],
             TOPFIT[side][0], SCAN[(side, 'solid')][0]),
          'tools/west_far.py superseded by tools/end_face_scan.py')
# THE EDGE BOTH ENDS SEE, NOW WITH A RANGE, so it is a bound after all (tools/far_edge_range.py).
# It was withdrawn this evening because a crossing height is an occlusion bound only if the feature lies
# BEYOND the face plane, and the detector never tested that. The fit already contained the answer: an edge
# spanning the hall is a line (u*, h*) and fitting it localises the feature in 3D rather than only in
# height. Two errors were fixed to get there. The residual was not in metres, it was the perpendicular
# distance times sqrt(vu^2 + vh^2), so an 80 mm threshold meant something different for every ray. And one
# fit over everything cannot be checked, so the cameras are split by distance into two independent
# experiments on the same edge.
#   west  366 inliers within 50 mm, median 10 mm, edge on u 4.160 h 9.799
#         near half (4.154, 9.802) against far half (4.258, 9.773): 0.10 m apart in u, 0.03 m in h
#   east  660 inliers within 50 mm, median 15 mm, edge on u 48.397 h 9.865
#         near half (48.474, 9.889) against far half (48.169, 9.816): 0.31 m and 0.07 m
#   and 100 per cent of the inliers at BOTH ends put the edge beyond the face plane, by 0.03 m west and
#   0.35 m east along the ray. The sightline crossed the plane before it arrived, so nothing solid stood
#   above the edge at that station. That is the missing half, and the bound stands on it.
# AND THE SIM NOW DRAWS THAT EDGE RATHER THAN STOPPING 0.40 m UNDER IT. The identity question that kept
# it out of the model is answered by the detector's parity: a bright-below dark-above step is the top of
# the LIT FRONT, and the top of the dark recess above it has the opposite parity and was never eligible.
# tools/front_open.py supplies the rest: all 39 lenses set back from the two faces stand BELOW their own
# measured top edge and every one of them photographs hall floor, so the front is OPEN up there, which is
# how the deck arrivals can cap a solid on 8.818 at the same time without contradiction.
for side, key, uface, edge in (('west', 'railWest', 4.194, 9.799), ('east', 'railEast', 48.056, 9.865)):
    drawn = G['deck'] + G[key]
    check('the %s balcony front is drawn where the hall floor measures it' % side,
          abs(drawn - edge) <= 0.005,
          'front drawn on %.3f, the deck %.3f plus %.3f. The measured edge crosses u %.3f on h %.3f, so '
          'this is %+.3f m out. It was 0.40 m out until this evening.'
          % (drawn, G['deck'], G[key], uface, edge, drawn - edge),
          'tools/far_edge_range.py')
check('the south tapestries hang in front of the south wall',
      all(d < G['dSouth'] for d in southtap),
      'wall face d %.3f; tapestries on %s. Measured surface 15.262.'
      % (G['dSouth'], ', '.join('%.3f' % d for d in southtap)),
      'tools/wall_planes.py')
check('the south tapestries sit on their measured plane',
      all(abs(d - 15.262) < 0.002 for d in southtap),
      'measured 15.257 and 15.267 in the two bays from 1,737 and 28,470 points; drawn %s'
      % ', '.join('%.3f' % d for d in southtap),
      'tools/wall_planes.py')
# THE PARAPETS WERE NEVER IN THIS AUDIT, and the gap was found by a test that refused (2026-09-09,
# tools/west_recess.py, tools/occupancy_audit.py). The occupancy test went looking for a lens inside the
# west parapet to confirm by occupancy what two photometric instruments had already found about the
# recess. It came back empty and settled nothing. But writing it made the gap plain: the audit checked
# the walls, the end walls, the floor, the gallery slabs and the corridor, and never the parapets. The
# west solid moved 0.484 m this evening and nothing would have noticed if it had been drawn through a
# camera. The parapets are in it now, each end tested on the plane its solid actually stands on.
# AND THE PROSE THAT USED TO SIT HERE WAS STALE. It claimed 1,565 cameras across 14 classes and a worst
# excursion of 2 mm. The audit now reads 1,568 across 15 and finds three real contradictions, all of them
# b6s frames that this archive already knows are posed outside the building.
OCC = {'cams': 1568, 'classes': 15, 'contradictions': 3, 'badclass': 'b6s', 'parapet_hits': 0}
check('nobody stood inside a solid, and the parapets are finally among the solids',
      OCC['parapet_hits'] == 0,
      '%d posed cameras across %d classes. %d cameras beat the 0.200 m allowance and every one of them is '
      'a %s frame: two put 8 m through the south wall and one puts 11 m through the east end wall, which '
      'is the registration already recorded as posing that clip outside the hall, and nothing in this '
      'model rests on it. NO camera is inside either gallery parapet, which is a check that did not exist '
      'until this evening.'
      % (OCC['cams'], OCC['classes'], OCC['contradictions'], OCC['badclass']),
      'tools/occupancy_audit.py')
check('the occupancy test that refused is kept as a refusal',
      True,
      'looking for a lens inside the volume the west parapet used to occupy found none, and none in the '
      'east control either, so occupancy can neither confirm nor deny the recess. No camera in this '
      'archive stood that close to either parapet at that height. The recess still rests on the near-far '
      'station scan and the arrival cap, which is two instruments and not three, and this is written down '
      'so that it is not later remembered as a third.',
      'tools/west_recess.py')

print('MEASURED BOUNDS ON THE BALCONIES, THE WALLS AND THE ROOM BEHIND THE BRICK WALL')
print('')
for ok, name, detail, source in notes:
    print('%s  %s' % ('PASS' if ok else 'FAIL', name))
    print('        %s' % detail)
    print('        %s' % source)
print('')
print('STILL UNMEASURED, and not tested here because nothing in the archive can test them:')
for line in ('the corridor floor 8.34, its back wall d -2.09 and its ceiling 11.4. A POINT IN THERE CAN'
             ' BE TESTED WHERE A LINE CANNOT, and that is the one crack in this room: a line is separated'
             ' only by cameras at different distances, which the slot collapses, while a point is'
             ' separated by the angular spread of the rays that see it. Lamp 8 gives 6 mm of half-to-half'
             ' agreement on d -2.368 against 242 mm at the end of its sweep, a ratio of 5.6, the sharpest'
             ' signal anything has produced inside that corridor. Lamp 9 gives a softer minimum on -1.849'
             ' and lamp 11 refuses on a leverage of 1.54, so the lamp plane is BRACKETED between -1.85 and'
             ' -2.37 rather than pinned, and the drawn wall sits inside that bracket, tools/lamp_v.py.'
             ' Every ray voting for any of the three comes from a camera between u 31.3 and 35.3, so the'
             ' two-sided parallax a point deserves does not exist anywhere in this archive.'
             ' AND THERE IS NOW A'
             ' NUMBER FOR WHY, statable before any fitting happens. The near-far test that measured the'
             ' north wall and the end walls has power in proportion to the RATIO of its two halves'
             ' distances, and the corridor rays give 1.32 where the north wall gives 2.54 and the end'
             ' walls give 42 over 5. Every camera that can see into that room stands 12.6 to 16.7 m off'
             ' it because the opening collimates them, so the two halves are the same instrument twice.'
             ' Run anyway it scores 2.5 against a bar of 3 and its best plane sits on the EDGE of the'
             ' sweep, which is the halves converging as the plane nears the cameras and not the feature'
             ' being found, tools/depth_v.py. Two counted reasons'
             ' stand behind that. FROM THE HALL FLOOR the opening collimates: seeing the whole ladder'
             ' through a 1.2 m slot forces the lens far back and the usable set collapses from an 8.64 m'
             ' baseline to 1.59 m, tools/corridor_lines.py. FROM INSIDE THE OPENINGS there is no imagery'
             ' at all: 317 posed lenses stand in north apertures and not one points into the room, the'
             ' most inward-facing still 0.38 of the way toward the hall, tools/opening_facing.py',
             'BUT THERE IS A REAL FEATURE IN THERE, found by anchoring instead of fitting'
             ' (tools/corridor_locus.py). A baseline is what a TWO-unknown fit needs; fix the depth and'
             ' each ray gives the height on its own with nothing to slide along. Done that way the 215'
             ' rays through the openings agree sharply: at the drawn back wall the west and east halves'
             ' both give h 10.803 and the nearer and further halves 10.801 and 10.805, four millimetres'
             ' across all four. That is the first real signal anything has ever got from that room',
             'AND IT CONTRADICTS THE DRAWN ROOM, conditionally. The rays cannot fix the DEPTH: the count'
             ' is flat across the whole sweep, so what they give is a locus, h = 10.806 - 0.565*(d +'
             ' 2.090). On the drawn back wall that puts the feature on 10.806, which is 0.184 m BELOW'
             ' the highest lamp triangulated inside the room. A ceiling cannot be under a lamp. So IF'
             ' this feature is the ceiling meeting the back wall, that wall is at least 2.42 m behind'
             ' the face rather than the drawn 2.09. Nothing is moved on it, because the feature has not'
             ' been identified: a boundary where the lamps stop lighting the back wall would sit in the'
             ' same place, and the day-against-night test that could tell them apart has no night'
             ' imagery of that room to run on',
             'the north tapestries d -0.053: 547 points near that wall, no sheet',
             'RESOLVED, and the first answer was wrong. The count-based scan called the north wall depth'
             ' unmeasurable because the inlier count stayed flat over a 270 mm band. A count is a blunt'
             ' conditioning test: a wrong plane moves every ray the same way before it spreads them, so'
             ' the consensus peak follows the error and keeps its rays. The near-far split with its own'
             ' null finds a real minimum, and BOTH edges land on the same plane d -0.030, the sill with'
             ' 1 mm of half-to-half agreement against 26 mm by the end of its sweep on a null of 3, the'
             ' head with 2 mm against 55 on a null of 15. The face moved 0.060 m into the hall, the sill'
             ' and head came down with it, and the corridor width absorbed the move so its back wall'
             ' stays where the lamps put it. The jamb feature is now 0.177 m behind the face rather than'
             ' 0.117, which is the face moving and not the jambs, tools/depth_v.py',
             'AUDITED, and it held: the only geometry in this model moved on a fit the near-far split had'
             ' never seen was the 0.147 m shift applied to five north openings. Five of the eight testable'
             ' jambs carry a real depth minimum, but the eight minima scatter from -0.050 to -0.213, so the'
             ' jamb DEPTH is far softer than the 13 mm the free fits agreed to. That does not reach the'
             ' openings, because they were drawn from the AGREEMENT of nine stations with twelve pairs of'
             ' edges and a drift common to all nine cancels out of an agreement. Sweeping the depth across'
             ' 0.18 m moves the mean residual only from -21 to +27 mm, a 48 mm range against a 147 mm'
             ' shift. The per-opening accuracy is now stated rather than assumed: 5 mm in the mean, about'
             ' 55 mm for any single edge, tools/jamb_v.py',
             'STILL OPEN in physics but CLOSED in consequence: what the jamb detector finds 0.117 m back.'
             ' The day-against-night test that settled the balcony front cannot run here: the 22 night'
             ' frames on that band of wall yield ZERO usable columns, even with a 3 grey level bar and an'
             ' 8 sample window, so there is no second lighting state to compare. But it does not matter'
             ' for anything this model draws. A rebate back edge and a shadow on the reveal return BOTH'
             ' lie in the jamb plane, and that is a plane of constant u, so both give the same station.'
             ' The openings were moved on the station and the station is invariant to the answer',
             'ANSWERED, and it was never a lean: the head and the sill of the same openings correlate'
             ' +0.96, and their DIFFERENCE spreads 38 mm where the head alone spreads 79. Whatever'
             ' moves the heads moves the sills with it, which is one instrument leaning and not twelve'
             ' openings built at different heights. Opening 3 carries most of it, high on both edges.'
             ' The openings are 2.43 m tall and the model draws 2.425, tools/head_lean.py',
             'ANSWERED: which of the west numbers was wrong. It was the FACE. A top 0.20 m lower, a deck'
             ' 0.20 m lower and a face 0.20 m over all fitted the same rays, and the upstand-top line fit'
             ' separates them because a line carries both at once: face u 3.760, height 9.082. The cap'
             ' read on THAT face is 9.220, so nothing was ever over it, tools/west_far.py',
             'b6g and b6gp are the worst poses in the archive: median near-field ray miss 0.179 and 0.200 m'
             ' with 0.6 and 0.3 per cent of matches inside 15 mm. Nothing should rest on those six frames,'
             ' tools/pose_selfcheck.py',
             'ENDW soffitDepth 2.1, and the refusal is now sharper than nothing has seen it. The peel ran'
             ' to five lines in the right band at each end and every one sits within 0.9 m of the face;'
             ' none lands near the drawn back edge on u 2.094 west or 50.156 east, which the ray fan does'
             ' reach. The cause is photometric: from the far half of the hall the soffit is seen twelve'
             ' degrees off edge-on, so 2.1 m of it subtends about 0.44 m of apparent height across forty'
             ' metres, and its junction with the back wall is the darkest part of the darkest surface in'
             ' the bay, tools/soffit_back.py',
             'the b6 gallery frames: the new b6s registration poses frames 396 to 1260 OUTSIDE the hall'
             ' (u 62.9, d 23.7), while b6g poses frames 1002 to 1020 of the same clip on the east deck on'
             ' 7 to 9 inliers. Two models, one clip, 20 m apart. Nothing rests on either, tools/balcony_walk.py',
             'the parapet TOP is bracketed 9.110 to 9.363 and the face is only bounded from the west, so'
             ' the coping depth itself has never been measured',
             'WHAT the far edge at h 9.55-9.59 actually is. It is 1.21 to 1.25 m above the drawn deck at'
             ' both ends, which fits a balustrade top and would also fit the top of the dark recess behind'
             ' one. The face station it implies carries about 0.5 m of slop (RANSAC and least squares'
             ' disagree by 0.37 m west and 0.58 m east), so it cannot confirm a face, tools/west_far.py',
             'ANSWERED: a low solid upstand with an open rail above it was the shape that satisfied both'
             ' west instruments, and it is now drawn AND measured rather than proposed. The upstand top'
             ' is a line of its own, dark below and lit above, and it fits on 0.742 m west and 0.727 m'
             ' east of the deck, the two ends agreeing to 15 mm, tools/west_far.py',
             'ANSWERED, and it was a shape and not a slide: the west solid upstand really does stand'
             ' behind the west rail. Fixing the station and splitting the rays by camera distance gives'
             ' a sharp minimum on u 3.710 for the solid, 5 mm of near-far agreement there against 63 mm'
             ' at the far end of the sweep, on a null split that never exceeds 4 mm. The arrival cap,'
             ' which shares no assumption with it, independently forbids a solid past u 4.010. The solid'
             ' moved back 0.484 m and the face is glazed to the deck. THE EAST IS THE CONTROL AND IT'
             ' PASSED: its two edges land on u 48.055 and 48.047 against a face drawn on 48.056, so the'
             ' instrument was not aimed at its answer. The WEST RAIL station is withheld, because it'
             ' fails its own null: 21 mm of near-far against 14 mm of null, tools/end_face_scan.py',
             'and whether the front the hall floor measures is glass, balusters or a solid with a deep'
             ' recess behind it. All three pass light the same way from where the cameras stood',
             'WITHDRAWN within the hour: the third line reported 0.2 m above each front top is a GRADIENT'
             ' and not an edge. It looked convincing, 384 rays west with the camera halves agreeing to'
             ' 6 mm, and it passed the spread-across-the-hall test. What killed it is window invariance:'
             ' run at step windows of 25 and 40 samples it reads 10.053 and 10.009, moving 44 mm on a'
             ' feature claimed to 6 mm, while the front tops beneath it hold to 24 mm and 7 mm across'
             ' three windows. A difference-of-means detector reports a peak inside any smooth brightening'
             ' and that peak walks with the window. Nothing was moved on it,'
             ' tools/soffit_back.py',
             'STILL OPEN and smaller: a window-invariant line does sit on the WEST face on h 9.9025, from'
             ' two windows agreeing to 1 mm, about 0.104 m above that front top. The east has no'
             ' counterpart that survives the same test, so one end is not a building feature yet'):
    print('   ' + line)
print('')
if fails:
    print('%d BOUND(S) VIOLATED: %s' % (len(fails), '; '.join(fails)))
    sys.exit(1)
print('%d bounds, all satisfied. The sim contradicts nothing the imagery can prove, which is a weaker' % len(notes))
print('statement than "correct" and is the strongest one this archive supports.')
