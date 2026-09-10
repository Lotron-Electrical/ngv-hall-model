"""The corridor behind the brick wall, seen THROUGH the east gallery's north door (2026-09-10).

No posed frame faces the corridor. But b6 frames 1248 and 1320 face the east gallery's north door
square from 12.9 and 9.5 m (tools/gallery_north_end.py measured the door: jambs u 48.118 and 49.291,
head 11.487), and the door is open: what is inside it is the corridor, or whatever stands behind
that door. The drawn corridor has its ceiling on 10.947 (the height of two lamps read from the hall,
WALLF.lamps) and its back wall on d -2.350 (openDepth 0.90 plus width 1.420). The door head stands
0.54 m ABOVE that ceiling, so through the door the ceiling's underside should be visible as a band
from the head down to where it meets the back wall, and that junction is a horizontal edge whose row
is fixed by the camera distance: angle above the horizon (h - hcam) / (dcam - d), horizon cancelling
against the head's own row. This file looks for that edge.

THE INSTRUMENT. Frames undistorted with the b6g intrinsics. The camera's distance to the wall is
taken from the door's own width in pixels (1.173 m). Inside the door's inner width, rows are
averaged to one column profile and its gradient taken; every horizontal edge is a peak of |gradient|.
The reveal's far arris (the head soffit seen from below, 0.90 m deep as drawn) and the ceiling/back
wall junction get predicted rows; the profile says whether an edge stands there.

THE DECISION RULE, FIXED BEFORE THE RUN.
  1. CONTROL: the head itself must be the strongest edge within 15 px of its seed in both frames, or
     the profile cannot be trusted and nothing is read.
  2. THE DRAWN CEILING (10.947 meeting d -2.350) stands if an edge at least twice the interior's
     median |gradient| lies within 15 px of its predicted row in BOTH frames; it is refuted if that
     holds in NEITHER; otherwise undecided. If refuted, the ceiling behind this door is above the
     line of sight over the head at the back wall, which is (hcam + 1.59 * (dcam - d_b) / (dcam + 0.03))
     per frame, and the file records the larger of the two as the lower bound.
  3. THE SOFFIT DEPTH: the strongest edge between the head and 60 px below it, if any, is read as the
     far edge of a lit soffit at the head's height, and its depth t follows from the gap
     g = f * 1.59 * (1/Z - 1/(Z + t)). Reported from both frames, and a HINT unless the two agree
     within 0.25 m, because a 5 px reading error moves it by 0.3 m from 12.9 m off.
  4. Anything else inside the door (the dark-framed rectangle) is described, not measured: its size
     hardly changes between the two distances, which says it is far beyond the back wall.

THE RESULT (2026-09-10, first run).
  b6_001248: door 117 px -> camera d 12.90. Head seed 823, strongest edge 832 (control pass). Junction row
  predicted 902: strongest edge within 15 px 1.4 on row 892, interior median 1.1: NO EDGE. Soffit far edge
  on row 842 (gap 10 px) -> 0.87 m. Bound if refuted: 11.77.
  b6_001320: door 159 px -> camera d 9.48. Head seed 948, strongest edge 961 (control pass). Junction row
  predicted 1062: strongest edge within 15 px 1.4 on row 1073, median 0.6: an edge stands there. Soffit far
  edge on row 985 (gap 24 px) -> 1.19 m. Bound if refuted: 11.87.
  UNDECIDED by the rule: the ceiling stays on 10.947. Soffit depth 0.87 and 1.19: a hint only.
  Seen and not measured: a dark-framed rectangle with a lit panel, 70 px wide from 12.9 m and 75 px from
  9.5 m (a thing on the back wall would have grown by a third), so it stands far beyond the corridor and
  the corridor's back wall must be open opposite the door; index.html draws that opening by eye.

Run:
  python tools/door_interior.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

RAW = 'E:/sitecapture-captures/ngv-video/balcony2/b6/images/b6_%06d.png'
DOOR_W = 49.291 - 48.118; HEAD = 11.487; HCAM = 9.9; CEIL = 10.947; DB = -2.350; DFACE = -0.030; REVEAL = 0.90
TOL = 15; STRONG = 2.0
# seeds (undistorted px): the door's jambs (row band) and the head row
SEEDS = {1248: dict(jambs=(676, 793), band=(880, 950), head=823),
         1320: dict(jambs=(564, 723), band=(1000, 1080), head=948)}


def main():
    fr = U.load_class('b6g'); cam, _ = fr[sorted(fr)[0]]
    fx, fy, cx, cy, k1, k2, p1, p2 = cam.params
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]); dist = np.array([k1, k2, p1, p2])
    f = fy
    verdicts = []; bounds = []; depths = []
    for fno, sd in SEEDS.items():
        im = cv2.undistort(cv2.imread(RAW % fno), K, dist)
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        xa, xb = sd['jambs']; wpx = xb - xa
        dcam = f * DOOR_W / wpx + DFACE            # camera d from the door's width
        Z = dcam - DFACE
        inner = gray[:, xa + 12: xb - 12].mean(axis=1)
        inner = cv2.GaussianBlur(inner.reshape(-1, 1), (1, 5), 0).ravel()
        g = np.abs(np.gradient(inner))
        h0 = sd['head']; i0 = int(np.argmax(g[h0 - TOL:h0 + TOL])) + h0 - TOL
        control = abs(i0 - h0) <= TOL and g[i0] == g[h0 - TOL:h0 + TOL].max()
        # predicted rows, relative to the head row: dy = f * (a_head - a_x)
        a_head = (HEAD - HCAM) / Z
        a_join = (CEIL - HCAM) / (dcam - DB)
        a_arris = (HEAD - HCAM) / (Z + REVEAL)
        y_join = i0 + f * (a_head - a_join)
        y_arris = i0 + f * (a_head - a_arris)
        seg = g[i0 + 30: i0 + 260]                 # the interior, below the head band
        med = np.median(seg)
        lo_j, hi_j = int(y_join - TOL), int(y_join + TOL)
        peak_j = g[lo_j:hi_j].max(); row_j = lo_j + int(np.argmax(g[lo_j:hi_j]))
        stands = peak_j >= STRONG * med
        bound = HCAM + (HEAD - HCAM) * (dcam - DB) / Z
        # the soffit's far edge
        s0, s1 = i0 + 6, i0 + 60
        row_s = s0 + int(np.argmax(g[s0:s1])); gap = row_s - i0
        t = 1.0 / (1.0 / Z - gap / (f * (HEAD - HCAM))) - Z
        print('b6_%06d: door %d px wide -> camera d %.2f (Z %.2f); head seed %d, strongest edge near it %d (%s)'
              % (fno, wpx, dcam, Z, h0, i0, 'CONTROL PASS' if control else 'CONTROL FAIL'))
        print('   drawn ceiling %.3f meeting d %.3f: junction predicted on row %.0f; strongest edge within %d px is %.1f on row %d, '
              'interior median %.1f -> %s' % (CEIL, DB, y_join, TOL, peak_j, row_j, med, 'an edge stands there' if stands else 'NO EDGE'))
        print('   reveal far arris (0.90 deep) predicted on row %.0f; strongest edge under the head on row %d (gap %d px) -> soffit depth %.2f m'
              % (y_arris, row_s, gap, t))
        print('   if the ceiling is above the sightline over the head at d %.2f, it is above %.2f' % (DB, bound))
        verdicts.append((control, stands)); bounds.append(bound); depths.append(t)
    print()
    if not all(v[0] for v in verdicts):
        print('A CONTROL FAILED: nothing read.'); return
    n = sum(1 for v in verdicts if v[1])
    if n == 2: print('THE DRAWN CEILING STANDS: an edge sits on its predicted row in both frames.')
    elif n == 0: print('THE DRAWN CEILING IS REFUTED BEHIND THIS DOOR: no edge on its row in either frame. The ceiling there is above %.2f (the larger bound).' % max(bounds))
    else: print('UNDECIDED: one frame shows an edge on the row, the other does not.')
    print('soffit depth from the two frames: %.2f and %.2f -> %s' % (depths[0], depths[1], 'agree within 0.25, a reading' if abs(depths[0] - depths[1]) < 0.25 else 'a hint only'))


if __name__ == '__main__':
    main()
