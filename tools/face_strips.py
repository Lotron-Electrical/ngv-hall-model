"""THE EAST FACE FROM THE HALL, IN STRIPS ALONG d (2026-09-10, after tools/face_from_hall.py).

face_from_hall.py split its region and kept a lit patch; this reads the face strip by strip, each strip its own
median, so a strip that is dark stays dark and a strip that shows the lit interior shows it.

THE RULE, FIXED BEFORE THE RUN.
  Strips. Thirteen strips of 1 m along d, from d 1 to 14, on the east parapet face (u 48.056) between h 8.45 and
  9.75, and the same thirteen on the back wall (u 51.894) between 10.5 and 12.5; each strip 20 px inside the frame
  under the lens model and the pinhole, 200 px or more.
  Columns. A hall column crossing a strip blackens it; the wall strip above shares the column, so a strip is VOID in
  a frame when its wall strip's median luma is under 25.
  Reading. r_k = median luma of face strip k / median luma of wall strip k, per frame; the claim for strip k is the
  median over the frames that hold it, spread half the interquartile range, ten frames or more, and a claim must
  not be smaller than its spread.
  The sim. The same strips through the render of b7s_000908 (render-shots/render-match/r01.jpg, from back_wall_hue
  photo3), read the same way with the same void test.
  Decision. A strip DISAGREES when the sim's r is more than 1.5x the claim or less than the claim / 1.5. If seven or
  more of the claimed strips disagree the same way: the sim too bright -> the east face's pane above the band takes
  a hall-side black tint whose opacity is the median over those strips of 1 - claim / r_sim, one material for the
  east face only, and a second render checks it; the sim too dark -> recorded, not acted on, because the deck-side
  reading of that pane (face_band.py) is the primary and a brighter face from the hall would come from the interior
  it shows, not the glass. Fewer than seven: record only.

THE RESULT. 23 frames. Claims (r, spread, frames): d 1-2 0.924 (0.512, 20); 2-3 0.558 (0.241, 18); 3-4 0.309 (0.113,
15); 4-5 0.353 (0.249, 14); 5-6 0.217 (0.022, 12); 6-7 0.200 (0.009, 13); 7-8 and 8-9 under their spreads; 9-11 not
held; 11-12 0.197 (0.005, 22); 12-13 0.234 (0.012, 23); 13-14 0.302 (0.024, 23). The sim through b7s_000908: 1-2
0.056; 3-4 0.302; 4-5 0.672; 7-8 0.069; 11-12 0.477; 12-13 0.467; 13-14 0.518. Of nine claimed strips the sim is
too bright in four (4-5 and 11-14, about 2.2x) and too dark in one (1-2, where the sim shows black and the photo
the lit interior): short of seven, RECORD ONLY, nothing moves. What the strips add: from the hall the face reads
the lit interior only at d 1 to 3 (0.92, 0.56) and one dark tone from d 5 on (0.20 to 0.30); the sim's face over
d 11 to 14 sits near 0.5, brighter than that tone, and its north end is black where the photo is lit.

Run:
  python tools/face_strips.py
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import W, HU, HD, UP, SCRATCH

UFACE, UWALL = 48.056, 51.894
FACE_H, WALL_H = (8.45, 9.75), (10.5, 12.5)
STRIPS = [(d, d + 1.0) for d in range(1, 14)]
CLASSES = ('b7s', 'b7sp')
MARGIN, MINPX, MINFRAMES, VOID_LUMA, FACTOR, NEEDED = 20, 200, 10, 25, 1.5, 7


def strip_pts(u, d0, d1, h):
    return [(u, d0, h[0]), (u, d1, h[0]), (u, d1, h[1]), (u, d0, h[1])]


def project_cam(cam, pts):
    P = np.array([W(*p) for p in pts]); x, y, z = cam.project(P)
    D = P - cam.center; zz = D @ cam.R[2]
    px = cam.params[0] * (D @ cam.R[0]) / zz + cam.params[2]; py = cam.params[1] * (D @ cam.R[1]) / zz + cam.params[3]
    ok = (z > 0.5).all() and (x >= MARGIN).all() and (x <= cam.w - MARGIN).all() and (y >= MARGIN).all() and (y <= cam.h - MARGIN).all() \
        and (px >= MARGIN).all() and (px <= cam.w - MARGIN).all() and (py >= MARGIN).all() and (py <= cam.h - MARGIN).all()
    return ok, np.stack([x, y], 1)


def med_luma(g, poly):
    m = np.zeros(g.shape, np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if m.sum() < MINPX: return None
    return float(np.median(g[m == 1]))


def read_frame(g, proj_fn):
    out = {}
    for k, (d0, d1) in enumerate(STRIPS):
        okf, pf = proj_fn(strip_pts(UFACE, d0, d1, FACE_H)); okw, pw = proj_fn(strip_pts(UWALL, d0, d1, WALL_H))
        if not (okf and okw): continue
        a = med_luma(g, pf); b = med_luma(g, pw)
        if a is None or b is None or b < VOID_LUMA: continue
        out[k] = (a, b, a / max(b, 1))
    return out


def main():
    per = {k: [] for k in range(len(STRIPS))}; n_frames = 0
    for cls in CLASSES:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            img = cv2.imread(imgpath, cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            got = read_frame(img, lambda pts: project_cam(cam, pts))
            if not got: continue
            n_frames += 1
            for k, v in got.items(): per[k].append(v[2])
    claims = {}
    for k, rs in per.items():
        if len(rs) < MINFRAMES: continue
        med = float(np.median(rs)); spread = float((np.percentile(rs, 75) - np.percentile(rs, 25)) / 2)
        claims[k] = (med, spread, len(rs), spread < med)
    print('photo: %d frames hold strips; claims per strip (d, r, spread, frames, ok):' % n_frames)
    for k, (med, spread, n, ok) in sorted(claims.items()): print('   d %2d-%2d  r %.3f  spread %.3f  %2d frames  %s' % (STRIPS[k][0], STRIPS[k][1], med, spread, n, 'ok' if ok else 'claim under its spread'))
    R = json.load(open(SCRATCH + '/back-wall-hue3.json')); p = R['picks'][1]
    rd = cv2.imread('render-shots/render-match/r01.jpg', cv2.IMREAD_GRAYSCALE)
    if rd is None: print('no render r01.jpg'); return
    S = rd.shape[0]; fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
    C = W(p['u'], p['d'], p['h']); fh = p['fu'] * HU + p['fd'] * HD; fh /= np.linalg.norm(fh)
    pr = math.radians(p['pitch']); f = fh * math.cos(pr) + UP * math.sin(pr)
    right = np.cross(f, UP); right /= np.linalg.norm(right); up = np.cross(right, f)
    def proj_sim(pts):
        P = np.array([(S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f)) for X in [W(*q) for q in pts]])
        return bool((P >= MARGIN).all() and (P <= S - MARGIN).all()), P
    sim = read_frame(rd, proj_sim)
    print('sim through %s: strips (d, face, wall, r):' % p['stem'])
    for k, (a, b, r) in sorted(sim.items()): print('   d %2d-%2d  face %3.0f  wall %3.0f  r %.3f' % (STRIPS[k][0], STRIPS[k][1], a, b, r))
    bright = []; dark = []
    for k, (med, spread, n, ok) in claims.items():
        if not ok or k not in sim: continue
        r = sim[k][2]
        if r > FACTOR * med: bright.append((k, 1 - med / r))
        elif r < med / FACTOR: dark.append((k, r / med))
    print('of %d claimed strips the sim is too bright in %d and too dark in %d' % (sum(1 for v in claims.values() if v[3]), len(bright), len(dark)))
    if len(bright) >= NEEDED:
        o = float(np.median([v for _, v in bright]))
        print('VERDICT: the sim face is too bright from the hall in %d strips: a hall-side black tint on the east pane, opacity %.2f' % (len(bright), o))
    elif len(dark) >= NEEDED:
        print('VERDICT: the sim face is too dark from the hall in %d strips (median %.2fx): recorded, not acted on' % (len(dark), float(np.median([v for _, v in dark]))))
    else:
        print('VERDICT: fewer than %d strips disagree either way: record only' % NEEDED)
    json.dump(dict(claims={str(k): v for k, v in claims.items()}, sim={str(k): v for k, v in sim.items()}, bright=bright, dark=dark, frames=n_frames), open(SCRATCH + '/face-strips.json', 'w'))


if __name__ == '__main__':
    main()
