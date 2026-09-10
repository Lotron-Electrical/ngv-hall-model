"""THE CORRIDOR'S LAMPS AT THEIR OWN POSITIONS, BY DAY AND BY NIGHT (2026-09-10, after tools/lamp_night.py).

lamp_night.py read the brightest point in a whole widened slot and its day positive control failed: too much else is
bright in a slot. This looks only where each lamp is. The two lamps were triangulated from day frames (index.html
C.lamps: u 30.527 d -2.022 h 10.916 and u 34.140 d -2.047 h 10.945), so their projected pixel in any posed frame is
known to the pose's error, about half a slot.

THE RULE, FIXED BEFORE THE RUN.
  Visible. A frame counts for a lamp only if the sim's own geometry lets the ray from the camera reach it: through
  the aperture (at the face, d -0.03, the ray's u inside the opening and h between sill 8.740 and head 11.165), past
  the reveal (at d -0.93, u still inside the opening, h under the corridor ceiling 10.947 and over its floor 8.34),
  and with the lamp inside the frame by 40 px under the lens model and under the plain pinhole (the fold guard).
  Region. A disc about the lamp's projected pixel whose radius is 0.6 m at the lamp's distance (the pose error), at
  least 12 px; the annulus from 2 to 3 radii is the local ground.
  Reading. The frame blurred 3x3; PEAK = the 99.5th percentile inside the disc; GROUND = the median of the annulus.
  A pair is LIT if PEAK / GROUND >= 2.5.
  Null. Three lamps that do not exist, mid-slot behind openings 9, 10 and 11 at the same d and h, read the same way.
  Claim per class and lamp: LIT if more than half the visible pairs are LIT and the nulls' lit fraction is under a
  tenth; DARK if fewer than a tenth are LIT and the nulls too; else undecided.
  Positive control. By day (walk and day4k together) both lamps must read LIT, or the instrument is unproven and the
  night answer is recorded only.
  Decision. If the day control holds and both lamps read DARK by night with the night nulls DARK, the lamp material
  takes a dark night colour (cnm), day unchanged, and w6_000146 is rendered to show the dot gone. Otherwise nothing.

THE FIRST RUN (1 s). Day: lamp7 16 visible pairs, all LIT (ratio median 4.75, peak median 200, ground 42); lamp8 13,
  all LIT (4.44, 189, 42); every one a walk frame 16 to 18 m off; null9 2 pairs, one LIT (w2_000196, peak 124 over
  36, ratio 3.45), null10 and null11 none visible: the null fails on a sample of two, so the day control is
  undecided by the rule as written. Night: NO visible pairs. Lamp7 is in frame in 17 night frames (w6_000144 to 147
  among them) and the sim's jamb hides it by 1 to 3 cm, a fiftieth of the pose error; lamp8 is hidden by 0.64 m.
  Nothing decided.

THE SECOND RUN, RULE AMENDED AFTER SEEING THE FIRST, AND SAID SO. Two changes, each from a number above:
  (a) a pair is LIT only if PEAK >= 150 as well as PEAK / GROUND >= 2.5 (the lamps read 189 to 200 by day, the null's
  one false LIT read 124); (b) the visibility test allows the ray 0.10 m outside the jamb lines (a sixth of the pose
  error the disc already assumes), which admits lamp7's 17 night frames and still excludes lamp8's 34. A claim from
  this run is weaker than one from a rule fixed blind, and the record says so.
  python tools/lamp_point.py second

THE SECOND RUN'S RESULT (1 s). Day: lamp7 16 of 16 LIT, lamp8 13 of 13 LIT, null9 0 of 6 (peak median 45 over 34),
  the control holds. Night: lamp7 2 visible pairs (the other 15 fail the 40 px margin or the reveal), neither LIT
  (peak 56 over ground 42, ratio 1.35), lamp8 none, no null visible. By the rule the night is UNDECIDED: two dark
  pairs without a null are not a count. Nothing in the sim moves. What the archive holds on this question is now
  exhausted: no night camera stands where it can see a corridor lamp with a null beside it.

Run:
  python tools/lamp_point.py
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from opening_tone_sweep import OPEN, SILL, HEAD, DFACE, W, O, HU, HD

LAMPS = {'lamp7': (30.527, -2.022, 10.916, 7), 'lamp8': (34.140, -2.047, 10.945, 8)}
for _k in (9, 10, 11):
    LAMPS['null%d' % _k] = ((OPEN[_k][0] + OPEN[_k][1]) / 2, -2.03, 10.93, _k)
CEIL, FLOOR, DREVEAL, MARGIN, RATIO, MINR = 10.947, 8.34, -0.93, 40, 2.5, 12
SECOND = len(sys.argv) > 1 and sys.argv[1] == 'second'
TOL = 0.10 if SECOND else 0.0       # the second run's jamb tolerance
PEAK_MIN = 150 if SECOND else 0     # the second run's absolute floor
CLASSES = {'day': ('walk', 'day4k'), 'night': ('night',)}
OUT = 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad/lamp-point.json'
OUT2 = 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad/lamp-point-second.json'


def hall(pt):
    q = pt - O
    return float(q @ HU), float(q @ HD), float(q[1])


def visible(cam, lamp):
    lu, ld, lh, k = lamp
    cu, cd, ch = hall(cam.center)
    if cd <= ld: return False
    u0, u1 = OPEN[k]
    for dplane, hlo, hhi in ((DFACE, SILL, HEAD), (DREVEAL, FLOOR, CEIL)):
        t = (dplane - cd) / (ld - cd)
        if not (0 < t < 1): return False
        u = cu + t * (lu - cu); h = ch + t * (lh - ch)
        if not (u0 - TOL <= u <= u1 + TOL and hlo <= h <= hhi): return False
    return True


def project_both(cam, pt):
    x, y, z = cam.project(np.array([pt]))
    D = pt - cam.center; zz = float(D @ cam.R[2])
    px = cam.params[0] * float(D @ cam.R[0]) / zz + cam.params[2]; py = cam.params[1] * float(D @ cam.R[1]) / zz + cam.params[3]
    return float(x[0]), float(y[0]), float(z[0]), px, py


def read(g, x, y, r):
    H, Wd = g.shape
    yy, xx = np.ogrid[:H, :Wd]
    rr = (xx - x) ** 2 + (yy - y) ** 2
    disc = g[rr <= r * r]; ann = g[np.logical_and(rr >= 4 * r * r, rr <= 9 * r * r)]
    if disc.size < 50 or ann.size < 100: return None
    return float(np.percentile(disc, 99.5)), float(np.median(ann))


def main():
    result = {}
    for phase, classes in CLASSES.items():
        rows = []
        for cls in classes:
            for stem, (cam, imgpath) in sorted(load_class(cls).items()):
                hits = []
                for name, lamp in LAMPS.items():
                    if not visible(cam, lamp): continue
                    pt = W(lamp[0], lamp[1], lamp[2])
                    x, y, z, px, py = project_both(cam, pt)
                    if z <= 0.3: continue
                    if not (MARGIN <= x <= cam.w - MARGIN and MARGIN <= y <= cam.h - MARGIN): continue
                    if not (MARGIN <= px <= cam.w - MARGIN and MARGIN <= py <= cam.h - MARGIN): continue
                    r = max(MINR, cam.params[0] * 0.6 / z)
                    hits.append((name, x, y, r, z))
                if not hits: continue
                img = cv2.imread(imgpath, cv2.IMREAD_GRAYSCALE)
                if img is None: continue
                g = cv2.blur(img, (3, 3))
                for name, x, y, r, z in hits:
                    rd = read(g, x, y, r)
                    if rd is None: continue
                    peak, ground = rd
                    rows.append(dict(cls=cls, frame=stem, lamp=name, x=round(x), y=round(y), r=round(r), dist=round(z, 1), peak=peak, ground=ground, ratio=peak / max(ground, 1), lit=bool(peak >= RATIO * max(ground, 1) and peak >= PEAK_MIN)))
        verdict = {}
        print('%s (%s)%s:' % (phase, ', '.join(classes), ', SECOND RUN, amended rule' if SECOND else ''))
        for name in LAMPS:
            sub = [w for w in rows if w['lamp'] == name]
            if not sub: print('   %-6s no visible pairs' % name); verdict[name] = 'none'; continue
            lit = sum(w['lit'] for w in sub); frac = lit / len(sub)
            ratios = sorted(w['ratio'] for w in sub)
            print('   %-6s %3d visible pairs, %3d lit (%3.0f%%), ratio median %.2f max %.2f, peak median %.0f, ground median %.0f, distance %.0f to %.0f m' % (
                name, len(sub), lit, 100 * frac, ratios[len(ratios) // 2], ratios[-1], np.median([w['peak'] for w in sub]), np.median([w['ground'] for w in sub]), min(w['dist'] for w in sub), max(w['dist'] for w in sub)))
            verdict[name] = frac
        nulls = [verdict[n] for n in LAMPS if n.startswith('null') and verdict[n] != 'none']
        null_ok = bool(nulls) and all(f < 0.1 for f in nulls)
        state = {}
        for name in ('lamp7', 'lamp8'):
            f = verdict[name]
            state[name] = 'none' if f == 'none' else ('LIT' if (f > 0.5 and null_ok) else ('DARK' if (f < 0.1 and null_ok) else 'undecided'))
        print('   nulls lit fractions %s -> %s; lamp7 %s, lamp8 %s' % (['%.2f' % f for f in nulls], 'null ok' if null_ok else 'NULL FAILS', state['lamp7'], state['lamp8']))
        result[phase] = dict(rows=rows, state=state, null_ok=null_ok)
    day, night = result['day']['state'], result['night']['state']
    if not (day['lamp7'] == 'LIT' and day['lamp8'] == 'LIT'):
        print('VERDICT: the day positive control fails (%s, %s); the instrument is unproven; the night count is recorded only' % (day['lamp7'], day['lamp8']))
    elif night['lamp7'] == 'DARK' and night['lamp8'] == 'DARK':
        print('VERDICT: the day control holds and both lamps are DARK by night with the nulls dark: give the lamps a dark night colour')
    elif night['lamp7'] == 'LIT' or night['lamp8'] == 'LIT':
        print('VERDICT: the day control holds and a lamp is LIT by night: the lamps stay lit')
    else:
        print('VERDICT: the day control holds; the night is undecided (%s, %s); record only' % (night['lamp7'], night['lamp8']))
    json.dump(result, open(OUT2 if SECOND else OUT, 'w'))


if __name__ == '__main__':
    main()
