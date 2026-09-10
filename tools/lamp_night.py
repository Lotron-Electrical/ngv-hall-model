"""ARE THE CORRIDOR'S LAMPS LIT AT NIGHT? (2026-09-10, after tools/opening_tone_sweep.py)

The corridor's two downlights (C.lamps, u 30.527 and 34.140, triangulated from day frames as bright points) are drawn
with an unlit bright material, so the sim shows them lit at every hour, and the night render of w6_000146 puts a white
dot inside opening 7 where the night photo shows a slot of one dark tone. This asks the night frames directly.

THE RULE, FIXED BEFORE THE RUN.
  Pairs. Every night frame that sees opening 7 or 8 whole (the fold-guarded test of opening_tone_sweep.polys), and,
  as the CONTROL, every night frame that sees opening 9, 10 or 11 whole, which have no lamp drawn behind them.
  Region. The slot polygon widened by 0.6 m each side along u (the pose error is half a slot) and from the sill to the
  head; the ring is the same as the sweep's (1.6x about the centre, the polygon cut out) and its median must be wall,
  12 to 120, or the pair is void.
  Reading. The image is blurred 3x3 first (a lamp 0.15 m across seen from 11 m with f 1290 is 17 px, a hot pixel is
  one); the pair's PEAK is the 99.9th percentile of grey inside the region. A lit lamp saturates: PEAK >= 200 counts
  as LIT, else DARK. By day the same lamp shows as a bright point through opening 7 in the walk frames (w2_000243).
  Claim. For each of openings 7 and 8: LIT if more than half the pairs are LIT; DARK if fewer than one in ten are;
  otherwise undecided and record only. The control openings 9 to 11 must come out DARK by the same count, or the
  measure is reading something other than lamps (a reflection, the truss lights) and the run is void.
  Decision. If both lamp openings read DARK and the control holds, the lamp material takes a dark night colour (cnm),
  the day colour unchanged. If either reads LIT, nothing changes. Anything else records only.

  Positive control, by day. The same count over the walk frames (wall 40 to 200): openings 7 and 8 should read LIT
  and 9 to 11 DARK, which shows the measure can see a lamp when there is one. Added before the run.

THE RESULT (both runs, 2 s and 7 s).
  Night: opening 7, 9 pairs, none lit, peak median 110, max 129, ring 56; opening 8, 25 pairs, none lit, peak median
    166, max 182, ring 77; controls 9, 10, 11 (32, 34, 37 pairs) none lit, peaks 122 to 167, rings 80 to 100. By the
    count, DARK everywhere, control held.
  Day, the positive control: opening 7, 62 pairs, 9 lit (15 per cent, max 221); opening 8, 63 pairs, 3 lit (5 per
    cent); controls 9, 10, 11: 0, 2 and 11 lit (0, 3 and 13 per cent, two of them reaching 255). Neither lamp opening
    read LIT and a control opening did not read DARK: the positive control FAILED.
  So the instrument is unproven: by day it sees the lamp in one frame in seven and sees something as bright behind a
  lampless opening in one in eight (glass reflections or the truss lights inside the widened region, not looked into).
  The night count is recorded as what it is, thirty-four night pairs with nothing brighter than 182 behind either
  lamp opening while the truss lamps in the same frames saturate, and the lamp material is NOT changed by it: a
  control that fails vetoes the run. What would prove the instrument: a region tight to the lamp's own projected
  position (0.15 m, known to 5 cm from the triangulation) instead of the whole widened slot, by day first.

Run:
  python tools/lamp_night.py          # night
  python tools/lamp_night.py walk     # the day control
"""
import os, sys, json
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from opening_tone_sweep import OPEN, SILL, HEAD, DFACE, MARGIN, RING, W, polys

LAMP_OPENINGS = (7, 8)
CONTROL_OPENINGS = (9, 10, 11)
WIDEN = 0.6
WALL = (12, 120)
LIT_PEAK = 200
OUT = {'night': 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad/lamp-night.json',
       'walk': 'C:/Users/LLOYDG~1/AppData/Local/Temp/claude/C--Users-Lloyd-Gibbs-Claude-Projects-ngv-hall-model/7ac78459-3aa5-43ef-aae7-7d6745ece11b/scratchpad/lamp-day-control.json'}


def region(cam, k):
    u0, u1 = OPEN[k]
    pts = np.array([W(u0 - WIDEN, DFACE, SILL), W(u1 + WIDEN, DFACE, SILL), W(u1 + WIDEN, DFACE, HEAD), W(u0 - WIDEN, DFACE, HEAD)])
    x, y, z = cam.project(pts)
    return np.stack([x, y], 1)


def peak_and_ring(g, poly):
    m = np.zeros(g.shape, np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    c = poly.mean(0); big = ((poly - c) * RING + c).astype(np.int32)
    mb = np.zeros(g.shape, np.uint8); cv2.fillPoly(mb, [big], 1)
    ring = g[np.logical_and(mb == 1, m == 0)]
    if m.sum() < 500 or ring.size < 500: return None
    inside = g[m == 1]
    return float(np.percentile(inside, 99.9)), float(np.median(ring)), int(m.sum())


def main():
    cls = sys.argv[1] if len(sys.argv) > 1 else 'night'
    wall = (40, 200) if cls != 'night' else WALL
    cams = load_class(cls)
    rows = []
    for stem, (cam, imgpath) in sorted(cams.items()):
        seen = {k for k, _ in polys(cam)}
        want = [k for k in LAMP_OPENINGS + CONTROL_OPENINGS if k in seen]
        if not want: continue
        img = cv2.imread(imgpath, cv2.IMREAD_GRAYSCALE)
        if img is None: continue
        g = cv2.blur(img, (3, 3))
        for k in want:
            r = peak_and_ring(g, region(cam, k))
            if r is None: continue
            peak, ring, n = r
            if not (wall[0] <= ring <= wall[1]): continue
            rows.append(dict(frame=stem, k=k, peak=peak, ring=ring, px=n, lit=bool(peak >= LIT_PEAK)))
    verdict = {}
    for k in LAMP_OPENINGS + CONTROL_OPENINGS:
        sub = [w for w in rows if w['k'] == k]
        if not sub:
            print('opening %d: no pairs' % k); verdict[k] = 'none'; continue
        lit = sum(w['lit'] for w in sub); frac = lit / len(sub)
        v = 'LIT' if frac > 0.5 else ('DARK' if frac < 0.1 else 'undecided')
        peaks = sorted(w['peak'] for w in sub)
        print('opening %d%s: %d pairs, %d lit (%.0f%%), peak median %.0f, max %.0f, ring median %.0f -> %s' % (
            k, ' (lamp)' if k in LAMP_OPENINGS else ' (control)', len(sub), lit, 100 * frac, peaks[len(peaks) // 2], peaks[-1], np.median([w['ring'] for w in sub]), v))
        verdict[k] = v
    control_ok = all(verdict[k] in ('DARK', 'none') for k in CONTROL_OPENINGS) and any(verdict[k] == 'DARK' for k in CONTROL_OPENINGS)
    lamps = [verdict[k] for k in LAMP_OPENINGS]
    if not control_ok:
        print('VERDICT: the control openings are not dark; the measure is not reading lamps; VOID')
    elif all(v == 'DARK' for v in lamps):
        print('VERDICT: both lamp openings DARK with the control dark: the lamps are off by night; give them a dark night colour')
    elif any(v == 'LIT' for v in lamps):
        print('VERDICT: a lamp opening reads LIT; the lamps stay lit')
    else:
        print('VERDICT: undecided (%s); record only' % lamps)
    json.dump(dict(rows=rows, verdict={str(k): v for k, v in verdict.items()}, control_ok=control_ok), open(OUT[cls], 'w'))


if __name__ == '__main__':
    main()
