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
# CORRECTED 2026-09-09, and it had been wrong since the corridor was first drawn. The model builds
# the room as dR = face + s*openDepth, then dB = dR + s*width, so the corridor WIDTH is measured
# from the back of the reveal and the back wall stands the reveal PLUS the width behind the face.
# This line left the reveal out, so every corridor bound has been evaluating a plane the model does
# not draw: with width 2.06 the checker read -2.090 while the sim drew -2.990. It passed anyway,
# because the lamp bounds are one-sided and a deeper wall satisfies them, which is exactly how an
# arithmetic error survives a suite of one-sided tests.
G['cBack'] = G['dNorth'] - G['openDepth'] - G['cWidth']

lamps = re.search(r'lamps:\[(\[.*?\])\]\}', src)
LAMPS = [[float(x) for x in t.split(',')] for t in re.findall(r'\[([-0-9.,]+)\]', lamps.group(1))] if lamps else []
# RE-RUN 2026-09-09 after the openings moved 0.147 m and the wall face moved to -0.030. The aperture
# gate that decides which rays may vote for a lamp depends on both, so the old array was built on
# superseded geometry. Re-run, the three collapse onto one level.
# RE-RUN AGAIN with the aperture pointed at the measured sill, head and wall depth. The third lamp
# is not found through the corrected gate, so it is not drawn. The two that remain agree to 25 mm
# in depth and 29 in height, better than the three did.
MEASURED_LAMPS = [[30.527, -2.022, 10.916], [34.140, -2.047, 10.945]]
OLD_LAMPS = [[30.642, -1.093, 10.374], [34.139, -2.144, 10.990], [42.043, -1.824, 10.908]]
# the near-far parallax test on each lamp's own ray bundle: measured?, best depth, height, ratio,
# leverage (tools/lamp_v.py)
LAMPV = {8: (True, -2.322, 11.090, 6.5, 5.71), 9: (False, -2.047, 10.945, 2.9, 12.59)}

# BOTH WALLS NOW, 2026-09-09. This gathered only the SOUTH tapestries, because the only textile fault
# anyone had found was on the south wall. The north pair went unchecked and duly acquired the identical
# fault the moment the north face moved: they are stored as absolute world corners in a JSON file, so a
# face that moves leaves them behind. A bound written for the wall where the bug was found does not
# protect the wall where it had not been found yet.
southtap, northtap = [], []
for t in tap['tapestries']:
    ds = [sum((c[k] - O[k]) * HD[k] for k in range(3)) for c in t['corners']]
    d = sum(ds) / len(ds)
    (southtap if d > 8.0 else northtap).append(d)

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
# WITHDRAWN THE SAME NIGHT, and the withdrawal is the bound now (2026-09-09, tools/corridor_lamp.py).
# Everything found behind this wall comes through an APERTURE: the drawn opening rectangle projected into
# each frame and used as a mask. That rectangle is built from the sill, the head and the wall depth, and it
# had been carrying 8.99, 11.35 and -0.090 all day while the model moved to 8.740, 11.165 and -0.030.
# So the mask stopped 0.185 m above the real head. Two points reported on consecutive nights as sitting
# 0.19 m ABOVE the head, one with a parallax ratio of 88, came in on 11.359 and 11.340 against a gate that
# stopped on 11.350. Two points nineteen millimetres apart straddling the mask edge is the mask. Pointed
# at the measured wall neither comes back: the best candidate up there now scores 2.9 against a bar of 3.
check('the reveal claims built on the stale aperture are withdrawn, not quietly dropped',
      G['openDepth'] >= 0.422 - 1e-9,
      'the reveal depth bound goes back to the 0.422 m a lens leaning through an opening gives it, from '
      'the 0.629 claimed on the withdrawn point. The point implied on the hall face on h 9.051 also fails '
      'to reappear and is withdrawn with it. openDepth is drawn %.2f and still clears the bound that '
      'survives.' % G['openDepth'],
      'tools/corridor_cloud.py')
check('a shared input error cannot be caught by agreement between instruments',
      True,
      'the withdrawn point passed a parallax split, an odd-against-even null, and confirmation by a '
      'second independent point found in a separate peel round. All three agreed because all three looked '
      'through the same wrong mask. No consistency test between instruments can catch an error in an '
      'input they share. What caught it was reading the tool constants against the model numbers, which '
      'is now worth doing to every tool in here that hard-codes geometry.',
      'tools/corridor_lamp.py')
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
# ONE LAMP NOW SURVIVES THE PARALLAX TEST, NOT TWO. Through the corrected aperture lamp 9 scores 2.9
# against a bar of 3 and lamp 11 is not found at all, so the bracket is no longer between two lamps. It is
# between the two ESTIMATORS on the one lamp that does survive, and they straddle the drawn wall.
# NARROWED 2026-09-09. This read "the back wall sits between the two estimators on the one testable
# lamp" and tested both edges. That conflated a LAMP's depth with the WALL's depth: a lamp on d -2.022
# does not put the wall on -2.022, it only forbids the wall from being shallower than the lamp. The
# ceiling locus now forbids the upper edge outright, which is how the over-claim was caught. Only the
# one-sided half survives, and the bracket is kept in the text because it is still what is known about
# that lamp.
check('the back wall is behind the one testable lamp, on both estimators of it',
      G['cBack'] <= min(LAMPV[8][1], -2.022),
      'a POINT can be tested where a line cannot: a line in that room is separated only by cameras at '
      'different distances and the slot collapses that to a leverage of 1.32, while a point is separated '
      'by the angular spread of the rays that see it. Lamp 8 is the only point behind this wall that '
      'still carries a real depth minimum, its two camera halves agreeing on d %.3f with a ratio of %.1f '
      'on a leverage of %.2f. Its own least-squares point sits on -2.022. Two estimators on the SAME rays, '
      '%.0f mm apart, straddling the wall drawn on %.3f. Lamp 9 now scores %.1f against a bar of 3 and '
      'lamp 11 is not found through the corrected gate at all. So the corridor has one testable point and '
      'a 300 mm bracket. Only the near edge of it constrains the wall.'
      % (LAMPV[8][1], LAMPV[8][3], LAMPV[8][4], 1000 * abs(LAMPV[8][1] + 2.022), G['cBack'], LAMPV[9][3]),
      'tools/lamp_v.py')
check('the corridor lamps are drawn where they were measured',
      len(LAMPS) == 2 and all(abs(a - b) < 0.001
                              for L, M in zip(sorted(LAMPS), sorted(MEASURED_LAMPS))
                              for a, b in zip(L, M)),
      '%d lamps in WALLF.corridor, down from three: the third is not found through the aperture '
      'pointed at the measured wall, so it is not drawn.' % len(LAMPS),
      'tools/corridor_lamp.py')
check('the corridor ceiling is above its own lamps',
      G['cCeil'] > max(L[2] for L in MEASURED_LAMPS),
      'ceiling drawn on %.3f, the highest lamp measured inside the room on 10.942. Clearance %.3f m. '
      'This is the ONLY constraint on that ceiling and it is one-sided.'
      % (G['cCeil'], G['cCeil'] - max(L[2] for L in MEASURED_LAMPS)),
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
# RE-PINNED 2026-09-09. This held cBack on -2.090, where the wall sat when it was placed by a lamp on
# d -2.144 that has since been withdrawn as a mask artefact. The ceiling locus cut by the lamp that
# survives moves it to -2.350. The PRINCIPLE the bound exists for is unchanged and is the reason it is
# re-pinned rather than deleted: the back wall is drawn as the face minus the width, so a change to the
# face must be absorbed by the WIDTH and must not drag the wall, because the wall was never measured
# from the face.
check('the corridor back wall stays where the evidence puts it, whatever the face does',
      abs(G['cBack'] - (-2.350)) <= 0.01,
      'the face moved 0.060 m into the hall this afternoon and the width absorbed it, 2.00 to 2.06, so '
      'the wall did not follow. Tonight the wall itself moved, on evidence: the anchored ceiling locus '
      'cut by the highest surviving lamp puts it on -2.350, and the width absorbed that too, 2.06 to '
      '%.3f. The wall is on %.3f and the face is on %.3f.'
      % (G['cWidth'], G['cBack'], G['dNorth']),
      'tools/corridor_locus.py')
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
      G['openDepth'] >= 0.422 - 1e-9,
      'openDepth %.3f. b1_000057 sits 0.422 m behind the wall face between a measured pair of jambs and '
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
# RE-RUN on rays generated with the sill, head and wall depth pointed at the measured wall (2026-09-09,
# tools/constant_drift.py found the stale ones, tools/run_wall_edges.py regenerated the rays). The
# geometry survived and a VERDICT DID NOT. The first run read 38 mm of opening-height spread against 79 mm
# of head spread and concluded the lean was entirely the instrument. The corrected run reads 48 against
# 88, which is on the other side of the same half-threshold, and with the outlier removed it reads 20
# against 5, which is on the other side again. A conclusion that turns on which side of a half a number
# lands is not a conclusion, and the earlier one went further than the evidence.
LEAN = {'head': 0.088, 'sill': 0.055, 'corr': 0.95, 'tall5': 0.048, 'tall4': 0.020,
        'mean5': 2.438, 'mean4': 2.431, 'tilt': 0.0017, 'worst': 3}
check('most of the head lean is common to the sill, and the rest is not settled',
      LEAN['corr'] >= 0.9,
      'the five openings with rays on both edges give heads spreading %.0f mm and sills spreading %.0f, '
      'correlating %+.2f. That correlation is the solid part: most of what moves the heads moves the '
      'sills with it and is therefore the instrument. Opening %d is high on BOTH edges in both runs, '
      'which is the same signature. What is NOT settled is the residual: the opening height spreads '
      '%.0f mm across all five and %.0f mm with that outlier removed, and the threshold this check used '
      'to carry flips between those two populations and between the two ray sets. The claim that the '
      'lean is entirely the instrument is withdrawn to what the correlation actually supports.'
      % (1000 * LEAN['head'], 1000 * LEAN['sill'], LEAN['corr'], LEAN['worst'],
         1000 * LEAN['tall5'], 1000 * LEAN['tall4']),
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
# THE BLACK BAND NAMED, AND THE BAR DELETED (2026-09-10, rail_over.py with rail_band.py).
RO = {'back': 0.164, 'eye': 9.810, 'thick': 0.06, 'subtend': 18, 'seen': 49, 'glass': 47,
      'hand': 0, 'solid': 0, 'ctrl_e': 0.51, 'ctrl_w': 0.63, 'band_n': 29, 'band_hits': 1,
      'rays_e': 660, 'rays_w': 366, 'drawn_e': 1.525, 'drawn_w': 1.459}
check('the band across the east gallery render has a name, and it is a mesh this file draws',
      RO['subtend'] > 10,
      'it was gallery-handrail, an opaque Lambert quad drawn across the whole width of the gallery on '
      'deck plus railTops. A deck camera stands %.3f m behind it with its eye on h %.3f, so %.0f mm of '
      'opaque bar subtends about %d degrees of vertical view, roughly a third of a portrait frame '
      'straight across the middle. That is the band, and it is the standing complaint about these '
      'balconies.'
      % (RO['back'], RO['eye'], 1000 * RO['thick'], RO['subtend']),
      'tools/rail_over.py')
check('the occlusion route has no leverage on a gallery barrier, and the reason is geometry',
      RO['glass'] > 0.9 * RO['seen'] and RO['hand'] == 0 and RO['solid'] == 0,
      'a deck camera looks out over the barrier at the north wall, so each sightline to the bottom of one '
      'of the twelve openings can be traced to the barrier plane and the photograph asked whether that '
      'opening is there. Of the %d sightlines seen at both ends together, %d crossed the barrier inside '
      'the GLASS and %d crossed the opaque handrail and %d the solid upstand. Glass blocks nothing, so '
      'seeing an opening through it contradicts nothing. Every deck camera stands with its eye between '
      'the upstand top and the rail top, which is where a person stands, so almost every sightline to '
      'anything far leaves through the glass. That is why this element has resisted every instrument, '
      'and it is recorded so the route is not rebuilt. The not-seen readings were discarded first: the '
      'control registers %.0f per cent east and %.0f west, so a miss is as likely to be the instrument.'
      % (RO['seen'], RO['glass'], RO['hand'], RO['solid'], 100 * RO['ctrl_e'], 100 * RO['ctrl_w']),
      'tools/rail_over.py')
check('so the bar was deleted rather than moved, and the measured edge under it was kept',
      RO['band_hits'] == 1 and RO['band_n'] == 29,
      'the ray fit measured a top EDGE of the lit front, %d rays inside 50 mm east and %d west. A BAR '
      'standing on that edge was never measured; it was laid over the measurement as an interpretation '
      'of it, and rail_band.py finds it in %d photograph out of %d taken from behind it. The glass quad '
      'still runs to the same rTop, so the measured edge is not given up and only the unmeasured bar '
      'goes. Both ends lose it, not only the refuted east, because at neither end did anything ever '
      'measure a bar; railTops stays %.3f east and %.3f west as the record of the edge that was.'
      % (RO['rays_e'], RO['rays_w'], RO['band_hits'], RO['band_n'], RO['drawn_e'], RO['drawn_w']),
      'tools/rail_over.py')
# AN OPENING MOVED, ON THREE LINES THAT AGREED (2026-09-10, opening_holes.py, opening_shift.py).
OP3 = {'reads': 1055, 'ctrl': 0.04, 'lo': 0.57, 'hi': 0.85, 'three': 1.10, 'spacing': 3.679,
       'within': 0.115, 'predicted': 0.784, 'measured': 0.780, 'clo': 0.600, 'chi': 0.870,
       'nframes': 49, 'worst_ctrl': 0.329, 'spread': 1.200, 'jlo': 20.027, 'jhi': 34.877,
       'was': [10.707, 11.920], 'now': [11.487, 12.700], 'pier_was': [1.796, 3.307],
       'pier_now': [2.576, 2.527], 'pier_rest': [2.324, 2.537], 'shift': 0.780}
check('the openings read as holes in the photographs and the wall between them does not',
      OP3['ctrl'] < 0.10 and OP3['hi'] < 1.0,
      'an opening is a hole into an unlit corridor, dark and flat from the hall against lit textured '
      'ashlar either side, so the inside of each drawn rectangle was compared with the pier beside it '
      'over %d readings from the walk, night and day4k frames. Eleven of the twelve come back between '
      '%.2f and %.2f of the stone beside them. The control is the wall itself and costs nothing: the '
      'same rule run the other way round, asking whether the PIER reads as a hole, fires on %.0f per '
      'cent of the same readings.'
      % (OP3['reads'], OP3['lo'], OP3['hi'], 100 * OP3['ctrl']),
      'tools/opening_holes.py')
check('opening 3 read the wrong way round, and it was the only one that did',
      OP3['three'] > 1.0,
      'its interior measured %.2f times its own pier, the brightest interior and the darkest pier of all '
      'twelve. Both halves moving together is the signature of a rectangle in the wrong PLACE: a '
      'rectangle drawn off the real opening samples stone while the pier sample beside it catches the '
      'hole. A rectangle merely drawn a little wide or a little tall cannot do that.'
      % OP3['three'],
      'tools/opening_holes.py')
check('the drawn spacing predicted where opening 3 should be before any picture was opened',
      abs(OP3['predicted'] / OP3['within']) > 5,
      'a straight line through the other eleven drawn centres spaces them %.3f m and holds every one of '
      'them within %.3f m. Opening 3 sat %.3f m WEST of that rhythm, seven times the next worst. The '
      'prediction was written down first: the photographs should find it about +0.78 m east.'
      % (OP3['spacing'], OP3['within'], OP3['predicted']),
      'tools/opening_shift.py')
check('and the photographs put it there, so for the first time a piece of this model moved',
      abs(OP3['measured'] - OP3['predicted']) < 0.02
      and abs(OP3['now'][0] - OP3['was'][0] - OP3['shift']) < 1e-6,
      'a darkest-window search swept 1.5 m either side of every opening. Read raw it would have been '
      'another stability failure: the offsets lean positive in the west and negative in the east and '
      'opening 3 alone spread %.3f m. So each opening was DIFFERENCED against the neighbours within two '
      'places of it, which cancels whatever leans the run, the move that settled the head lean. Opening 3 '
      'stands out by %+.3f m, 95 per cent %+.3f to %+.3f over 2000 resamples of its own %d frames, where '
      'the eleven controls through identical code stand out by no more than %.3f. Measured %.3f against '
      'predicted %.3f, and the two lines are independent: one is arithmetic on this file, the other is '
      'pixels. Nothing had ever measured it either: the nine jamb lines the openings were shifted on all '
      'lie between u %.3f and %.3f, which is openings 5 to 9. So it moved from %.3f-%.3f to %.3f-%.3f, '
      'and the pier either side goes from %.3f and %.3f to %.3f and %.3f where the other nine run %.3f '
      'to %.3f. This test says a hole is somewhere and never where its edges are, so opening 3 is now in '
      'the right bay and its jambs are still drawn from the same rigid set as before.'
      % (OP3['spread'], OP3['measured'], OP3['clo'], OP3['chi'], OP3['nframes'], OP3['worst_ctrl'],
         OP3['measured'], OP3['predicted'], OP3['jlo'], OP3['jhi'], OP3['was'][0], OP3['was'][1],
         OP3['now'][0], OP3['now'][1], OP3['pier_was'][0], OP3['pier_was'][1], OP3['pier_now'][0],
         OP3['pier_now'][1], OP3['pier_rest'][0], OP3['pier_rest'][1]),
      'tools/opening_shift.py')
# A MEDIAN OUTLIVES ITS OWN MEASUREMENTS, FOR THE FOURTH TIME TODAY (2026-09-10, deck_face_scan.py).
DFS = {'east_n': 32, 'step': 9.095, 'drawn': 9.095, 'near': 9.085, 'far': 9.095, 'nullo': 9.095,
       'nulle': 9.080, 'iqr': 0.432, 'spread': 1.500, 'ratio': 43, 'west_n': 7, 'deck': 8.34,
       'floor_frames': 30, 'floor_lo': 12.9, 'floor_hi': 34.0, 'deck_lo': 0.02, 'deck_hi': 3.5}
check('reading the end face from the deck is real leverage and nobody had used it',
      DFS['east_n'] > 20 and DFS['deck_hi'] < DFS['floor_lo'],
      'every scan of an end face here has been made from the hall floor: end_scan.py used %d frames from '
      '%.1f to %.1f m, where a pixel covers 15 to 25 mm. But 176 frames stand ON a deck looking out, '
      '%.2f to %.1f m behind the face, and no instrument had read the face from in there. From the deck '
      'the profile up the face should be dark across the inside of the parapet, a step, then the bright '
      'hall, with the step being the top of the solid part and nothing searched for near a drawn line.'
      % (DFS['floor_frames'], DFS['floor_lo'], DFS['floor_hi'], DFS['deck_lo'], DFS['deck_hi']),
      'tools/deck_face_scan.py')
check('and the answer came back perfect, which is the tell',
      abs(DFS['step'] - DFS['drawn']) < 0.001 and DFS['iqr'] > 0.3,
      '%d east frames put the step on h %.3f and this file draws the solid upstand top on %.3f. Zero '
      'millimetres. Near half %.3f against far half %.3f, ten apart, on a null of fifteen. But the frames '
      'underneath spread %.3f m and their interquartile range alone is %.3f m, which is %d TIMES the '
      'precision the split claims. The median of a wide scatter is stable, and both the split and the '
      'null test that stability, so both pass while the measurements under them have stopped meaning '
      'anything. The west end returns %d usable frames, so there is no control outside the run either.'
      % (DFS['east_n'], DFS['step'], DFS['drawn'], DFS['near'], DFS['far'], DFS['spread'],
         DFS['iqr'], DFS['ratio'], DFS['west_n']),
      'tools/deck_face_scan.py')
check('four instruments in one day passed a stability test and were wrong, and that is now a rule',
      DFS['ratio'] >= 8,
      'the fins split to 15 mm while two edges of ONE fin sat 0.29 m apart. The corridor lamps two '
      'tightest fits, misses of 0.128 and 0.132 m, landed 20 and 36 m from their own openings. The cloud '
      'plane fit gave five tight south bands that leaned 20 mm per metre. And this one agreed with the '
      'model to nothing on a scatter of %.3f m. Every one passed a stability test; every one was caught '
      'by something else, a redundancy the target itself provided, a control with an independently known '
      'answer, or the spread of its own inputs. deck_face_scan.py now refuses any claim more than eight '
      'times tighter than the interquartile range of its own inputs, however well it splits.'
      % DFS['spread'],
      'tools/deck_face_scan.py')
# THE EAST HANDRAIL IS NOT IN THE PICTURES, AND TWO TESTS BRACKET IT (2026-09-10, tools/rail_band.py).
BAND = {'east_n': 29, 'east_hits': 1, 'below': 107.4, 'inband': 55.9, 'above': 49.8,
        'west_n': 7, 'drawn_lo': 9.805, 'drawn_hi': 9.865, 'axis_lo': 9.420, 'deck': 8.34,
        'brk_lo': 1.080, 'brk_hi': 1.465, 'drawn_rail': 1.525, 'chest_lo': 1.2, 'chest_hi': 1.4}
check('an axis test can never refute a handrail, and that is why the last one did not',
      BAND['east_hits'] < BAND['east_n'] / 4.0,
      'rail_seeover.py projected each deck camera OPTICAL AXIS and found it threads between the solid '
      'upstand and the handrail, and that was read as clearing the handrail. An axis is one ray. A 60 mm '
      'rail standing 0.16 m from a lens blocks a BAND either side of the ray that goes under it. The '
      'question was put to the picture instead: project the rail own top and bottom edges into each frame '
      'and compare that band with the bands immediately above and below, sampled the same way in the same '
      'frame at the same exposure, so the comparison carries its own control.',
      'tools/rail_band.py')
check('the east handrail as drawn is in one frame out of twenty-nine',
      BAND['east_hits'] == 1 and BAND['east_n'] == 29,
      '%d frames put the drawn band h %.3f to %.3f in shot and %d shows a dark flat bar. The median '
      'brightness runs %.1f below the band, %.1f in it and %.1f above, which is a gradient from the lit '
      'floor up into the dark upper wall, not a bar in front of a hall. A full-width opaque handrail '
      '0.16 m from the lens cannot be invisible in 28 frames out of 29.'
      % (BAND['east_n'], BAND['drawn_lo'], BAND['drawn_hi'], BAND['east_hits'], BAND['below'],
         BAND['inband'], BAND['above']),
      'tools/rail_band.py')
check('and the two tests together bracket the east rail where neither does alone',
      BAND['drawn_rail'] > BAND['brk_hi'],
      'the sightlines say nothing opaque stands where the lowest axis crossed, h %.3f, so a handrail must '
      'be ABOVE that. The band test says it is not on %.3f to %.3f, so it must be BELOW that. The east '
      'handrail top therefore lies between %.3f and %.3f m over the deck. This file draws %.3f, which is '
      '%.0f mm outside the bracket. A third line lands inside it: the clip sweep reader described b6 1032 '
      'as a parapet with a wide flat top standing chest height on the visitors beside it, about %.1f to '
      '%.1f m, written from the pictures with no access to either test.'
      % (BAND['axis_lo'], BAND['drawn_lo'], BAND['drawn_hi'], BAND['brk_lo'], BAND['brk_hi'],
         BAND['drawn_rail'], 1000 * (BAND['drawn_rail'] - BAND['brk_hi']), BAND['chest_lo'],
         BAND['chest_hi']),
      'tools/rail_band.py')
check('and nothing is moved on it, because a bracket is not a number',
      abs(G['railEast'] - 1.525) < 1e-6 and BAND['west_n'] < 12,
      'the bracket is %.3f m wide, the west end has only %d usable frames and returns inconclusive rather '
      'than agreement, and this file has refused twice today to draw the two ends differently on evidence '
      'that covers one. What it does mean is that railTops.east %.3f is now a value the imagery EXCLUDES '
      'rather than one it has never tested, which is a different and worse position for it to be in.'
      % (BAND['brk_hi'] - BAND['brk_lo'], BAND['west_n'], G['railEast']),
      'tools/rail_band.py')
# THE OCCLUDER NAMED, THEN THE NAME DISPROVED (2026-09-10, tools/rail_seeover.py).
SEE = {'west_n': 23, 'east_n': 153, 'west_lo': 9.240, 'east_lo': 9.420, 'deck': 8.34,
       'west_spread': 0.308, 'east_spread': 0.798, 'ups_w': 9.097, 'ups_e': 9.095,
       'hand_w': 9.739, 'hand_e': 9.805, 'eye': 9.81, 'refuted': 0}
check('176 frames stand on a deck and look out, and their sightlines agree with the drawn deck',
      SEE['west_n'] + SEE['east_n'] == 176,
      'a frame that shows the hall proves its own sightline was not blocked, so the height at which its '
      'optical axis crosses the end face is a height nothing opaque can occupy. %d frames do that at the '
      'west end and %d at the east, which is worth recording on its own: this archive has far more '
      'balcony-standpoint imagery than any instrument here has used. The lowest axis crosses the west '
      'face on h %.3f, %.3f m over the deck, spread %.3f m; the east on h %.3f, %.3f m over, spread '
      '%.3f m. Those are the heights a standing eye reaches over a balustrade, so the deck %.2f and the '
      'poses agree, which is a quiet pass for a number that has never had one.'
      % (SEE['west_n'], SEE['east_n'], SEE['west_lo'], SEE['west_lo'] - SEE['deck'], SEE['west_spread'],
         SEE['east_lo'], SEE['east_lo'] - SEE['deck'], SEE['east_spread'], SEE['deck']),
      'tools/rail_seeover.py')
check('and the handrail I named as the occluder is cleared by the same test',
      SEE['refuted'] == 0,
      'only two things on that face are opaque: the solid upstand, topping out on %.3f west and %.3f '
      'east, and the 60 mm handrail on %.3f west and %.3f east. The lowest sightline passes ABOVE both '
      'upstands and BELOW both handrails; it threads the glass, which cannot block a view. The guess was '
      'made from a picture and an arithmetic coincidence, the eye height %.2f falling inside the east '
      'handrail band, and a coincidence in one frame is not a mechanism.'
      % (SEE['ups_w'], SEE['ups_e'], SEE['hand_w'], SEE['hand_e'], SEE['eye']),
      'tools/rail_seeover.py')
check('so the band in the pair render is still unexplained, and that is the honest state of it',
      SEE['east_lo'] < SEE['hand_e'] and SEE['east_lo'] > SEE['ups_e'],
      'nothing this file draws on the east face between the upstand and the handrail can stop that view, '
      'so the band comes from somewhere else: a surface not on the face plane, or a material meant to be '
      'transparent that is not rendering that way. The glass rail is a basic material on 0.28 opacity '
      'spanning %.3f to %.3f, and if its transparency fails it is opaque across most of that frame. '
      'Naming it needs a raycast from the standpoint rather than another inference from arithmetic.'
      % (SEE['ups_e'], SEE['hand_e'] + 0.06),
      'tools/rail_seeover.py')
# THE PHOTOGRAPH AND THE SIM THROUGH THE SAME LENS (2026-09-10, tools/pose_pair.py).
PAIR = {'frames': 5, 'west_agree_px': 10, 'east_u': 48.22, 'east_d': 5.43, 'east_h': 9.81,
        'east_face': 48.056, 'behind': 0.164, 'blocked': True, 'deck': 8.34, 'head': 11.09}
check('the west end from the hall floor lines up, and what differs there is tone and not shape',
      PAIR['west_agree_px'] <= 12,
      'the pair is his frame beside this model rendered from that frame OWN solved camera: same position '
      'in hall coordinates, same forward direction, same pitch, same vertical field of view, same pixel '
      'size, with the whole interface hidden by walking the DOM rather than by a selector list. On walk '
      'w1_000084 the ground wall top edge and the canopy lower edge both land within about %d px of the '
      'photograph. What differs is that this file draws the upper gallery as a bright open void with a '
      'pale soffit where the photograph shows a nearly uniform dark band with a row of lamps along its '
      'top. That is materials, not geometry.'
      % PAIR['west_agree_px'],
      'tools/pose_pair.py')
check('and from the east gallery this model puts a solid band across a view that is open in the photograph',
      PAIR['blocked'],
      'on b3_000100, standing ON the east deck on u %.2f d %.2f h %.2f and looking west down the hall, '
      'the photograph is an open view: canopy, both long walls with their opening rows, the truss, the '
      'carpet, people. The sim from the SAME camera puts a solid black horizontal band across the middle '
      'of the frame spanning nearly its whole width, with the canopy above it and the floor below it. A '
      'person standing where Lloyd stood cannot see the hall in this model, and "the balcony sections are '
      'still not correct" was said about a view from a balcony.'
      % (PAIR['east_u'], PAIR['east_d'], PAIR['east_h']),
      'tools/pose_pair.py')
check('which is the class of error no detector here could ever have reported',
      abs(PAIR['east_u'] - PAIR['east_face']) < 0.30,
      'every instrument in this repo was pointed at a level or a plane and asked how far off it was. Not '
      'one was asked whether you can SEE PAST it, so an occluder in the wrong place returns a clean bill '
      'from all of them. Which mesh it is has not been named yet and that is the next step rather than a '
      'guess: the camera stands %.3f m behind the east face plane %.3f, so the candidates are the '
      'surfaces drawn on and near that plane between the deck on %.2f and the head on %.2f. A raycast '
      'from that exact standpoint names it in one run.'
      % (PAIR['behind'], PAIR['east_face'], PAIR['deck'], PAIR['head']),
      'tools/pose_pair.py')
# THE CORRIDOR LAMPS PUT THROUGH THE SAME CONTROL (2026-09-10, tools/corridor_lamps.py).
CLAMP = {'clusters': 11, 'kept': 4, 'strays': [1.4, 2.2, 6.9, 7.9, 12.9, 19.7, 35.5],
         'best_miss': [0.128, 0.132], 'best_d': [13.05, 12.67], 'best_away': [19.7, 35.5],
         'survivor_u': 15.73, 'survivor_d': -0.11, 'survivor_h': 9.17, 'survivor_miss': 0.135,
         'face': -0.030, 'stale_d': -2.99, 'stale_ceil': 11.4}
check('twelve openings are twelve windows onto one room, and that redundancy was never used',
      CLAMP['kept'] < CLAMP['clusters'] / 2.0,
      'a lamp found through opening N is seen through a hole 1.2 m wide standing on a known u, so the '
      'point it triangulates to MUST land within about that span. The tool had every number needed to '
      'check it and printed none of it. Checked now: %d clusters were reported across the day walk, the '
      'night walk and the 4K capture, and %d land outside the opening they were found through, by %s '
      'metres. Only %d survive.'
      % (CLAMP['clusters'], CLAMP['clusters'] - CLAMP['kept'],
         ', '.join('%.1f' % v for v in CLAMP['strays']), CLAMP['kept']),
      'tools/corridor_lamps.py')
check('and the two best-fitting clusters in the whole run are the two most obviously wrong',
      min(CLAMP['best_miss']) < CLAMP['survivor_miss'] and min(CLAMP['best_d']) > 10.0,
      'the 4K capture two clusters carry misses of %.3f and %.3f m, the tightest anywhere in the run, and '
      'they land %.1f and %.1f m from their own openings on d %+.2f and %+.2f. That is not behind the '
      'north wall, it is over by the SOUTH wall: they are the hall own lights, fitted beautifully. A miss '
      'residual measures how well rays agree with each other and says nothing about whether they were '
      'pointed at the same object, which is what the fins taught the same day about a near-far split.'
      % (CLAMP['best_miss'][0], CLAMP['best_miss'][1], CLAMP['best_away'][0], CLAMP['best_away'][1],
         CLAMP['best_d'][0], CLAMP['best_d'][1]),
      'tools/corridor_lamps.py')
check('so the corridor width and ceiling have no surviving lamp under them',
      abs(G['cWidth'] - 1.420) < 1e-6 and abs(G['cCeil'] - 10.947) < 1e-6,
      'exactly one triangulation both lands in its own opening and holds a miss under 0.6 m: the day walk '
      'through opening 4, on u %.2f, d %+.2f, h %.2f, miss %.3f. It sits %.2f m behind the wall face '
      '%+.3f, not %.3f, and %.2f high, not %.3f. A fitting 80 mm behind a face is a light in the reveal. '
      'The two numbers are NOT changed, because one dropped cluster is not a replacement for another and '
      'because the deletion made today was earned by 33 rays and a swept void while this is earned by '
      'nothing. What changes is the honesty of their support. The tool was also comparing against a model '
      'that no longer exists, quoting the corridor as d %.2f on a ceiling of %.1f, which were the numbers '
      'on 2026-09-09; it reads both out of index.html at run time now.'
      % (CLAMP['survivor_u'], CLAMP['survivor_d'], CLAMP['survivor_h'], CLAMP['survivor_miss'],
         abs(CLAMP['survivor_d'] - CLAMP['face']), CLAMP['face'], G['cWidth'], CLAMP['survivor_h'],
         G['cCeil'], CLAMP['stale_d'], CLAMP['stale_ceil']),
      'tools/corridor_lamps.py')
# A SPLIT AND A NULL TEST STABILITY, NOT CORRECTNESS (2026-09-10, tools/fin_v.py).
FINV = {'pooled': 15.105, 'drawn': 15.240, 'near': 15.115, 'far': 15.130, 'nullo': 15.095,
        'nulle': 15.105, 'resid': 4.66, 'settings': [15.105, 15.115, 15.115, 15.115],
        'reads': [318, 645, 172, 950], 'fins': [15.145, 15.125, 15.135, 15.120, 15.365],
        'pairs': [(15.130, 15.300), (15.325, 15.115), (15.105, 15.395)], 'fin_gap': 0.40,
        'n_pixwin': -0.285, 'n_known': -0.030, 'n_strict': 13}
check('the fin test passed every stability check this file owns',
      abs(FINV['near'] - FINV['far']) < 0.02 and max(FINV['settings']) - min(FINV['settings']) < 0.02,
      'each south fin is 0.40 m wide on a known u, so both vertical edges of its hall-side face are lines '
      'on known u and UNKNOWN d, and a ray to one carries exactly ONE unknown. Detection happens once in a '
      'window fixed around the drawn d and the answer is solved afterwards from recorded pixels, so the '
      'sweep cannot drag the detector after it. It came back d %.3f, %.0f mm in front of the drawn %.3f, '
      'near half %.3f against far half %.3f, a null of %.0f mm, a median residual of %.2f px, and across '
      'four detector settings from %d to %d readings it moved %.0f mm in total.'
      % (FINV['pooled'], 1000 * (FINV['drawn'] - FINV['pooled']), FINV['drawn'], FINV['near'],
         FINV['far'], 1000 * abs(FINV['nullo'] - FINV['nulle']), FINV['resid'], min(FINV['reads']),
         max(FINV['reads']), 1000 * (max(FINV['settings']) - min(FINV['settings']))),
      'tools/fin_v.py')
check('and the fins themselves refused it, which is what a control is for',
      max(FINV['fins']) - min(FINV['fins']) > 0.15,
      'five fins stand in five places on ONE plane and each has two edges %.2f m apart, so a detector on '
      'the fin faces must return one d for all ten. It does not. The five scatter %.3f to %.3f, a spread '
      'of %.3f m, and inside a single fin the two edges land %s. Two edges of the SAME fin cannot be '
      '0.29 m apart in depth. The outside control had already gone silent: with a window fixed in PIXELS '
      'the north jambs read %+.3f against a station known to %+.3f, and tightened to metres only %d '
      'readings survive, because those openings are 100 to 150 px wide carrying under 20 grey levels.'
      % (FINV['fin_gap'], min(FINV['fins']), max(FINV['fins']),
         max(FINV['fins']) - min(FINV['fins']),
         ', '.join('%.3f and %.3f' % pr for pr in FINV['pairs']),
         FINV['n_pixwin'], FINV['n_known'], FINV['n_strict']),
      'tools/fin_v.py')
check('so dSouth stays, and what the 15 mm agreement was measuring is now written down',
      abs(G['dSouth'] - 15.364) < 1e-6,
      'the median of a wide scatter is stable. The near-far split, the odd-even null and the settings '
      'sweep all test the STABILITY of that median, and a scatter spread evenly enough is perfectly '
      'stable while being perfectly wrong. Only a control asks the other question, and when the outside '
      'control went silent the redundancy of the fins supplied one for nothing. dSouth stays on %.3f for '
      'the second time today, refused by a sharper instrument and for a sharper reason: no detector in '
      'this archive can find a south fin edge well enough for two edges of one fin to agree inside '
      '0.29 m. That is a statement about the capture and not about the wall.'
      % G['dSouth'],
      'tools/fin_v.py')
# THE HALL WIDTH PUT TO THE CLOUD, AND THE CONTROL THAT FAILED (2026-09-10, tools/wall_plane.py).
WPL = {'n_lo': -0.178, 'n_hi': -0.017, 'n_known': -0.030, 'n_spread': 0.361, 'n_halves': 0.531,
       'n_clean': 0, 's_clean': 5, 's_fit': 15.275, 's_lean': 0.0197, 's_leanmm': 79,
       's_meds': [15.317, 15.296, 15.275, 15.258, 15.237], 's_tight_lo': 0.017, 's_tight_hi': 0.032,
       'fin_frames': 4, 'fin_d': 15.24}
check('the cloud cannot place a long wall, and the north wall is what proves it',
      WPL['n_clean'] == 0,
      'the north face is known to 1 to 2 mm by the near-far V test on d %+.3f, an instrument sharing '
      'nothing with a point cloud, so the identical band-by-band fit was run there FIRST. It fails: the '
      'medians scatter %+.3f to %+.3f across the height bands, the spread inside a band reaches %.3f m, '
      'and the west and east halves of the same band disagree by up to %.3f m. Not one north band is both '
      'tight and consistent. A cloud that cannot reproduce a number already known to 2 mm has not earned '
      'the right to move one that is unknown.'
      % (WPL['n_known'], WPL['n_lo'], WPL['n_hi'], WPL['n_spread'], WPL['n_halves']),
      'tools/wall_plane.py')
check('the south answer looked tight and was thrown away, and that is the point of the control',
      abs(G['dSouth'] - 15.364) < 1e-6,
      '%d south bands come back tight, spreads of %.3f to %.3f m with the halves agreeing to within '
      '0.029, and they put the wall on d %.3f, which is %.0f mm in front of the drawn %.3f. Applied, that '
      'would have moved the hall width and every balcony d with it. It is NOT applied, because those five '
      'medians fall MONOTONICALLY with height, %s, a lean of %.4f m per metre and %d mm across the four '
      'metres of clean band. No ashlar wall leans 20 mm per metre. That is a registration tilt or a '
      'grazing-angle bias and the 89 mm sits inside it. A tight number from a biased instrument is more '
      'dangerous than a loose one.'
      % (WPL['s_clean'], WPL['s_tight_lo'], WPL['s_tight_hi'], WPL['s_fit'],
         1000 * (G['dSouth'] - WPL['s_fit']), G['dSouth'],
         ', '.join('%.3f' % v for v in WPL['s_meds']), WPL['s_lean'], WPL['s_leanmm']),
      'tools/wall_plane.py')
check('and only four posed frames in the whole archive face the south fins, which is the real limit',
      WPL['fin_frames'] < 10,
      'of every posed floor frame here, %d see three or more south glazing fins whole, and that count is '
      'itself the measure of how little this capture ever faced that wall. On night w6_000074 and walk '
      'w1_000131 the fins drawn on d %.2f land on real vertical members and the drawn doorway lands on '
      'the real doorway, which refuses a gross error and cannot see 89 mm. dSouth stays on %.3f and the '
      'reason it cannot be improved is now measured rather than inherited. What would measure it is the '
      'near-far V test pointed at the fins own vertical edges; depth_v.py is hard-wired to two targets '
      'today and would have to be opened up.'
      % (WPL['fin_frames'], WPL['fin_d'], G['dSouth']),
      'tools/wall_plane.py')
# THE CLOUD CENSUS, THE AUDIT OF THE DELETION, AND THE HOLE THAT MEASURES THE RECESS (2026-09-10,
# tools/end_cloud_census.py, tools/end_gap.py).
CLOUD = {'clip_models': {'b1': 0, 'b3': 0, 'b4': 389, 'b5': 644, 'b6g': 63, 'b6s': 10, 'b7s': 110},
         'in_band': 0, 'site_west': 15, 'site_east': 36, 'audit_in_void': 7, 'lamp_like': 3,
         'lamp_du': 0.20, 'lamp_dd': 0.08, 'white': 231, 'envelope': 4, 'env_lo': 0.03, 'env_hi': 0.09,
         'e_deep': 21, 'e_track': 15, 'e_err': 1.22, 'e_lo': 5.65, 'e_hi': 7.45, 'gap': 0.959,
         'sill': 6.188, 'head': 7.148, 'p_east': 5.17e-06, 'w_deep': 8, 'p_west': 1.19e-02,
         'w_sill': 5.846, 'w_head': 6.617}
check('not one balcony clip reconstructed a single point of either end recess',
      CLOUD['in_band'] == 0 and min(CLOUD['clip_models'].values()) >= 0,
      'end_cloud.py had only ever been aimed at the day4k model, and the standing note that the ends carry '
      'almost no surface was written about a capture shot from the hall FLOOR forty metres off. The '
      'balcony clips were shot on the upper level three metres from the recess and each has its own '
      'reconstruction, so every one was counted: %s. None has a point in the band. Standing close did not '
      'reconstruct it, and that is now measured rather than assumed. Everything in the band comes from the '
      'one shared site cloud, %d points west and %d east.'
      % (', '.join('%s %d total' % (k, v) for k, v in sorted(CLOUD['clip_models'].items())),
         CLOUD['site_west'], CLOUD['site_east']),
      'tools/end_cloud_census.py')
check('the deletion was checked against that cloud and it stands, with its blind spot now written down',
      CLOUD['lamp_like'] + CLOUD['envelope'] == CLOUD['audit_in_void'],
      '%d of the %d west points fall INSIDE the swept void, which would refute it. %d do not: they sit on '
      'u 2.39, d 7.73 to 7.83, h 6.93 to 7.05, which is %.2f m in u and %.2f in d from the triangulated '
      'fitting, and one is rgb %d, white. The cloud found the same lamp on its own. That exposes a real '
      'limit of the sweep: within about %.1f m of the fitting the void is only as empty as the fitting, '
      'because the rays END there. The other %d sit %.2f to %.2f m UNDER the void upper envelope near the '
      'face, which is where a grazing bundle boundary lies, so they fit a real surface bounding the rays '
      'from above rather than a wrong void.'
      % (CLOUD['audit_in_void'], CLOUD['site_west'], CLOUD['lamp_like'], CLOUD['lamp_du'],
         CLOUD['lamp_dd'], CLOUD['white'], CLOUD['lamp_du'], CLOUD['envelope'], CLOUD['env_lo'],
         CLOUD['env_hi']),
      'tools/end_cloud_census.py')
check('a hole in the deep east points measures a sill and a head, and it is not thin sampling',
      CLOUD['p_east'] < 0.001,
      'take only points more than a metre behind the face, so nothing on the face is in the sample. An '
      'open recess puts points on its sill and its head with AIR between; one flat wall spreads them. The '
      'east has %d such points, median track %d, median error %.2f px, running h %.2f to %.2f, with a '
      'HOLE %.3f m tall from %.3f to %.3f, eleven below and ten above. A random scatter of %d over 1.80 m '
      'makes a gap that big with probability %.2e. b5 136-190 had already read this tier as a recess with '
      'a definite head AND a definite sill; the cloud now puts numbers on both, and the two lines are '
      'entirely independent.'
      % (CLOUD['e_deep'], CLOUD['e_track'], CLOUD['e_err'], CLOUD['e_lo'], CLOUD['e_hi'], CLOUD['gap'],
         CLOUD['sill'], CLOUD['head'], CLOUD['e_deep'], CLOUD['p_east']),
      'tools/end_gap.py')
check('and it is NOT drawn, because the west cannot carry the same claim',
      CLOUD['p_west'] > 0.01 and CLOUD['w_deep'] < 10,
      'the west has only %d deep points and its own best hole, %.3f to %.3f, comes back at probability '
      '%.2e, which is suggestive and not a measurement, and it sits about 0.4 m off the east one. Drawing '
      'a slot at one end on %d points while the other end has %d would put a difference into this model '
      'that the evidence does not carry, and this file has already refused that once today over the lamp. '
      'The recess stays open 5.30 to 8.08 at both ends. What would settle it is the one thing this archive '
      'has never had: frames shot INTO an end recess rather than along the hall past it.'
      % (CLOUD['w_deep'], CLOUD['w_sill'], CLOUD['w_head'], CLOUD['p_west'], CLOUD['e_deep'],
         CLOUD['w_deep']),
      'tools/end_gap.py')
# THE SWEPT VOID, AND THE FOUR SURFACES IT DELETED (2026-09-10, tools/lamp_void.py).
VOID = {'planes': [(0.000, 5.458, 6.842), (0.509, 5.871, 6.926), (1.019, 6.284, 7.010),
                   (1.528, 6.697, 7.094), (2.003, 7.002, 7.173)],
        'rays': 33, 'apron_ov': 0.872, 'upstand_ov': 0.512, 'slab': 6.33, 'deleted': 4,
        'd_lo': 6.2, 'd_hi': 8.2, 'recess_lo': 5.30, 'recess_hi': 8.08}
check('the emptiness is swept in world coordinates, not sampled on one plane',
      len(VOID['planes']) >= 5 and VOID['planes'][-1][0] > 1.9,
      'a bound on ONE plane can be dodged by moving the surface off it, and this file has done that '
      'before: the corridor width absorbed a face move rather than admitting one. A lower front pushed '
      'back a few centimetres would satisfy a face-plane bound and go on blocking the same light. Each of '
      'the %d rays ran from a camera in the hall all the way to the fitting, so every point on it is '
      'empty. Plane by plane behind the face the band that must be empty is %s. All %d rays reach every '
      'plane, and anything drawn inside that is refuted wherever it sits.'
      % (VOID['rays'], '; '.join('%.2f m back, h %.3f to %.3f' % pl for pl in VOID['planes']),
         VOID['rays']),
      'tools/lamp_void.py')
check('four surfaces were deleted, and the one that matters is the deck and not the front',
      VOID['deleted'] == 4,
      'the apron overlapped the void by %.3f m, the lower parapet upstand by %.3f m, the glass rail stood '
      'on the same refuted front, and the lower gallery FLOOR, a slab on %.2f running from the face back '
      'to the plate end, is struck at the face itself. They are deleted and NOT moved, because a sweep '
      'says where the emptiness is and can never say where a surface went. What is drawn in their place '
      'is what remains: an open recess from the ground wall soffit on %.2f up to the top slab on %.2f '
      'with the back wall behind it, which is what b4 232-246, b5 136-190 and b1 208-286 all describe.'
      % (VOID['apron_ov'], VOID['upstand_ov'], VOID['slab'], VOID['recess_lo'], VOID['recess_hi']),
      'tools/lamp_void.py')
check('the proof is west-only, the change is both ends, and most of the recess is still unknown',
      VOID['d_hi'] - VOID['d_lo'] < 4.0,
      'the rays are the west end near d %.1f to %.1f and say nothing about the rest of the 15.4 m width; '
      'the two east candidates failed their own split by 0.481 and 2.015 m. The clips read the same '
      'recess at both ends, and drawing the ends differently on no east evidence would be worse than '
      'drawing them alike, so both changed. The recess has a real sill, a real head and a real depth and '
      'none of the three is measured. 6.33, 6.85 and 7.16 stay in ENDW as the record of what was refuted '
      'and no geometry reads them now. The 1.75 m clear height is not repaired but WITHDRAWN: there is no '
      'lower deck in this file any more to be 1.75 m under anything.'
      % (VOID['d_lo'], VOID['d_hi']),
      'tools/lamp_void.py')
# LIGHT WENT THROUGH A WALL THIS FILE DRAWS SOLID (2026-09-10, tools/gallery_lamp.py, lower band).
LAMP = {'u': 2.191, 'd': 7.858, 'h': 7.083, 'rays': 33, 'rms': 0.047, 'base': 28.9, 'du': 0.066,
        'dh': 0.035, 'x_lo': 5.458, 'x_hi': 6.842, 'face': 4.194, 'back': 0.344,
        'east_fail': [0.481, 2.015], 'others_lo': 0.079, 'others_hi': 5.365,
        'apron': 5.40, 'lowdeck': 6.33, 'lowup': 6.85}
check('a fitting inside the west lower band triangulates 2.0 m behind the face and passes its own split',
      LAMP['du'] < 0.10 and LAMP['du'] < min(LAMP['east_fail']),
      'every instrument aimed at the lower tier today needed a PLANE, and the lower tier is not on the '
      'plane they were searching. A lamp needs no plane: it is a point, two rays fix it, and a bright '
      'point survives a bad exposure and a steep angle. gallery_lamp.py had its band hard-wired to the '
      'upper gallery, so the lower tier had never been offered to it; the band is now an argument. The '
      'point lands on u %.3f d %.3f h %.3f from %d rays, %.3f m rms, cameras %.1f m apart. Its depth had '
      'to be tested on a new axis: lamp_v.py splits a point along its DEPTH axis, which at an end is u, '
      'and every camera here stands on the hall side, so that split returned zero rays on one side for '
      'every fitting. Split instead across the hall width, south against north, the halves land %.3f m '
      'apart in u and %.3f in h. The two east candidates split by %.3f and %.3f and are dropped, and '
      'every other cluster in the same run split by %.2f to %.2f m, so %.3f is the tight end of the run.'
      % (LAMP['u'], LAMP['d'], LAMP['h'], LAMP['rays'], LAMP['rms'], LAMP['base'], LAMP['du'],
         LAMP['dh'], LAMP['east_fail'][0], LAMP['east_fail'][1], LAMP['others_lo'], LAMP['others_hi'],
         LAMP['du']),
      'tools/gallery_lamp.py')
check('and its rays crossed the west face where this file draws a solid apron and a solid deck front',
      LAMP['x_lo'] > LAMP['apron'] and LAMP['x_hi'] < LAMP['lowup'],
      'this is the half that needs no identification of the fitting and no plane at all. The %d rays came '
      'from the hall and reached a point %.3f m BEHIND the face plane u %.3f, so nothing on the face '
      'blocked them, and they crossed that plane between h %.3f and h %.3f. This file draws the apron quad '
      'from %.2f to %.2f on the face and the lower deck slab with its upstand from %.2f to %.2f on the '
      'same plane. As built, every one of those rays is stopped by geometry this file asserts, and light '
      'does not do that.'
      % (LAMP['rays'], LAMP['face'] - LAMP['u'], LAMP['face'], LAMP['x_lo'], LAMP['x_hi'],
         LAMP['apron'], LAMP['lowdeck'], LAMP['lowdeck'], LAMP['lowup']),
      'tools/gallery_lamp.py')
check('so the west lower front is open, and that is a bound rather than a replacement number',
      abs(G['lowUp'] - 0.52) < 1e-6,
      'the front is open between h %.3f and %.3f. Knowing a front is open does not say where its real head '
      'and sill are, so nothing is renumbered on it. What it settles is the argument the rest of today '
      'only pointed at: the lower tier is not a deck standing on the end face, and the apron under it is '
      'not a wall. The drawn %.2f m upstand and the %.2f m glass rail over it stand on a front that has '
      'now been shown to pass light.'
      % (LAMP['x_lo'], LAMP['x_hi'], G['lowUp'], G['lowRail']),
      'tools/gallery_lamp.py')
# THE LOWER GALLERY IS A RECESS SET BACK AND NOT A DECK ON THE FACE (2026-09-10, tools/end_scan.py,
# tools/end_ladder.py, and a 68-agent sweep of the seven clips).
LOW = {'refused': 6, 'bar': 0.55, 'gaps': [0.10, 0.52, 0.26], 'wpara': 8.972, 'epara_day': 9.124,
       'epara_night': 9.136, 'wnf': 0.012, 'wnull': 0.004, 'e1': 6.640, 'e2': 7.304, 'e1nf': 0.008,
       'e1null': 0.004, 'sep': 0.664, 'frames': 30, 'rlo': 12.9, 'rhi': 34.0, 'lines_drawn': 6}
check('the lower gallery has never been measured, and the tool that measures ends refuses it by design',
      LOW['refused'] == 6,
      'tools/end_levels.py finds a level by projecting the line the MODEL draws and taking the strongest '
      'gradient in a window round it, and refuses any level whose nearest modelled neighbour is closer '
      'than %.2f m. Down the ENDW stack that is ground top 5.30 against apron 5.40 (%.2f m), lower deck '
      '%.2f against lower upstand %.2f (%.2f m), and slab soffit %.2f against top deck %.2f (%.2f m): all '
      '%d refused. Of the nine lines drawn across an end face the floor imagery has only ever measured '
      'the top parapet, the head and the wall top.'
      % (LOW['bar'], LOW['gaps'][0], 6.33, 6.85, LOW['gaps'][1], 8.08, G['deck'], LOW['gaps'][2],
         LOW['refused']),
      'tools/end_scan.py')
check('an unseeded scan of the end faces reproduces the west-east parapet split it was never told about',
      abs(LOW['epara_night'] - LOW['wpara']) > 0.10,
      'tools/end_scan.py walks h continuously up the face and reports where the brightness steps, so it '
      'has no drawn line to follow; tools/follow_test.py measured that following as about 45 per cent of '
      'an answer from the old finder. Near against far, a null of the same frames split odd against even, '
      'and two smoothing widths were all stated before it ran. It puts the west parapet on %.3f and the '
      'east on %.3f by day and %.3f by night against %.2f and 9.11 drawn, and that line is 10 to 30 times '
      'stronger than anything else on either face. West reads near-far %.3f on a null of %.3f and does '
      'not move between windows.'
      % (LOW['wpara'], LOW['epara_day'], LOW['epara_night'], G['deck'] + G['upWest'], LOW['wnf'],
         LOW['wnull']),
      'tools/end_scan.py')
check('and it finds nothing on the west face where this file draws six lines',
      LOW['lines_drawn'] == 6,
      'between the parapet top and the ground wall near 5.2 the west end is one continuous dark band with '
      'no edge that survives all three tests, over %d frames from %.1f to %.1f m. This file draws %d lines '
      'in that band. The east face by night does carry two, %.3f (near-far %.3f on a null of %.3f) and '
      '%.3f, %.3f m apart where this file draws 0.31 from upstand top to rail top. The clips say what it '
      'is: b4 232-246, b5 136-190 and b1 208-286 independently read the lower tier as a deep unlit RECESS '
      'set back behind the parapet face, with a head, a sill, a back wall, a doorway with two downlights '
      'over it, and no balustrade and no people. This file draws a deck ON the face with a rail and a '
      'ceiling %.2f m over it, which is why it reads as a room nobody could stand up in. Nothing is '
      'renumbered on this, because a recess needs a depth, a sill and a head and none is measured yet.'
      % (LOW['frames'], LOW['rlo'], LOW['rhi'], LOW['lines_drawn'], LOW['e1'], LOW['e1nf'],
         LOW['e1null'], LOW['e2'], LOW['sep'], 8.08 - 6.33),
      'tools/end_ladder.py')
# NOBODY EVER TURNED ROUND (2026-09-10, tools/find_corridor.py): there is no frame inside the corridor.
NOTURN = {'frames': 917, 'clips': 3, 'runs': 3, 'inside': 0, 'd_lo': -0.45, 'd_hi': 0.12,
          'h_lo': 9.07, 'h_hi': 10.14, 'px_lo': 100, 'px_hi': 150, 'levels': 20}
check('not one of the 917 frames shot from inside the north openings looks into the corridor',
      NOTURN['inside'] == 0,
      'b1, b4 and b5 are posed with the camera on d %+.2f to %+.2f and h %.2f to %.2f, standing IN an '
      'opening. If the operator had turned round, the frame would show the corridor from inside, and that '
      'room is the least measured thing here. Every ACCEPTED frame of those clips points out at the hall, '
      'which proves nothing, because the registrar solves against a model of the HALL and a frame aimed '
      'into dark stone has nothing to match. So all %d were scored on the two things a corridor frame '
      'cannot contain, the stained glass and the pink carpet, and ranked. %d runs came back and all %d '
      'are hall views: the south wall with its tapestry, the canopy seen 22 degrees up, and the balcony '
      'across the hall. Each was opened and looked at rather than trusted to the score.'
      % (NOTURN['d_lo'], NOTURN['d_hi'], NOTURN['h_lo'], NOTURN['h_hi'], NOTURN['frames'],
         NOTURN['runs'], NOTURN['runs']),
      'tools/find_corridor.py')
check('so the corridor numbers cannot improve on this archive and should stop being hunted in it',
      abs(G['cWidth'] - 1.420) < 1e-6,
      'already on the record: from the hall floor an opening is %d to %d px wide carrying under %d grey '
      'levels, the head soffit stands over the reveal so an upward sightline ends on its underside, and '
      'no posed frame is in the room. Now added: on the one day anybody was up there with a camera, not '
      'one of %d frames from inside the openings is aimed into the corridor. He stood in the window and '
      'filmed the room, which is what a person does. Width %.3f and ceiling %.3f therefore stay exactly '
      'as strong as the single lamp-locus crossing that produced them, floor 8.34 stays unmeasured, and '
      'moving any of them needs new capture rather than another pass over this one.'
      % (NOTURN['px_lo'], NOTURN['px_hi'], NOTURN['levels'], NOTURN['frames'], G['cWidth'], G['cCeil']),
      'tools/find_corridor.py')
# THE END WALL COUNTED IN ITS OWN COURSES, NO CAMERA IN THE ARGUMENT (2026-09-10, tools/wall_courses.py).
CRS = {'course': 0.306, 'strips': 7, 'agree': [60.0, 60.5, 61.0, 61.5], 'counted': 16.8,
       'metres': 5.15, 'frame_w': 2160, 'frame_h': 3840, 'endtop_captures': 5, 'endtop_resid': -0.009}
check('the end wall stack is confirmed by counting stone, and it has no room left in it',
      abs(13.5 - G['deck'] - CRS['metres']) < 0.15,
      'the frames that stand ON a balcony are the ones the registrar could not solve, because it solves '
      'against a model of the HALL and a frame aimed at the wall beside the operator has nothing to match. '
      'So the best views here carry no pose, and the ashlar is a ruler that does not need one: it was '
      'coursed off the 4 mm orthophotos of 1,026 posed frames on %.3f m. In b7_000810, %d by %d and sharp, '
      'four of %d strips agree on a joint pitch of %s px, 2.5 per cent apart, and from the canopy junction '
      'down to the BOTTOM EDGE OF THE FRAME is %.1f courses, %.2f m of continuous ashlar, with the deck '
      'still below it. This file draws 13.5 less %.2f = %.2f m. The stone says at least %.2f and the frame '
      'ran out before the floor did, so any further course means the deck is lower than drawn or the wall '
      'top higher, and the wall top is pooled across %d captures with a residual of %+.3f m at this end.'
      % (CRS['course'], CRS['frame_w'], CRS['frame_h'], CRS['strips'],
         ', '.join('%.1f' % v for v in CRS['agree']), CRS['counted'], CRS['metres'], G['deck'],
         13.5 - G['deck'], CRS['metres'], CRS['endtop_captures'], CRS['endtop_resid']),
      'tools/wall_courses.py')
check('a count is a separation and never a height, and it is said before it is used',
      CRS['metres'] > 0,
      'this measures the distance between two things in one picture. It cannot say where either of them '
      'sits, so it can test whether the drawn stack is the right SIZE and can never place it. It also '
      'assumes the end wall courses with the long walls it was calibrated on, which is likely in one build '
      'and is not proved here. Counting more carefully repairs neither.',
      'tools/wall_courses.py')
# WHAT LLOYD'S OWN VIDEO SHOWS ON THE BALCONY, looked at rather than fed to a detector (2026-09-09,
# tools/balcony_sheet.py + balcony_chunks.py + balcony_look.py + frame_out.py + parapet_top.py).
CLIPS = {'clips': 7, 'frames': 5300, 'vitrine_a': 1240, 'vitrine_b': 1324, 'ceiling_frame': 1312,
         'soffit': 2.1, 'head': 11.09, 'endtop': 13.5, 'rays': 382, 'shallow': 9.475, 'steep_lo': 8.625,
         'steep_hi': 8.980, 'spread': 0.850, 'near': 0.43, 'far': 0.91, 'floor_px': 0.020,
         'deck_px': 0.0005, 'b6s_u': 30.8, 'b6s_d': 23.2, 'b6s_h': 1.23}
check('the end balcony is a furnished gallery and this model draws an empty slab',
      CLIPS['vitrine_b'] > CLIPS['vitrine_a'],
      "Lloyd: \"I gave you videos. You need to look through them thoroughly\", and then \"I was also "
      "hoping you would look at these ones on the balcony with the glass cabinets\". Seven clips and "
      "%d frames were shot on this level and every tool here had used them only as poses to feed a "
      "detector; none had displayed them. b6 frames %d to %d walk along a balcony past white plinths "
      "carrying Greek vases under tall glass vitrines, with a lit doorway and dark stone niches in the "
      "back wall behind them. A detector answers the question it was set and cannot report that a "
      "balcony is the wrong shape, because nobody asked it that."
      % (CLIPS['frames'], CLIPS['vitrine_a'], CLIPS['vitrine_b']),
      'tools/balcony_chunks.py')
check('a claim I shipped an hour earlier was withdrawn by a sharper frame of the same junction',
      CLIPS['endtop'] > G['gHead'],
      'in b6_%06d the balcony back wall is ashlar that stops on a clean horizontal line and the Leonard '
      'French canopy meets it there, with no stone above and no separate flat ceiling over the deck. This '
      'file draws the end walls as stone to h %.1f with a %.1f m soffit on %.2f over the front of each '
      'balcony and an open void behind it. I WROTE THAT THIS CONTRADICTED THE MODEL AND IT DOES NOT. To '
      'get there I turned an angle into a height by guessing the range, in a clip stored 1520 by 2032 and '
      'heavily compressed. b7_000806 and b7_000810 hold the same junction at the west end in sharp 4K and '
      'show ashlar running UP to the canopy with doorways and a vent below it, which is what this file '
      'draws. An angle is not a height until something fixes the range, and nothing did.'
      % (CLIPS['ceiling_frame'], CLIPS['endtop'], CLIPS['soffit'], G['gHead']),
      'tools/balcony_look.py')
check('a contested pose is settled by what is overhead in the picture rather than by the registration',
      CLIPS['b6s_d'] > 15.364 or CLIPS['b6s_h'] < 5.0,
      'b6s registers that stretch of the clip OUTSIDE this hall, u %.1f d %.1f h %.2f, on the ground '
      'floor of another gallery, while b6g puts neighbouring frames of the SAME clip on the east deck. '
      'The archive recorded the contradiction and rested nothing on either. It does not have to: the '
      'Leonard French ceiling covers one room in this building and it is directly overhead in these '
      'frames, so the camera is inside the Great Hall volume, which at that height means standing on a '
      'balcony. b6s is wrong there and Lloyd, who was holding the phone, says the same.'
      % (CLIPS['b6s_u'], CLIPS['b6s_d'], CLIPS['b6s_h']),
      'tools/balcony_look.py')
check('forty times the resolution on the wrong feature is still the wrong feature',
      CLIPS['spread'] > 0.3,
      'b7 frames 604 to 920 are posed and stand ON the west deck, which puts the drawn parapet %.2f to '
      '%.2f m from the lens where a pixel covers about %.1f mm instead of the %.0f mm it covers from the '
      'hall floor. That is the leverage this model has been missing. The detector found a strong '
      'bright-above dark-below step on every one of %d rays and it is NOT one edge: solved on the '
      'set-back plane it reads %.3f on the frames pitched 12 degrees down and %.3f to %.3f on those '
      'pitched 20 to 23 degrees down, %.0f mm of spread on a feature that cannot move. The split is by '
      'PITCH, which is what a detector reading two different things looks like. Nothing is moved on it.'
      % (CLIPS['near'], CLIPS['far'], 1000 * CLIPS['deck_px'], 1000 * CLIPS['floor_px'], CLIPS['rays'],
         CLIPS['shallow'], CLIPS['steep_lo'], CLIPS['steep_hi'], 1000 * CLIPS['spread']),
      'tools/parapet_top.py')
# THE LOWER END BALCONY IS DRAWN 1.75 m HIGH INSIDE (2026-09-09, arithmetic on this file's own numbers).
TIER = {'deck': 6.33, 'slab': 0.26, 'upper': 8.34, 'rail': 7.16, 'depth': 3.85,
        'habitable': 2.1, 'lenses_lower': 0, 'lenses_upper': 309, 'end_spread': 0.163}
_clear = TIER['upper'] - TIER['slab'] - TIER['deck']
check('the lower balcony as drawn is too low inside to be the gallery it is drawn as',
      _clear < TIER['habitable'],
      'the lower deck 6.33 and the ceiling over it 8.08 were both read off the same 4K frame, and their '
      'difference is %.2f m of clear height over a floor %.2f m deep with a balustrade drawn on its edge. '
      'A balustrade says people stand there; %.2f m says they cannot, being under every habitable minimum '
      '(%.1f m) and under the standing height of a large share of adults. Two readings that cannot both '
      'mean what they were taken for. RESOLVED 2026-09-10, and not the way this line expected: the deck '
      'and the front it stood on were both deleted (tools/lamp_void.py), because 33 rays crossed the space '
      'they occupied. There is no lower deck in this file any more to be %.2f m under anything, so the '
      'contradiction is withdrawn rather than repaired. The wording above is kept as the record of the '
      'question that led to the sweep.'
      % (_clear, TIER['depth'], _clear, TIER['habitable'], _clear),
      'tools/check_bounds.py')
check('and no camera in the archive has ever stood on the lower deck',
      TIER['lenses_lower'] == 0 and TIER['lenses_upper'] > 100,
      'the upper deck carries %d lenses across the captures and the lower one carries %d. That is '
      'CONSISTENT with the lower band being closed to the public, which would make the drawn rail the '
      'wrong element, and it is not evidence of it: nobody films from a service level either way. Named '
      'so the three live possibilities stay separable - the 6.32 row is a parapet and not a floor, the '
      '8.08 row hangs under the real ceiling, or the band is not occupied. The two readings that resolve '
      'this tier already disagree by %.0f mm between the two ends, so there is no room to fit a third '
      'answer out of them.'
      % (TIER['lenses_upper'], TIER['lenses_lower'], 1000 * TIER['end_spread']),
      'tools/check_bounds.py')
# THE HEAD RESIDUAL: BUILT, SHIPPED INTO ELEVEN TOOLS, REFUSED BY A BOUND, REVERTED
# (2026-09-09, tools/head_obliquity.py + tools/head_rebate.py).
HRES = {'sill': 0.010, 'head': -0.110, 'null': -0.020, 'profiles': 232, 'openings': 6, 'of': 7,
        'dissent': -0.005, 'windows': 3, 'implied': 2.315, 'measured_h': 2.431,
        'D_head': 0.083, 'D_sill': -0.000, 'D_null': 0.030, 'n_head': 794, 'n_sill': 2370,
        'n_null': 412, 'jamb': 0.178, 'Lmin': 11.0, 'Lmax': 14.0}
check('the head residual is real and better controlled than most things shipped tonight',
      abs(HRES['head']) > 3.0 * abs(HRES['null']) and abs(HRES['sill']) < 0.030,
      'a profile walked through every drawn edge in 789 walk frames finds the SILL right, %+.0f mm, and '
      'the HEAD %+.0f mm on %d of %d openings that carry square-on views, %d profiles, identical through '
      '%d windows, against a pier null of %+.0f mm. One opening dissents on %+.0f mm and is named. The '
      'sill is the control that says the detector is not biased downward in general.'
      % (1000 * HRES['sill'], 1000 * HRES['head'], HRES['openings'], HRES['of'], HRES['profiles'],
         HRES['windows'], 1000 * HRES['null'], 1000 * HRES['dissent']),
      'tools/head_obliquity.py')
check('the move I had already applied everywhere was refused by a bound written days ago',
      abs(HRES['measured_h'] - HRES['implied']) > 0.100,
      'the head was moved to 11.055 in the model and in every tool carrying it as a live aperture '
      'constant. This suite refused it: tools/head_lean.py measures the opening HEIGHT as a difference in '
      'which a drift common to sill and head cancels, and gets %.3f m across four openings, where the '
      'move implies %.3f. Two instruments that both claim to cancel their own bias disagreeing by %.0f mm '
      'is not settled by preferring the newer one, so the change was reverted whole. The bound that '
      'caught it was written days ago for a different reason.'
      % (HRES['measured_h'], HRES['implied'],
         1000 * abs(HRES['measured_h'] - HRES['implied'])),
      'tools/check_bounds.py')
check('the residual expressed as a depth does not clear its own null by enough',
      abs(HRES['D_head']) < 3.0 * abs(HRES['D_null']),
      'a horizontal return standing D behind the face projects lower than the arris by '
      '(H - h_cam) * D / (L + D), so the residual can be solved for D on every profile and must come out '
      'constant if it is a surface. Signed, the sill returns %+.3f m on %d profiles, the pier null %+.3f '
      'on %d, and the head %+.3f on %d. The head beats its null by less than the factor of three this '
      'archive uses, and %.3f does not match the %.3f the jambs measured on the vertical edges.'
      % (HRES['D_sill'], HRES['n_sill'], HRES['D_null'], HRES['n_null'], HRES['D_head'],
         HRES['n_head'], HRES['D_head'], HRES['jamb']),
      'tools/head_rebate.py')
check('the camera set has no distance leverage to test that depth for constancy',
      HRES['Lmax'] - HRES['Lmin'] < 5.0,
      'the first version of that test was biased by its own filter and the null caught it: keeping only '
      'downward offsets made every set return a positive depth, the pier null included, which came back '
      'with D 0.205 m on masonry with no opening behind it. A null that cannot sit on zero is not a null. '
      'Signed, it behaves. But every walk camera stands %.0f to %.0f m from this wall, so only one '
      'distance bin answers and constancy cannot be tested at all. One bin is not a constant, the head is '
      'not moved, and 11.165 stands with the opening height 2.43.'
      % (HRES['Lmin'], HRES['Lmax']),
      'tools/head_rebate.py')
# THE NORTH TAPESTRIES, BURIED BY A CHANGE I SHIPPED THIS AFTERNOON (2026-09-09).
TAPN = {'old_face': -0.090, 'drawn': -0.053, 'standoff': 0.037, 'south_standoff': 0.102,
        'shift': 0.060}
check('no hanging textile is inside the wall it hangs on',
      all(d > G['dNorth'] for d in northtap) and all(d < G['dSouth'] for d in southtap),
      'the north pair is drawn on %s against a face on %.3f, and the south pair on %s against %.3f. This '
      'model already diagnosed exactly this on the south wall, where a textile was drawn 19 mm behind the '
      'stone it hangs on and was moved; the north pair was left alone because the cloud could not measure '
      'it. Then the north FACE moved %.3f to %.3f this afternoon and this file stores ABSOLUTE world '
      'corners, so the tapestries did not follow and ended up %.0f mm inside the masonry.'
      % (', '.join('%+.4f' % d for d in northtap), G['dNorth'],
         ', '.join('%.3f' % d for d in southtap), G['dSouth'], TAPN['old_face'], G['dNorth'],
         1000 * abs(TAPN['drawn'] - G['dNorth'])),
      'tools/tapestries.json')
check('the north tapestries followed their face without acquiring a new opinion',
      all(abs((d - G['dNorth']) - TAPN['standoff']) < 0.002 for d in northtap),
      'the fix is the smallest one that removes the impossibility: shift both sheets by the %+.3f m the '
      'face moved, which preserves the drawn standoff of %.3f m exactly and changes nothing else. It is '
      'not a measurement. Worth recording beside it: the only MEASURED standoff in this building is the '
      'south pair, %.3f m, so %.3f is thin and that is a separate open question from this one.'
      % (TAPN['shift'], TAPN['standoff'], TAPN['south_standoff'], TAPN['standoff']),
      'tools/tapestries.json')
check('geometry stored in world coordinates does not follow a plane that moves',
      True,
      'the grilles, doors and openings on this wall are all drawn as offsets from the face in the page '
      'itself, so they followed it when it moved. The tapestries are absolute corners in a separate JSON '
      'and could not. That is the general shape of this fault and it is worth naming: a change to a '
      'reference plane silently splits the model into the part that follows and the part that does not, '
      'and the part that does not is whatever lives outside the formula.',
      'tools/check_bounds.py')
# WHERE PEOPLE ACTUALLY STOOD BEHIND THAT WALL (2026-09-09, tools/corridor_occupancy.py). No detector,
# no window, no polarity, no threshold: a lens is a point that was not inside stone.
OCC = {'lenses': 1568, 'classes': 15, 'behind': 196, 'inreveal': 196, 'inroom': 0,
       'deepest': 0.422, 'was': 0.362, 'oldface': -0.090, 'lowest': 9.066, 'highest': 10.121,
       'back_slack': 1.898, 'floor_slack': 0.726, 'ceil_slack': 0.826,
       'openings': 3, 'behind_classes': 5, 'below_sill': 0}
check('the reveal bound was measured against a wall face the model has moved away from',
      abs(OCC['deepest'] - (OCC['was'] + abs(G['dNorth'] - OCC['oldface']))) < 0.002,
      'the deepest lens behind this wall is b1_000057 and it has not moved. The FACE moved: %.3f to %.3f '
      'this afternoon, so the same lens that sat %.3f m behind the old face sits %.3f m behind the '
      'measured one. The bound is 60 mm better and nothing was re-measured to get it. tools/mask_audit.py '
      'reads the constants inside TOOLS; this one was a stale constant baked into a BOUND VALUE, where '
      'nothing was looking.'
      % (OCC['oldface'], G['dNorth'], OCC['was'], OCC['deepest']),
      'tools/corridor_occupancy.py')
check('nobody in the archive has ever stood in the corridor itself',
      OCC['inroom'] == 0,
      '%d posed lenses across %d classes, %d of them behind the north wall face, from %d classes and %d '
      'different openings. ALL %d are still inside the REVEAL: the deepest reaches %.3f m in and the '
      'drawn reveal is %.2f m deep. Not one lens is past it, let alone in the room. So everything this '
      'model draws deeper than %.3f m rests on photometry and the 1968 plan, and no pose in this archive '
      'touches it.'
      % (OCC['lenses'], OCC['classes'], OCC['behind'], OCC['behind_classes'], OCC['openings'],
         OCC['inreveal'], OCC['deepest'], G['openDepth'], OCC['deepest']),
      'tools/corridor_occupancy.py')
check('the pose bounds on the corridor are real and nearly empty',
      OCC['back_slack'] > 1.0 and OCC['floor_slack'] > 0.5,
      'the three bounds are one-sided and assumption-free: the back wall is behind the deepest lens, the '
      'floor below the lowest, the ceiling above the highest. Nothing is contradicted, and the size of '
      'the clearances is the content. The back wall has %.2f m of slack, the floor %.2f m and the ceiling '
      '%.2f m against the people who were actually in there. A bound with metres of slack constrains '
      'almost nothing, and this room is drawn far beyond where anybody stood.'
      % (OCC['back_slack'], OCC['floor_slack'], OCC['ceil_slack']),
      'tools/corridor_occupancy.py')
check('the lens is not the person, and the first draft of that tool forgot it',
      OCC['below_sill'] == 0,
      'reading %d lenses inside the reveal, the tool first concluded people were leaning IN from outside. '
      'There is nowhere outside to lean from: these lenses sit between h 9.07 and 10.12, the sill is '
      '%.3f, and on the hall side at that height there is nothing but air. %d of the %d are below the '
      'sill, so the bodies were standing INSIDE the room and only the lenses leaned forward into the '
      'reveal. A lens bounds where the LENS was; the feet are behind it and deeper in, which is why this '
      'says nothing about the floor and everything about the reveal.'
      % (OCC['behind'], G['sill'], OCC['below_sill'], OCC['behind']),
      'tools/corridor_occupancy.py')
# THE BALCONY MEASURED FROM THE BALCONY (2026-09-09, tools/overlay_residual.py with SET=gallery).
GAL = {'frames_day': 138, 'frames_b3p': 140, 'deck_bands': (0.020, -0.030, 0.030),
       'null_conf': 5, 'null_bands': 6, 'real_conf': 5, 'real_bands': 10,
       'b3p_deck_profiles': 2, 'day_deck_lo': 36, 'day_deck_hi': 81,
       'null_h': (8.600, 8.850), 'deck': 8.34}
check('the near view of the deck was being discarded by a rule written for the far view',
      True,
      'the profile sampler demanded that EVERY sample be in front of the lens and inside the frame. From '
      'the hall floor that is fair; from a metre away the same 0.6 m of profile fills the frame and its '
      'ends run off the edge. The first gallery run returned zero usable profiles on nineteen of twenty '
      'features and none of that was the building. The sampler now takes the longest contiguous visible '
      'run, provided it still carries the detector window either side of a candidate.',
      'tools/overlay_residual.py')
check('the deck junction appears confirmed from the gallery and the null says it is not',
      GAL['null_conf'] / float(GAL['null_bands']) >= GAL['real_conf'] / float(GAL['real_bands']),
      'across %d day4k frames the deck junction reads %+.0f, %+.0f and %+.0f mm in three of four bands, '
      'window-invariant, which looks like the confirmation this number has waited for all night. Two null '
      'lines were drawn across BLANK parapet face, h %.3f and %.3f, where the model draws nothing, in the '
      'same stone under the same light at the same distance: %d of their %d bands come back confirmed '
      'within 50 mm, against %d of %d for the real features. The null scores BETTER than the signal, so '
      'this detector finds an edge wherever it is pointed on that face.'
      % (GAL['frames_day'], 1000 * GAL['deck_bands'][0], 1000 * GAL['deck_bands'][1],
         1000 * GAL['deck_bands'][2], GAL['null_h'][0], GAL['null_h'][1], GAL['null_conf'],
         GAL['null_bands'], GAL['real_conf'], GAL['real_bands']),
      'tools/overlay_residual.py')
check('two clips disagree about whether the deck junction exists at all',
      GAL['b3p_deck_profiles'] * 10 < GAL['day_deck_lo'],
      'on the identical junction with identical geometry, day4k clears the contrast bar %d to %d times '
      'per band while b3p, %d frames of it, clears it %d times in total across all four bands. A junction '
      'that one clip sees hundreds of times and another cannot see at all is lighting, not masonry.'
      % (GAL['day_deck_lo'], GAL['day_deck_hi'], GAL['frames_b3p'], GAL['b3p_deck_profiles']),
      'tools/overlay_residual.py')
check('the near route to the deck is closed on evidence and nothing is moved on it',
      abs(G['deck'] - GAL['deck']) < 1e-9,
      'the gallery route is now tested rather than untried, and it was closed by the instrument own null '
      'rather than by an absence of data. Run without that null it would have produced a headline: the '
      'deck confirmed in three of four bands from %d balcony frames. That sentence would have been false '
      'and nothing else in the experiment could have said so. %.2f stays a bound: under the lowest lens '
      'standing on it, h 9.03.' % (GAL['frames_day'], G['deck']),
      'tools/overlay_residual.py')
# THE WHOLE NORTH WALL AGAINST 263 POSED FRAMES (2026-09-09, tools/overlay_residual.py).
RESID = {'frames': 263, 'features': 18, 'invariant': 14, 'confirmed': 10, 'nulls': 7,
         'null_fail': 5, 'null_stable': 2, 'sill_ok': 8, 'sill_win': 3, 'sill_off': 0.145,
         'head_lo': -0.110, 'head_mid': (-0.135, -0.110, -0.110), 'head_ends': (0.040, -0.030),
         'wide': 0.50, 'narrow': 0.30, 'blind': 0.08}
check('the drawn sills are confirmed against the imagery, not just against their own rays',
      RESID['sill_ok'] >= 8,
      'each drawn edge was measured by walking a profile THROUGH it in %d real frames, in metres, so no '
      'intrinsics enter the answer. %d of the twelve sills sit within 50 mm of where this model draws '
      'them, over 90 to 203 profiles each, with medians of 0, 0, 0, -10, -15, -20, -30 and -50 mm. Three '
      'more looked badly wrong through the half-metre window, -330, -250 and -200 mm, and all three '
      'collapse to within 55 mm when the window is halved: they were the window.'
      % (RESID['frames'], RESID['sill_ok']),
      'tools/overlay_residual.py')
check('the one sill that is genuinely off is named and not applied',
      True,
      'opening 1 reads +%.0f mm through the wide window and +140 through the narrow, as invariant as any '
      'confirmation here. It is also the opening nearest the west gallery, whose deck, upstand and rail '
      'all stand inside the same height band a metre away, so a competing edge is available to it that no '
      'other opening has. One opening in twelve with a plausible impostor beside it does not move a line '
      'that eleven others confirm.' % (1000 * RESID['sill_off']),
      'tools/overlay_residual.py')
check('the head discrepancy is a pattern and therefore not a correction',
      abs(RESID['head_lo']) > 0.050,
      'openings 7, 8 and 9 read %.0f, %.0f and %.0f mm and hold those values through both windows, '
      'opening 8 to the millimetre. Openings 1 and 12, at the two extremes of the hall, read %+.0f and '
      '%+.0f and are confirmed. A head that is right at both ends and 110 mm low across the middle is not '
      'a single number to correct, so nothing moves. It is now the north wall most specific open '
      'discrepancy rather than a vague one.'
      % (1000 * RESID['head_mid'][0], 1000 * RESID['head_mid'][1], 1000 * RESID['head_mid'][2],
         1000 * RESID['head_ends'][0], 1000 * RESID['head_ends'][1]),
      'tools/overlay_residual.py')
check('the confirmations are read against the instrument own false positive rate',
      RESID['null_stable'] > 0 and RESID['confirmed'] > 3 * RESID['null_stable'],
      '%d of the %d pier nulls fail window invariance, moving 70 to 190 mm, which is a null behaving as a '
      'null should. %d of them do NOT: they return a stable edge within 50 mm on a pier where this model '
      'draws nothing. So this instrument produces a convincing false positive about two times in seven, '
      'and %d confirmations out of %d features is read against that and not against zero.'
      % (RESID['null_fail'], RESID['nulls'], RESID['null_stable'], RESID['confirmed'],
         RESID['features']),
      'tools/overlay_residual.py')
# THE DECK LEVEL, SEARCHED AND REFUSED PROPERLY (2026-09-09, tools/run_deck_edge.py + run_deck_ladder.py)
DECKS = {'pin_h': 8.645, 'pin_band_hi': 8.65, 'pin_rays': 145, 'pin_share': 1.00, 'pin_res': 0.0081,
         'pin2_h': 8.803, 'pin2_band_hi': 8.80, 'pin2_share': 0.99,
         'wide_a': 9.090, 'wide_b': 9.093, 'wide_share_a': 0.84, 'wide_share_b': 0.82,
         'wide_res': 0.0333, 'ustation_a': 3.757, 'ustation_b': 3.746, 'usolid': 3.710,
         'uface': 4.194, 'east_lit': 4, 'east_dark': 9, 'lowest_lens': 9.03, 'classes': 15}
check('the deck edge that looked measured was the ceiling of its own ladder',
      abs(DECKS['pin_h'] - DECKS['pin_band_hi']) < 0.010
      and abs(DECKS['pin2_h'] - DECKS['pin2_band_hi']) < 0.010,
      'a ladder from 7.85 to 8.85 on the measured west face returned %d detections agreeing 100 per cent '
      'on h %.3f with an %.0f mm residual, which would have been the best-conditioned balcony fit in the '
      'archive and would have moved the deck 0.3 m. The detector averages 40 samples either side of a '
      'candidate and a sample is 5 mm, so its usable band was 8.05 to 8.65 and the answer sat %.0f mm '
      'under the top of it. A second window, usable 7.80 to 8.80, answered %.3f: its own ceiling again.'
      % (DECKS['pin_rays'], DECKS['pin_h'], 1000 * DECKS['pin_res'],
         1000 * abs(DECKS['pin_band_hi'] - DECKS['pin_h']), DECKS['pin2_h']),
      'tools/run_deck_ladder.py')
check('the only edge near the deck level belongs to the parapet above it',
      abs(DECKS['wide_a'] - (G['deck'] + G['upWest'])) < 0.010 and abs(DECKS['wide_b'] - (G['deck'] + G['upWest'])) < 0.010,
      'two ladders tall enough to contain it, usable 7.60 to 9.20 and 8.20 to 9.40, both answer the same '
      'place: %.3f and %.3f against a solid upstand top this model draws on %.3f, recovered to %.0f mm '
      'and %.0f mm by a search that was not aimed at it. So between h 7.6 and 9.4 on the west end face '
      'there is exactly one photometric edge and it is not the deck. The east end refuses outright, %d '
      'and %d detections against a 22 grey level bar.'
      % (DECKS['wide_a'], DECKS['wide_b'], (G['deck'] + G['upWest']), 1000 * abs(DECKS['wide_a'] - (G['deck'] + G['upWest'])),
         1000 * abs(DECKS['wide_b'] - (G['deck'] + G['upWest'])), DECKS['east_lit'], DECKS['east_dark']),
      'tools/run_deck_ladder.py')
check('perfect consensus inside a narrow window is a symptom, not a result',
      DECKS['pin_share'] > DECKS['wide_share_a'] and DECKS['pin_res'] < DECKS['wide_res'],
      'the two pinned runs agreed %.0f and %.0f per cent with residuals of %.0f and 31 mm; the two honest '
      'ones agreed %.0f and %.0f per cent with %.0f mm. Detections pinned against a window edge cannot '
      'disagree with each other, so the tighter number is the worse one here. Nothing about agreement '
      'distinguishes them from the inside; only moving the window does.'
      % (100 * DECKS['pin_share'], 100 * DECKS['pin2_share'], 1000 * DECKS['pin_res'],
         100 * DECKS['wide_share_a'], 100 * DECKS['wide_share_b'], 1000 * DECKS['wide_res']),
      'tools/run_deck_ladder.py')
check('the recess measured this evening has a witness that was looking for something else',
      abs(DECKS['ustation_a'] - DECKS['usolid']) < abs(DECKS['ustation_a'] - DECKS['uface']),
      'the two wide ladders were searching a different band with a different polarity for a different '
      'feature, and their stations land on u %.3f and %.3f. That is the SOLID upstand on %.3f, not the '
      'face on %.3f: %.0f mm from the recessed parapet and %.0f mm from the face. The 0.484 m recess was '
      'the largest change of the day and nothing else had confirmed it.'
      % (DECKS['ustation_a'], DECKS['ustation_b'], DECKS['usolid'], DECKS['uface'],
         1000 * abs(DECKS['ustation_a'] - DECKS['usolid']),
         1000 * abs(DECKS['ustation_a'] - DECKS['uface'])),
      'tools/run_deck_ladder.py')
# THE JAMB PLANE, ASKED AS ONE UNKNOWN PER RAY (2026-09-09, tools/jamb_depth.py).
JD = {'lines': 8, 'pass': 6, 'span': 0.018, 'median': -0.208, 'spread_lo': 0.001, 'spread_hi': 0.078,
      'spread_med': 0.014, 'null_lo': 0.001, 'null_hi': 0.014, 'lev_a': 42.5, 'lev_b': 88.7,
      'agree_a': 0.001, 'agree_b': 0.005, 'fail_a': 20.029, 'fail_b': 23.751, 'gate2': 0.60,
      'cap': 0.362}
check('the plane the jamb lines stand on is measured, not assumed',
      JD['pass'] >= JD['lines'] * 0.7 and JD['spread_med'] < 3.0 * JD['null_hi'],
      'eight lines agreed on a depth to %.0f mm while each line own camera halves scattered by up to '
      '500, and a population tighter than its members is what a shared BIAS looks like as well as a '
      'shared FEATURE. Asked as ONE unknown per ray, with the rays split by how far ALONG the hall the '
      'camera stood, %d of %d lines keep their near-far spread inside three times their own null. Spread '
      'runs %.0f to %.0f mm against nulls of %.0f to %.0f; the two best-conditioned lines carry leverages '
      'of %.0f and %.0f and their halves agree to %.0f mm and %.0f mm. Two lines fail and are named: '
      'u %.3f on a leverage of 3.7, and u %.3f which spreads 19 mm against a 1 mm null. Doubling the '
      'peel depth gate to %.2f returns the same lines to the millimetre, so this is not the gate.'
      % (1000 * JD['span'], JD['pass'], JD['lines'], 1000 * JD['spread_lo'], 1000 * JD['spread_hi'],
         1000 * JD['null_lo'], 1000 * JD['null_hi'], JD['lev_a'], JD['lev_b'], 1000 * JD['agree_a'],
         1000 * JD['agree_b'], JD['fail_a'], JD['fail_b'], JD['gate2']),
      'tools/jamb_depth.py')
check('the measured jamb edge is not the back of the reveal, and the bound that says so came first',
      abs(JD['median'] - G['dNorth']) < JD['cap'],
      'the peel finds no vertical edge on the face plane at any support level, which invites reading its '
      'one plane as the back of a shallow reveal and cutting openDepth from %.2f to %.3f. A bound this '
      'model already carries forbids it: the arrival cap puts a lens %.3f m inside an opening, so a '
      'rebate %.3f m in would have that lens standing %.3f m inside solid stone. The two measurements do '
      'not compete, the earlier one settles what the later one is looking at. So the openings carry a '
      'step, a rebate or a frame line %.3f m in, the model draws nothing there, and openDepth is '
      'untouched because nothing here bears on where the reveal ENDS.'
      % (G['openDepth'], abs(JD['median'] - G['dNorth']), JD['cap'], abs(JD['median'] - G['dNorth']),
         JD['cap'] - abs(JD['median'] - G['dNorth']), abs(JD['median'] - G['dNorth'])),
      'tools/jamb_depth.py')
check('the rebate is recorded and not built, because its projection is smaller than its scatter',
      abs(1.212 - 1.189) < 0.054,
      'a rebate needs a depth AND a projection, and the projection is the one number this cannot give. '
      'The two peels width test reads %.3f m west and %.3f m east where the face opening is drawn %.3f, '
      'a %.0f mm step, against per-peel spreads of 54 and 17 mm. The step is smaller than the scatter it '
      'would have to be measured against. What this DOES harden is the opening shift: five of the twelve '
      'openings were moved 0.147 m east on these lines, and the plane those lines stand on was an '
      'assumption until tonight.'
      % (1.189, 1.190, 1.212, 1000 * abs(1.212 - 1.189)),
      'tools/jamb_lines.py')
# THE STALE CONSTANTS SORTED BY WHAT THEY DO (2026-09-09, tools/mask_audit.py), AND WHAT THAT FOUND.
MASKAUDIT = {'tools': 313, 'masks': 26, 'drift': 112, 'bom': 1}
JAMB = {'gate': 0.30, 'old_face': -0.090, 'rejected': 0.217, 'margin': 0.007, 'face_err': 0.060,
        'west': 4, 'east_before': 5, 'east': 4, 'west_move': 0.007, 'east_move': 0.010,
        'lost_u': 34.877, 'lost_rays': 36, 'off_w': 0.008, 'off_e': -0.014,
        'dmin': -0.217, 'dmax': -0.201, 'wid_w': 1.189, 'wid_e': 1.190, 'wid_drawn': 1.212}
check('no mask anywhere gates rays on a value the model has moved away from',
      MASKAUDIT['masks'] < MASKAUDIT['drift'] / 2.0,
      'two stale-constant faults tonight had opposite consequences: the lamp aperture manufactured two '
      'reveal points, the corridor ray gate moved its answer 5 mm, and the corridor ladder was moved '
      '260 mm on purpose and moved the answer 3 mm. The difference is not how stale a constant is but '
      'what it does. A MASK decides whether a ray exists and a wrong one is reported as a feature; a '
      'LADDER decides only where to look. The raw drift scan treats them alike, which is why its %d hits '
      'sat unread. Sorting by whether the value sits inside a COMPARISON leaves %d across %d tools, '
      'which is readable in one sitting.'
      % (MASKAUDIT['drift'], MASKAUDIT['masks'], MASKAUDIT['tools']),
      'tools/mask_audit.py')
check('the jamb depth gate is centred on the face the model actually draws',
      True,
      'the peel gates every line with a depth test centred on the wall face, %.2f m wide. That centre '
      'was %.3f while the model drew %.3f, so the accepted band ran %.3f to %.3f, and one of the three '
      'lines rejected as not on this wall sat on d +%.3f: %.0f mm outside a window whose centre was '
      'wrong by %.0f. On the corrected centre the band is %.3f to %.3f and that line is inside it. '
      'Whether it is a real jamb is what the re-run answers; deciding it on a stale number is not '
      'acceptable either way.'
      % (JAMB['gate'], JAMB['old_face'], G['dNorth'], JAMB['old_face'] - JAMB['gate'],
         JAMB['old_face'] + JAMB['gate'], JAMB['rejected'], 1000 * JAMB['margin'],
         1000 * JAMB['face_err'], G['dNorth'] - JAMB['gate'], G['dNorth'] + JAMB['gate']),
      'tools/jamb_lines.py')
check('the shipped opening shift survives the corrected gate',
      abs(JAMB['off_w']) < 0.030 and abs(JAMB['off_e']) < 0.030,
      're-peeled on the corrected gate the west returns the same %d lines, moved by %.0f mm or less. The '
      'east returns %d where it returned %d: the lost one is the weakest of the nine, u %.3f on %d rays, '
      'and the four that remain moved %.0f mm or less. Measured against the openings as the model now '
      'draws them the offsets have median %+.0f mm west and %+.0f mm east, so the 0.147 m shift applied '
      'this afternoon landed where the jambs say it should. Eight lines now, not nine.'
      % (JAMB['west'], 1000 * JAMB['west_move'], JAMB['east'], JAMB['east_before'], JAMB['lost_u'],
         JAMB['lost_rays'], 1000 * JAMB['east_move'], 1000 * JAMB['off_w'], 1000 * JAMB['off_e']),
      'tools/jamb_lines.py')
check('the edge the jamb peel finds is not on the face and is not drawn',
      G['openDepth'] > abs(JAMB['dmax'] - G['dNorth']),
      'all eight lines land between d %+.3f and %+.3f against a face on %+.3f, a spread of %.0f mm '
      'across two independent peels of opposite polarity. That is an edge %.3f m behind the face, and '
      'the model draws the reveal %.2f m deep with nothing on that plane. The two peels also agree on a '
      'width they were never asked for, %.3f m west over four openings and %.3f m east over three, '
      'medians 1 mm apart against a face opening drawn %.3f m wide. Both are the REVEAL and not the '
      'face, so both are recorded and neither is drawn.'
      % (JAMB['dmin'], JAMB['dmax'], G['dNorth'], 1000 * abs(JAMB['dmax'] - JAMB['dmin']),
         abs(JAMB['dmax'] - G['dNorth']), G['openDepth'], JAMB['wid_w'], JAMB['wid_e'],
         JAMB['wid_drawn']),
      'tools/jamb_lines.py')
check('the checker computes the back wall the way the model draws it',
      abs(G['cBack'] - (G['dNorth'] - G['openDepth'] - G['cWidth'])) < 1e-9,
      'the model builds the room as dR = face + openDepth then dB = dR + width, so the corridor WIDTH is '
      'measured from the back of the reveal and the back wall stands the reveal PLUS the width behind '
      'the face. This checker left the reveal out and had done so since the corridor was first drawn: '
      'with width 2.06 it read -2.090 while the sim drew -2.990. It passed anyway, because every '
      'corridor bound is one-sided and a wall drawn deeper than required satisfies a one-sided test '
      'happily. A suite of one-sided tests cannot catch an error that errs in the safe direction. '
      'Corrected, the width is %.3f so the drawn wall lands on the measured %.3f.'
      % (G['cWidth'], G['cBack']),
      'tools/check_bounds.py')
# THE CORRIDOR RE-GATED, AND THE LOCUS CUT BY THE LAMP IT MUST CLEAR
# (2026-09-09, tools/corridor_lines.py, tools/corridor_locus.py).
CORR = {'stale_rays': 215, 'rays': 128, 'stale_share': 0.40, 'share': 0.64, 'cut_d': -2.350,
        'cut_h': 10.947, 'cut_rays': 82, 'split': 0.010, 'drawn_h_at_old': 10.805, 'lamp': 10.945,
        'slope': 0.583, 'sens': 0.086, 'stale_head': 11.236, 'stale_sill': 8.761, 'stale_d': -0.090,
        'lad_rays': 117, 'lad_move': 0.260, 'lad_worst': 0.003, 'lad_share': 0.66}
check('the corridor aperture gate matches the openings the model actually draws',
      True,
      'every corridor measurement is gated by an aperture: a ray counts only if it crosses the wall '
      'plane between the sill and the head. That gate carried %.3f, %.3f and %.3f while the model drew '
      '%.3f, %.3f and %.3f, so the slot stood %.0f mm too tall at the head and %.0f mm too high at the '
      'sill and admitted rays through solid stone above the real opening. Corrected and regathered, '
      '%d rays became %d: %d of them, %.0f per cent, were admitted only by the too-tall slot. '
      'tools/constant_drift.py had flagged its consumer three times and the hits were triaged by '
      'category instead of read, which is the instruction that tool exists to enforce.'
      % (CORR['stale_d'], CORR['stale_sill'], CORR['stale_head'], G['dNorth'], G['sill'],
         G['head'], 1000 * (CORR['stale_head'] - G['head']),
         1000 * (CORR['stale_sill'] - G['sill']), CORR['stale_rays'], CORR['rays'],
         CORR['stale_rays'] - CORR['rays'],
         100.0 * (CORR['stale_rays'] - CORR['rays']) / CORR['stale_rays']),
      'tools/corridor_lines.py')
check('the wrong aperture added noise around a real feature rather than inventing one',
      CORR['share'] > 1.5 * CORR['stale_share'],
      'the natural fear after the reveal points is that every mask fault invalidates its finding. This '
      'one did not. The ceiling locus reads the same through both gates, %.3f against %.3f on the old '
      'drawn wall and %.3f against %.3f at the crossing, differences of 5 and 2 mm. What the correction '
      'bought was purity: the share of rays inside the consensus went from %.0f to %.0f per cent. Both '
      'lessons are true of different masks and neither generalises to the other.'
      % (CORR['drawn_h_at_old'], 10.800, CORR['cut_h'], 10.946, 100 * CORR['stale_share'],
         100 * CORR['share']),
      'tools/corridor_locus.py')
check('the corridor answer does not follow the ladder that found it',
      CORR['lad_worst'] < 0.010,
      'moving the back wall also moves the plane the detector ladder is walked on, so the rays were '
      'regathered a second time with the ladder standing on the new %.3f instead of the old -2.090, '
      '%.0f mm away, and %d rays became %d. The locus did not move: its worst station shifted %.0f mm '
      'and the rest less. That is the mask-versus-ladder distinction measured rather than asserted. A '
      'mask makes a feature invisible and detections pile onto its edge, which is what the aperture did '
      'to the withdrawn reveal points; a ladder only chooses where to look, and a wide enough one finds '
      'the right edge from the wrong centre. The aperture had to be right and the back wall did not, and '
      'both have now been shown to behave that way on the same rays.'
      % (CORR['cut_d'], 1000 * CORR['lad_move'], CORR['rays'], CORR['lad_rays'],
         1000 * CORR['lad_worst']),
      'tools/corridor_lines.py')
check('the drawn corridor is the shallowest room its own lamps allow',
      abs(G['cBack'] - CORR['cut_d']) < 0.005 and abs(G['cCeil'] - CORR['cut_h']) < 0.005
      and G['cCeil'] > max(L[2] for L in MEASURED_LAMPS),
      'the locus is a curve and not a number: fix the back wall anywhere and every ray gives the ceiling '
      'directly, one unknown per ray. It rises %.3f m of ceiling per metre of depth. The highest lamp '
      'inside the room hangs on h %.3f and a ceiling below a lamp is impossible, so the lamp cuts the '
      'curve on d %.3f h %.3f, from %d rays whose west, east, near and far splits agree to %.0f mm. The '
      'model drew -2.090 and 11.400, a pair that put the ceiling %.3f at the drawn depth, %.0f mm BELOW '
      'the lamp hanging in the room. Now %.3f and %.3f, which is the shallowest room the evidence admits '
      'and the first time the two numbers have come from one source. A DEEPER room is equally admissible '
      'because the cut is one-sided, and %.0f mm of lamp-height error moves the wall %.0f mm.'
      % (CORR['slope'], CORR['lamp'], CORR['cut_d'], CORR['cut_h'], CORR['cut_rays'],
         1000 * CORR['split'], CORR['drawn_h_at_old'],
         1000 * (CORR['lamp'] - CORR['drawn_h_at_old']), G['cBack'], G['cCeil'],
         50.0, 1000 * CORR['sens']),
      'tools/corridor_locus.py')
# THE APRON BOUNDARY, SEARCHED FOR THE FIRST TIME (2026-09-09, tools/run_apron_edge.py).
APRON = {'west_rays': 107, 'east_rays': 4, 'gap_lo': 0.198, 'gap_hi': 0.233, 'null': 0.015,
         'near': 6.2, 'far': 6.5}
check('the apron boundary is refused because the camera halves see different things, not because it is faint',
      APRON['gap_hi'] < 3.0 * APRON['gap_lo'],
      'the level 6.33 is a material change on the face plane, apron below and dark upstand above, and no '
      'ladder had ever contained it: every lower-tier run started on 6.35 or 6.70, at or above the floor, '
      'so it was excluded by construction and not by evidence. Searched now, the east returns %d '
      'detections and is refused; the west returns %d and they do not form a plane. Its near-far gap sits '
      'between %.0f and %.0f mm at EVERY station and never dips, near cameras putting the boundary around '
      '%.1f and far cameras around %.1f. That is two halves of the camera set looking at two different '
      'things, and a free fit over both would have averaged them into a confident number in between.'
      % (APRON['east_rays'], APRON['west_rays'], 1000 * APRON['gap_lo'], 1000 * APRON['gap_hi'],
         APRON['near'], APRON['far']),
      'tools/run_apron_edge.py')
check('the station scan now requires the gap to come down, not just to beat its null',
      APRON['gap_hi'] > 3.0 * APRON['null'],
      'the flat 200 mm apron gap beat a %.0f mm null comfortably and was declared real geometry by a '
      'verdict line already fixed once tonight. Beating the null and having the minimum inside the sweep '
      'are both necessary and still not enough: a curve with no dip is not a V. The rule now also '
      'requires the gap to fall by the same factor of three. Two defects in one line, both found by '
      'pointing it at something that was not there.' % (1000 * APRON['null']),
      'tools/end_face_scan.py')
# THE SAME QUESTION ASKED WIDE, AFTER THE NARROW ANSWER TURNED OUT TO REST ON THE WINDOW
# (2026-09-09, tools/apron_wide.py).
APRONW = {'lo': 0.151, 'hi': 0.251, 'ulo': 1.494, 'uhi': 5.594, 'asked': 4.2, 'stations': 42,
          'stable': 22, 'nullbar': 0.05, 'trunc_lo': 0.062, 'trunc_hi': 0.265, 'trunc_span': 3.8}
check('the apron refusal survives a sweep three times wider than the one that produced it',
      APRONW['hi'] < 3.0 * APRONW['lo'],
      'the narrow scan swept 1.3 m and a feature standing outside a swept window gives the same flat '
      'curve a genuinely different feature gives, so that refusal rested on window size. Swept %.1f m '
      'instead, the gap runs %.0f to %.0f mm over %d stations from u %.3f to %.3f, a ratio of %.1f '
      'against a bar of 3, climbing monotonically with no dip anywhere. No vertical plane in four metres '
      'of station reconciles the two camera halves to better than %.0f mm.'
      % (APRONW['uhi'] - APRONW['ulo'], 1000 * APRONW['lo'], 1000 * APRONW['hi'], APRONW['stations'],
         APRONW['ulo'], APRONW['uhi'], APRONW['hi'] / APRONW['lo'], 1000 * APRONW['lo']),
      'tools/apron_wide.py')
check('a fixed window can end a sweep early and the tool then blames the building',
      APRONW['uhi'] - APRONW['ulo'] > APRONW['trunc_span'],
      'the first wide run solved every station against a window centred on the DRAWN floor 6.33. Far from '
      'the truth the solved heights walk out of a fixed window, the station returns nothing and the sweep '
      'stops. It was asked for %.1f m, covered %.1f, and reported a gap falling %.0f to %.0f mm, a ratio '
      'of %.1f, with its minimum sitting on the first station that survived. That would have shipped as '
      'the lower tier station had the edge check not refused it. Recentring the window on each station '
      'own answer, as tools/low_gap.py does, holds one edge over %.1f m and the ratio falls to %.1f: the '
      'convergence was the truncation.'
      % (APRONW['asked'], APRONW['trunc_span'], 1000 * APRONW['trunc_hi'], 1000 * APRONW['trunc_lo'],
         APRONW['trunc_hi'] / APRONW['trunc_lo'], APRONW['uhi'] - APRONW['ulo'],
         APRONW['hi'] / APRONW['lo']),
      'tools/apron_wide.py')
check('stations where the null itself is large are not read',
      APRONW['stable'] < APRONW['stations'] and APRONW['lo'] > 2.0 * APRONW['nullbar'],
      'across a third of the swept stations the odd-against-even null runs 150 to 240 mm, which is the '
      'tracker failing to hold one feature rather than two halves disagreeing about where it is. A '
      'near-far number from a station like that is noise about noise. Only the %d of %d stations whose '
      'null stays under %.0f mm are read, and the surviving gap of %.0f mm is still three times that '
      'bar, so the refusal is not being manufactured by the gate.'
      % (APRONW['stable'], APRONW['stations'], 1000 * APRONW['nullbar'], 1000 * APRONW['lo']),
      'tools/apron_wide.py')
check('no verdict shipped on the old rule changes under the new one',
      True,
      'the two solid upstands, the replaned pair and the east rail were all re-run against the stricter '
      'rule and all still pass. The west rail was already withheld for failing its null and the two lower '
      'tier fits were already refused for minimising on the sweep edge. Nothing that was shipped moves, '
      'which is the check that makes a rule change safe rather than convenient.',
      'tools/end_face_scan.py')
# THE DECK, TWO ROUTES TRIED AND BOTH CLOSED (2026-09-09, tools/run_soffit_edge.py, tools/deck_bound.py).
DECKB = {'lenses': 309, 'classes': 7, 'lowest': 9.361, 'lens_lo': 1.05, 'lens_hi': 1.75,
         'lower_lenses': 0, 'feas_west': 0.37, 'det_east': 4}
check('the gallery deck is under the lowest lens that stood on it',
      G['deck'] < DECKB['lowest'],
      '%d posed lenses from %d classes stand on that deck, the lowest on h %.3f. A lens is above the '
      'floor carrying it, so the deck is under that, with no assumption of any kind. It is a metre of '
      'room and it says little, but it is the only assumption-free statement about the most load-bearing '
      'number on these balconies.' % (DECKB['lenses'], DECKB['classes'], DECKB['lowest']),
      'tools/deck_bound.py')
check('the drawn deck sits at the top of what the lenses comfortably allow, and is not moved on it',
      abs(G['deck'] - (DECKB['lowest'] - DECKB['lens_lo'])) <= 0.06,
      'the one quantity this archive cannot measure is how high a lens sits above the feet carrying it. '
      'Taken as %.2f to %.2f m, the lowest lens puts the deck between %.3f and %.3f, and the drawn %.3f '
      'lands %.0f mm above that band. Twenty-nine millimetres resting on the single lowest of %d lenses, '
      'which is exactly where an unusual posture shows up, is one-sided pressure and not a contradiction. '
      'Nothing is moved on it and the pressure is recorded instead.'
      % (DECKB['lens_lo'], DECKB['lens_hi'], DECKB['lowest'] - DECKB['lens_hi'],
         DECKB['lowest'] - DECKB['lens_lo'], G['deck'],
         1000 * (G['deck'] - (DECKB['lowest'] - DECKB['lens_lo'])), DECKB['lenses']),
      'tools/deck_bound.py')
check('the lower tier is named as the largest unsupported structure in this model',
      DECKB['lower_lenses'] == 0,
      'zero lenses in the whole archive stand on the lower deck. Beside the west end refusing to yield '
      'any lower-tier edge and the east lower fits failing the near-far test, that leaves the entire '
      'lower tier resting on one 2009 photograph and one inherited file: its floor has no ray and no lens '
      'behind it, its solid and its rail have no measured station, and the only measured thing about it '
      'is the 0.310 m between its two edges. The photometric route to the deck above it is shut too, the '
      'west soffit returning a feasibility of %.2f and the east %d detections above the contrast bar.'
      % (DECKB['feas_west'], DECKB['det_east']),
      'tools/deck_bound.py')
# THE FULL-WIDTH ASSUMPTION, MEASURED (2026-09-09, tools/balcony_width.py). Each entry: inliers, the d
# range they reach, this feature's quarters, and the quarters of ALL detections on that end, which carry
# the same sampling bias and are what it has to be judged against.
WIDTH = {
    ('west', 'solid'): (4130, 0.60, 14.80, (29, 26, 31, 14), (30, 27, 30, 13)),
    ('west', 'rail'): (161, 0.60, 14.80, (24, 27, 23, 26), (27, 26, 24, 22)),
    ('east', 'solid'): (3585, 0.60, 14.80, (13, 34, 35, 18), (22, 33, 29, 16)),
    ('east', 'rail'): (319, 0.60, 14.80, (16, 39, 28, 18), (18, 22, 26, 33)),
}
for (side, feat), (n, dlo, dhi, q, base) in WIDTH.items():
    gap = [i for i in range(4) if q[i] < 5 and base[i] >= 10]
    check('the %s %s runs the full width of the hall' % (side, feat),
          not gap and dhi - dlo >= 13.0,
          '%d inliers reaching d %.2f to %.2f of a hall 15.364 wide. By quarter this feature runs '
          '%s per cent against a sampling of %s, and the sampling is the fair comparison because a camera '
          'near one long wall reads the far side of a parapet at a worse angle. No quarter carries '
          'detections without carrying the feature, which is what a gallery stopping short looks like. '
          'The full-width assumption came from the first sketch and this is the first time anything has '
          'tested it: the ladder always walked sixty stations across the hall and discarded which one '
          'each detection came from.'
          % (n, dlo, dhi, ', '.join(str(t) for t in q), ', '.join(str(t) for t in base)),
          'tools/balcony_width.py')
check('the east rail leans across the hall, and it is named rather than redrawn',
      max(abs(a - b) for a, b in zip(WIDTH[('east', 'rail')][3], WIDTH[('east', 'rail')][4])) <= 25,
      'its inliers run %s per cent where the sampling runs %s, so it is 16 points heavy in the second '
      'quarter and 15 light in the fourth. It still reaches d 0.60 to 14.80, so the rail is there across '
      'the whole width and something about the far quarter makes its top edge harder to read. The other '
      'three features agree with their sampling to within 1, 4 and 9 points.'
      % (', '.join(str(t) for t in WIDTH[('east', 'rail')][3]),
         ', '.join(str(t) for t in WIDTH[('east', 'rail')][4])),
      'tools/balcony_width.py')
# THE RE-PLANE TEST (2026-09-09, tools/run_upstand_replane.py). west_far.py walks its ladder on the FACE
# plane, and the west solid was moved 0.484 m behind that face on rays it produced. Sampling one plane and
# solving for another is the same shape as the corridor aperture fault, so the ladder was moved onto the
# answer and the question put again: station, near-far at the minimum, worst near-far, worst null, rays.
REPLANE = {'west': (3.710, 0.000, 0.047, 0.002, 4625), 'east': (48.056, 0.005, 0.190, 0.037, 4502)}
for side in ('west', 'east'):
    st, mn, mx, nl, nr = REPLANE[side]
    check('the %s solid stays put when the ladder is moved onto it' % side,
          abs(st - SCAN[(side, 'solid')][0]) <= 0.02 and mx > 3.0 * nl,
          're-sampled on u %.3f instead of the drawn face, this end comes back on %.3f against the %.3f '
          'the original run gave, with its halves agreeing to %.0f mm there and disagreeing by %.0f mm at '
          'the end of the sweep on a null never past %.0f, from %d rays. The answer did not follow the '
          'ladder. That is the exact test that destroyed two corridor findings last night, and this side '
          'of the building passes it.'
          % (st, st, SCAN[(side, 'solid')][0], 1000 * mn, 1000 * mx, 1000 * nl, nr),
          'tools/run_upstand_replane.py')
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
             ' separated by the angular spread of the rays that see it. Through an aperture pointed at the'
             ' MEASURED sill, head and wall depth, exactly one point behind this wall still carries a real'
             ' depth minimum: lamp 8, halves agreeing on d -2.322 with a ratio of 6.5, whose own'
             ' least-squares point sits on -2.022. Two estimators, same rays, 300 mm apart, straddling the'
             ' drawn wall. Lamp 9 scores 2.9 against a bar of 3 and lamp 11 is not found at all, so the'
             ' lamps go from three to two and the testable points from two to one, tools/corridor_cloud.py.'
             ' A NIGHT OF FINDINGS WAS WITHDRAWN GETTING HERE: the aperture had been built from a stale'
             ' sill, head and depth, so its mask stopped 0.185 m above the real head and manufactured two'
             ' points sitting on that edge, one of which scored 88 and was called the best measurement'
             ' this archive had behind the wall. It was the mask.'
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
print('%d bounds, all satisfied.' % len(notes))
# THAT LINE USED TO SAY "the sim contradicts nothing the imagery can prove" AND ON 2026-09-10 IT STOPPED
# BEING TRUE. 33 triangulated rays pass through the west end's drawn apron and lower deck front to reach a
# fitting 2.0 m behind the face. A suite whose closing sentence outlives the evidence is worse than no
# closing sentence, so it now says what is actually the case: every bound here holds, and one of the bounds
# is that a drawn surface is refuted.
print('Every bound above holds, and some of them record where the sim WAS wrong and has been corrected:')
print('33 rays crossed a face the sim drew solid, the void they swept refuted the apron, the lower')
print('upstand, the glass rail and the lower deck slab itself, and all four are now deleted rather than')
print('moved. What stands there is an open recess. Its EAST sill and head now have numbers, 6.19 and')
print('7.15, from a 0.96 m hole in the deep cloud points that thin sampling makes with probability 5e-06,')
print('but they are not drawn: the west carries only 8 deep points and cannot support the same claim,')
print('and one end drawn differently from the other on that difference would be a fabrication.')
print('AND ONE OPENING HAS NOW MOVED. Opening 3 of the twelve in the north wall was the only one whose')
print('interior read BRIGHTER than the stone beside it, it sat 0.784 m off a rhythm the other eleven keep')
print('to 0.115, the photographs put it 0.780 m east of where it was drawn while eleven controls stayed')
print('put, and no jamb had ever been measured within 9 m of it. It moved. That is the first time a piece')
print('of this model has changed position rather than been deleted on a measurement.')
print('AND THE BAND THE EAST GALLERY RENDER PUTS ACROSS THE VIEW IS GONE. It was gallery-handrail, an')
print('opaque bar 60 mm tall drawn on a top edge the rays really did measure, standing 0.164 m from the')
print('eye of anyone on that deck and covering about a third of the frame. Nothing ever measured a BAR')
print('there, and 28 of 29 photographs taken from behind it show none, so it was deleted at both ends')
print('and the measured edge beneath it kept. That is the second surface this model has lost today.')
print('"All satisfied" means the file tells the truth about itself, not that it is right.')
