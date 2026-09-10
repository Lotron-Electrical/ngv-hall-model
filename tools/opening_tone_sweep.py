"""THE CORRIDOR'S TONE THROUGH EVERY OPENING THE HALL-FLOOR CAMERAS SEE WHOLE (2026-09-10, after tools/opening_tone.py).

opening_tone.py compared two frames and both failed their wall control (night wall 36, a day polygon in flare). This
is the same measurement over every posed frame that sees a whole opening, per class, so the claim carries a spread.

THE RULE, FIXED BEFORE THE RUN.
  Pairs. For each posed frame in night, walk and day4k and each of the twelve openings: the aperture polygon (the
  four corners at d -0.03, sill 8.740, head 11.165) must sit 40 px inside the frame under the lens model AND under the
  plain pinhole (the fold guard), in front (z > 0.3), and cover at least 1500 px.
  Reading. r = median grey inside the polygon / median grey of the ring (polygon scaled 1.6x about its centre, the
  polygon cut out). Grey is the PNG's luma.
  Controls, per pair. The ring must be wall: NIGHT ring median 12 to 120 (the one night wall read so far was 36,
  and the day range 40 to 200 fails night by construction, so this range is set from that single number and says
  so); DAY (walk, day4k) ring median 40 to 200. Both: the ring's interquartile range under 60 grey, which a flare
  gradient or a glass edge fails. A pair failing a control is void and not counted.
  What the sim shows there. Each pair is sorted by where the ray from the camera through the aperture's centre
  ends in the sim as drawn: above the head (11.165) when it reaches the reveal's back edge 0.9 m in, it ends on the
  HEAD SOFFIT (wall-reveal, a Lambert lit from above); between the corridor ceiling (10.947) and the head, on the
  DOWNSTAND; else it enters the corridor and ends on the CEILING if it is above 10.947 after the corridor's 1.42 m,
  or on the BACK wall. Claims are made per class and per ending, because those are different surfaces in the sim.
  Claim. The median r over the surviving pairs of a (class, ending); the spread is half the interquartile range. A
  group with fewer than 20 surviving pairs, or a spread larger than its claim, records only.
  Decision. The sim's r through the same kind of view is known from the two renders of opening_tone.py: 0.05 at
  night (w6_000146, opening 7: inside 1, wall 19) and 0.00 by day from the floor (w1_000104, opening 5: inside 0,
  wall 116). NIGHT: if the night claim exceeds 1.5 x 0.05 the corridor's night colours are raised so the sim's
  inside reads claim x 19 through w6_000146, and that render is repeated to check it lands inside claim +/- spread.
  DAY: the day claim is compared with a repeat render of w1_000104 after any change; the day colours change only
  if the sim's day r falls outside claim +/- spread AND the walk and day4k claims agree in direction against it.
  Each decision is per class; the two-frame agreement rule of opening_tone.py belonged to that tool's two frames.

THE RESULT (the run, 123 s, peak 0.89 GB).
  night 140 pairs (void: ring 5, iqr 21): ceiling 138, r 0.447 spread 0.065, inside 31 ring 72, CLAIM; downstand 2.
  walk 571 pairs (void: ring 229, iqr 18, small 214): soffit 109, r 0.978 spread 0.036, CLAIM; downstand 13, r 0.674;
    ceiling 449, r 0.714 spread 0.069, inside 35 ring 49, CLAIM.
  day4k 729 pairs (void: ring 307, iqr 47): back 729, r 0.959 spread 0.146, CLAIM; per opening 0 to 4 near 1.0 (the jamb
    face at grazing angles, 30 to 44 m off), 6 to 10 0.49 to 0.66 (the back wall, as d4_000120 read it).
  Renders through the same poses, before: walk ceiling pairs w1_000379/3 0.45, w2_000243/7 0.44, w1_000526/11 0.50.

TWO CONTROLS THIS RULE LACKED, ADDED AFTER SEEING THE DATA, AND SAID SO.
  A group whose r sits within 5 per cent of 1 with a spread under 0.05 is the wall: w1_000044's polygon lies on plain
  wall between two slots, the grazing views' pose error being the width of a slot. The soffit claim is VOID by it.
  A sim render whose ring is not wall (w1_000437: a foreground tower, ring 6) is void for the sim side.

WHAT MOVED IN THE SIM, AND THE RENDERS AFTER (index.html carries the same record).
  Night colour 9 -> 65: rendered 26 and 54 (r 1.30, 2.45), the toe of the night curve is not a line. -> 34: rendered
  13 and 22 (r 0.68, 1.00). -> 27, for 9 grey by the line grey = 0.45 (colour - 7) that the last two points make.
  Day ceiling 42 -> 67, the head underside unlit at the same tones: w1_000379 0.73, w2_000243 0.49, w1_000526 0.88
  against 0.714 +/- 0.069; the median sits inside, the scatter is the sim's wall (51 to 104 across those views, the
  photo's 48 to 55). The back wall's day colour keeps d4_000120.
  The night claim leans bright: w6_000146's photo polygon lies half on the wall. The sim errs light by that much.

Run (whole dataset, through the broker):
  hwq run --gb 6 --label "opening tone sweep" -- python -u tools/opening_tone_sweep.py
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853], [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
SILL, HEAD, DFACE = 8.740, 11.165, -0.03
MARGIN, MINPX, RING, IQR_MAX = 40, 1500, 1.6, 60
WALL = {'night': (12, 120), 'walk': (40, 200), 'day4k': (40, 200)}
SIM = {('night', 'ceiling'): 0.05, ('walk', 'soffit'): 0.00}   # from the two renders of opening_tone.py
OPEN_DEPTH, CEIL, CORR_W = 0.9, 10.947, 1.420


def ending(cam, k):
    u0, u1 = OPEN[k]; c = W((u0 + u1) / 2, DFACE, (SILL + HEAD) / 2)
    D = c - cam.center; dd = float(-(D @ HD)); dh = float(D[1])
    if dd <= 0: return 'level'
    slope = dh / dd
    hR = (SILL + HEAD) / 2 + slope * OPEN_DEPTH
    if hR > HEAD: return 'soffit'
    if hR > CEIL: return 'downstand'
    if hR < 8.34: return 'upstand'
    hB = hR + slope * CORR_W
    return 'ceiling' if hB > CEIL else 'back'
FACTOR = 1.5
OUT = 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad/opening-tone-sweep.json'


def W(u, d, h):
    return O + u * HU + d * HD + np.array([0, h, 0])


def polys(cam):
    """(k, polygon) for every opening this camera sees whole under both models."""
    out = []
    for k, (u0, u1) in enumerate(OPEN):
        pts = np.array([W(u0, DFACE, SILL), W(u1, DFACE, SILL), W(u1, DFACE, HEAD), W(u0, DFACE, HEAD)])
        x, y, z = cam.project(pts)
        if (z <= 0.3).any(): continue
        if (x < MARGIN).any() or (x > cam.w - MARGIN).any() or (y < MARGIN).any() or (y > cam.h - MARGIN).any(): continue
        D = pts - cam.center; zz = D @ cam.R[2]
        px = cam.params[0] * (D @ cam.R[0]) / zz + cam.params[2]; py = cam.params[1] * (D @ cam.R[1]) / zz + cam.params[3]
        if (px < MARGIN).any() or (px > cam.w - MARGIN).any() or (py < MARGIN).any() or (py > cam.h - MARGIN).any(): continue
        out.append((k, np.stack([x, y], 1)))
    return out


def read(g, poly):
    m = np.zeros(g.shape, np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    n = int(m.sum())
    if n < MINPX: return None
    c = poly.mean(0); big = ((poly - c) * RING + c).astype(np.int32)
    mb = np.zeros(g.shape, np.uint8); cv2.fillPoly(mb, [big], 1)
    ring = g[np.logical_and(mb == 1, m == 0)]
    if ring.size < MINPX: return None
    q1, q3 = np.percentile(ring, (25, 75))
    return float(np.median(g[m == 1])), float(np.median(ring)), float(q3 - q1), n


def main():
    result = {}
    for cls in ('night', 'walk', 'day4k'):
        cams = load_class(cls); rows = []; void = {'ring': 0, 'iqr': 0, 'small': 0}
        for stem, (cam, imgpath) in sorted(cams.items()):
            pl = polys(cam)
            if not pl: continue
            img = cv2.imread(imgpath, cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            for k, poly in pl:
                r = read(img, poly)
                if r is None: void['small'] += 1; continue
                inside, ring, iqr, n = r
                lo, hi = WALL[cls]
                if not (lo <= ring <= hi): void['ring'] += 1; continue
                if iqr >= IQR_MAX: void['iqr'] += 1; continue
                rows.append(dict(frame=stem, k=k, inside=inside, ring=ring, iqr=iqr, px=n, r=inside / ring, end=ending(cam, k)))
        print('%s: %d pairs survive (void: ring %d, iqr %d, small %d)' % (cls, len(rows), void['ring'], void['iqr'], void['small']))
        groups = {}
        for e in ('soffit', 'downstand', 'ceiling', 'back', 'upstand', 'level'):
            sub = [w for w in rows if w['end'] == e]
            if not sub: continue
            rs = np.array([w['r'] for w in sub]); med = float(np.median(rs)); q1, q3 = np.percentile(rs, (25, 75)); spread = float((q3 - q1) / 2)
            ok = len(rs) >= 20 and spread < med
            per_k = {k: float(np.median([w['r'] for w in sub if w['k'] == k])) for k in range(12) if any(w['k'] == k for w in sub)}
            print('   %-9s %4d pairs  r median %.3f  spread %.3f  inside %.0f  ring %.0f  %s' % (e, len(rs), med, spread, np.median([w['inside'] for w in sub]), np.median([w['ring'] for w in sub]), 'CLAIM' if ok else 'RECORD ONLY'))
            print('             per opening: ' + '  '.join('%d:%.2f' % (k, v) for k, v in sorted(per_k.items())))
            widest = max(sub, key=lambda w: w['px'])
            print('             widest: %s opening %d (%d px, r %.2f)' % (widest['frame'], widest['k'], widest['px'], widest['r']))
            if (cls, e) in SIM and ok:
                s = SIM[(cls, e)]
                print('             sim r %.2f: %s' % (s, 'the sim is darker than the claim by more than %.1fx' % FACTOR if med > FACTOR * max(s, 1e-6) else 'within %.1fx of the claim' % FACTOR))
            groups[e] = dict(n=int(len(rs)), median=med, spread=spread, claim=ok, per_opening=per_k, widest=widest)
        for stem, k in (('w6_000146', 7), ('w1_000104', 5)):
            for w in rows:
                if w['frame'] == stem and w['k'] == k: print('   %s opening %d: inside %.0f ring %.0f r %.2f ends on the %s' % (stem, k, w['inside'], w['ring'], w['r'], w['end']))
        result[cls] = dict(n=len(rows), void=void, groups=groups, rows=rows)
    json.dump(result, open(OUT, 'w'))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
