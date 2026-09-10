"""The east deck's ledge, from the six posed cameras that stood on that deck (2026-09-10).

THE PICTURE. b7s and b7sp frames 68 to 156 stand on the east deck's south end (u 48.99 to 49.21, h 9.50
to 9.73, facing west) with the hall in view and, along the bottom of every frame, a broad dark flat
surface: the ledge the phone was rested on (a phone case sits on it in b7s_000080). Its far edge is the
occluding contour where the HALL FLOOR appears above it: people and seats are seen straight over that
edge. index.html draws the east parapet as a solid upstand on the glass line (u 48.056) up to 9.095 with
a coping 0.45 wide behind it, and projects that coping's outer edge 550 px above where the frames have
the ledge edge. Whatever the ledge is, its outer top edge is a line along d with some (u, h), and a
camera 0.6 m above it cannot separate u from h along its own ray; but six cameras of three heights
and two stations narrow the family, and the drawn height 9.095 (the parapet's top edge as measured
from the hall, ENDW.upstands.east) picks one member of it.

THE INSTRUMENT. For each candidate edge (u_e, h 9.095) the line is projected into each frame over d from
the camera's d minus 2.5 to plus 1.0 and sampled; the score is the mean over samples of the tone step
across the line (8 px above minus 8 px below, the ledge being darker than the hall), in units of the
frame's median absolute row gradient. u_e sweeps 48.06 to 49.00 by 0.01. The peak per frame is the
edge; the pooled edge is the median over frames.

THE DECISION RULE, FIXED BEFORE THE RUN.
  1. CONTROL: in every frame the sweep must have ONE dominant peak (the second-highest local maximum
     under 60% of the first); a frame that fails is dropped, and fewer than four survivors means no
     claim.
  2. THE EDGE: claimed if the survivors' half-range is under 0.06 m; otherwise a hint.
  3. THE MEANING, fixed now: the sight line from each camera over the pooled edge continues down to
     the glass line u 48.056; the height where it crosses is the most the solid on the glass line can
     reach (the hall floor is seen over the edge). The file records the lowest of those crossings as
     the ceiling on the glass-line solid. If that ceiling is under the drawn 9.095, the drawn solid
     upstand on the glass line is refuted and the parapet becomes: a low solid on the glass line up to
     that ceiling (by this instrument), glass above it, and the ledge behind it with its outer edge on
     the pooled u, its top on 9.095. The ledge's width is not measured here (its inner edge is under
     the camera) and stays 0.45 by eye.

THE RESULT (2026-09-10). Eleven posed frames; ten pass the control (156 fails: second peak 31.7 against 50.7).
  frame (camera u, h): edge u on 9.095, crossing on the glass line
  68 (49.21, 9.67): 48.45, 8.80   72: 48.47, 8.77   76: 48.48, 8.76   80: 48.49, 8.75
  132 (49.13, 9.67): 48.47, 8.73   136 (49.08, 9.69): 48.41, 8.78   140 (49.03, 9.71): 48.38, 8.79
  144 (48.99, 9.73): 48.36, 8.79   148 (48.94, 9.75): 48.29, 8.86   152 (49.10, 9.59): 48.56, 8.63
  Edge on 9.095: median 48.460, half-range 0.135, A HINT. Ceiling on the glass-line solid 8.631 (0.291 over
  the deck): the drawn coping edge (48.056, 9.095) is REFUTED. Version 2: (47.950, 8.673), rms 0.055, a hint.
  index.html: faceSolid.east 0.291; faceBand.east [0.291, 0.755], a tinted band on the face whose top is the
  edge tools/end_face_scan.py tracked on u 48.055 (the deck sees the floor through the face beneath it, so
  it is not an opaque solid; what it is made of is unmeasured); upstandSet.east 0.404 (the pooled u, a hint,
  0.08 from the west end's measured 0.484); the coping 0.45 by eye behind it, now running into the north door.

Run:
  python tools/ledge_edge.py
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
GLASS = 48.056; HTOP = 8.34 + 0.755; STEP = 0.01; U0, U1 = 48.06, 49.00; OFF = 8; SPREAD = 0.06; SECOND = 0.60


def W(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])


def main():
    frames = []
    for cls in ('b7s', 'b7sp'):
        for k, (cam, ip) in U.load_class(cls).items():
            q = cam.center - O
            if q @ HU > 46 and 12.5 < q @ HD < 15 and k not in [f[0] for f in frames]: frames.append((k, cam, ip, q))   # a frame posed in both classes counts once
    frames.sort(key=lambda t: t[0])
    print('%d posed frames on the east deck' % len(frames))
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
        slope = (ch - HTOP) / (cu - us[i_best])
        cross = HTOP - slope * (us[i_best] - GLASS)
        print('%s: camera u %.2f h %.2f; edge u %.2f (score %.1f, next peak %.1f) %s; sight line reaches the glass line on h %.2f'
              % (k, cu, ch, us[i_best], best, second, 'CONTROL PASS' if control else 'CONTROL FAIL', cross))
        if control: survivors.append((us[i_best], cross, cu, ch))
    print()
    if len(survivors) < 4:
        print('FEWER THAN FOUR SURVIVORS (%d): no claim.' % len(survivors)); return
    ue = np.array([s[0] for s in survivors]); cr = np.array([s[1] for s in survivors])
    hr = (ue.max() - ue.min()) / 2
    print('ledge outer top edge on h %.3f: u %.3f (median of %d, half-range %.3f) -> %s'
          % (HTOP, np.median(ue), len(ue), hr, 'CLAIMED' if hr < SPREAD else 'a hint, spread too wide'))
    print('the solid on the glass line can reach no higher than h %.3f (the lowest crossing; drawn 9.095, floor 8.34 -> %.3f above the deck)'
          % (cr.min(), cr.min() - 8.34))
    # VERSION 2, declared after the first run showed the per-frame u climbing as the camera height falls, which is
    # what a single edge BELOW 9.095 does to a sweep pinned on 9.095: fit one edge (u_e, h_e) to all the survivors'
    # rays at once. Each survivor's ray runs from its camera through (u_i, 9.095); the fitted edge is the (u_e, h_e)
    # that minimises the spread of the rays' heights on u_e. Claimed if the rms of those heights is under 0.04 m
    # and the edge sits in 48.0..49.0 by 8.34..9.5; otherwise a hint.
    cu = np.array([s[2] for s in survivors]); ch = np.array([s[3] for s in survivors])
    slopes = (ch - HTOP) / (cu - ue)
    best = None
    for u_e in np.arange(47.9, 49.0, 0.005):
        h_i = ch - slopes * (cu - u_e)
        rms = h_i.std()
        if best is None or rms < best[0]: best = (rms, u_e, h_i.mean())
    rms, u_e, h_e = best
    ok = rms < 0.04 and 48.0 <= u_e <= 49.0 and 8.34 <= h_e <= 9.5
    print('VERSION 2, one edge fitted to %d rays: u %.3f, h %.3f (%.3f above the deck), rms of the ray heights %.3f -> %s'
          % (len(survivors), u_e, h_e, h_e - 8.34, rms, 'CLAIMED' if ok else 'a hint'))
    print('   the drawn coping edge (u %.3f, h %.3f) is %.2f m out and %.2f m up from it' % (GLASS, HTOP, u_e - GLASS, HTOP - h_e))


if __name__ == '__main__':
    main()
