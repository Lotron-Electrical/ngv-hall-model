"""THE LEDGE INSTRUMENT RUN ON THE WEST DECK, WHERE THE ANSWER IS ALREADY KNOWN (2026-09-10, the control
for tools/ledge_edge.py).

tools/ledge_edge.py read the east deck's ledge edge from the posed cameras standing on it and moved the
east's opaque solid back 0.404 on that reading. It had one internal control (one dominant peak per frame)
and no external one: nothing checked the instrument against a station measured another way. The west
deck has that station. tools/end_face_scan.py put the west solid's top on u 3.710 at h 9.097 from the
hall side, near and far cameras agreeing to 5 mm, and b7s frames 608 to 912 stand on the west deck's
south end (u 3.2 to 3.3, facing east) with that ledge along the bottom of the frame, exactly the east's
situation mirrored. If the sweep finds the west edge where the hall put it, the instrument and the poses
it rests on are validated and the east reading stands as the hint it is. If it does not, the east run is
vetoed, because it shares the poses and the method.

THE DECISION RULE, FIXED BEFORE THE RUN.
  1. The sweep is the east one mirrored: for each candidate (u_e, 9.097) the line along d is projected
     and the tone step across it scored; one dominant peak per frame (second under 60% of the first) or
     the frame is dropped; fewer than four survivors means no verdict and the east keeps its note.
  2. THE CONTROL PASSES if the known station 3.710 lies inside the survivors' range of u and the median
     is within 0.10 of it. The bias (median minus 3.710) is recorded either way.
  3. If it passes, index.html records the validation under the east block and nothing moves.
  4. If it fails, the east's set-back (upstandSet.east 0.404), faceSolid.east and faceBand.east are
     WITHDRAWN and the east parapet returns to the drawing before them (the flush solid to 9.095), with
     the failure written down; the refutation of the flush solid rested on the same poses and falls with
     them.

THE RESULT (2026-09-10). Sixteen posed frames; eleven pass the one-peak test (604, 608, 612, 616 and 880 fail,
their second peaks 80 to 95% of the first). Edge on 9.097 (camera u, h -> edge u):
  876 (3.19, 9.56) 3.44   884 (3.25, 9.67) 3.63   888 (3.20, 9.70) 3.68   892 (3.23, 9.69) 3.74   896 (3.25, 9.68) 3.74
  900 (3.28, 9.68) 3.69   904 (3.31, 9.67) 3.64   908 (3.33, 9.66) 3.64   912 (3.33, 9.66) 3.63   916 3.65   920 3.64
  Median 3.640, range 3.44 to 3.74, half-range 0.150; the station 3.710 lies inside the range, the median is 0.070
  from it: THE CONTROL PASSES. The east run stands as the hint it is; nothing in index.html moves. The bias
  (-0.070, the sweep reading the edge nearer its cameras than the hall's station) is recorded: on the east it would
  put the edge on 48.39, inside the east's 0.135 spread.

A NOTE, LATER THE SAME DAY: THE CROSSINGS ON THE WEST FACE, NOT IN THE RULE AND NOT USED. Run each survivor's
sight line over its edge on to the west face (4.194): 7.70, 8.25, 8.45, 8.57, 8.56, 8.38, 8.14, 8.09, 8.04, 8.14,
8.09 for 876 to 920. Seven of eleven are below the deck, which no real edge with the floor seen over it can give,
because such a ray meets the deck strip before the face. The cameras stand 0.30 to 0.55 m from the edge and their u,
the depth of a camera looking along u, is the least constrained pose coordinate; 0.1 m of it moves a crossing here by
0.2 to 0.3 m. So these say nothing about the west face and nothing is drawn from them. They do say the instrument's
per-frame u carries about 0.15 m, which is the spread both sweeps showed, and that the east's ceiling 8.631 is the
lowest of crossings that run 8.63 to 8.86: that spread is the number's honest width.

Run:
  python tools/ledge_edge_west.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
FACE = 4.194; STATION = 3.710; HTOP = 8.34 + 0.757; STEP = 0.01; U0, U1 = 3.30, 4.19; OFF = 8; SECOND = 0.60; PASS = 0.10


def W(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])


def main():
    frames = []
    for cls in ('b7s', 'b7sp'):
        for k, (cam, ip) in U.load_class(cls).items():
            q = cam.center - O
            if q @ HU < 6 and 12.0 < q @ HD < 15 and k not in [f[0] for f in frames]: frames.append((k, cam, ip, q))
    frames.sort(key=lambda t: t[0])
    print('%d posed frames on the west deck' % len(frames))
    us = np.arange(U0, U1 + 1e-9, STEP)
    survivors = []
    for k, cam, ip, q in frames:
        gray = cv2.cvtColor(cv2.imread(ip), cv2.COLOR_BGR2GRAY).astype(np.float32)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        med = np.median(np.abs(np.diff(gray, axis=0)))
        dc = q @ HD; ds = np.arange(dc - 2.5, dc + 1.0, 0.05)
        score = np.zeros(len(us))
        for i, ue in enumerate(us):
            x, y, z = cam.project(np.array([W(ue, d, HTOP) for d in ds]))
            ok = np.logical_and.reduce([z > 0.2, x > 2, x < cam.w - 3, y > OFF + 2, y < cam.h - OFF - 3])
            if ok.sum() < 10: score[i] = 0; continue
            xi = x[ok].astype(int); yi = y[ok].astype(int)
            score[i] = np.mean(gray[yi - OFF, xi] - gray[yi + OFF, xi]) / med
        i_best = int(np.argmax(score)); best = score[i_best]
        peaks = [i for i in range(1, len(us) - 1) if score[i] > score[i - 1] and score[i] >= score[i + 1] and abs(us[i] - us[i_best]) > 0.05]
        second = max([score[i] for i in peaks], default=0.0)
        control = best > 0 and second < SECOND * best
        cu, ch = q @ HU, q[1]
        print('%s: camera u %.2f h %.2f; edge u %.2f (score %.1f, next peak %.1f) %s'
              % (k, cu, ch, us[i_best], best, second, 'CONTROL PASS' if control else 'CONTROL FAIL'))
        if control: survivors.append((us[i_best], cu, ch))
    print()
    if len(survivors) < 4:
        print('FEWER THAN FOUR SURVIVORS (%d): no verdict.' % len(survivors)); return
    ue = np.array([s[0] for s in survivors])
    medu = float(np.median(ue)); hr = (ue.max() - ue.min()) / 2; bias = medu - STATION
    inside = ue.min() - 1e-9 <= STATION <= ue.max() + 1e-9
    print('west ledge edge on h %.3f: u %.3f (median of %d, range %.2f to %.2f, half-range %.3f); known station %.3f; bias %+.3f'
          % (HTOP, medu, len(ue), ue.min(), ue.max(), hr, STATION, bias))
    ok = inside and abs(bias) <= PASS
    print('THE CONTROL %s: the station %s inside the range and the median is %.3f from it (bar %.2f).'
          % ('PASSES' if ok else 'FAILS', 'lies' if inside else 'is NOT', abs(bias), PASS))
    print('   the east run %s.' % ('is validated; its reading stands as the hint it is' if ok else 'is VETOED; the east set-back, faceSolid and faceBand are withdrawn'))


if __name__ == '__main__':
    main()
