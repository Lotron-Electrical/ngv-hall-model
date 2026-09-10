"""THE EAST FACE'S DARKNESS FROM THE HALL (2026-09-10, after tools/back_wall_hue.py).

From the deck side the east parapet's glass was read for what it transmits (tools/face_band.py): a tinted band to
9.095 with opacity 0.39 against a clear pane above it. From the west deck (b7s, b7sp, 44 m across the hall) the
photo shows the whole face, deck floor to rail top, as one dark band under the lit cream back wall, while the sim
shows that wall through the upper pane. This measures the face against the wall above it, photo and render alike.

THE RULE, FIXED BEFORE THE RUN.
  Regions, both on the east gallery, d 3 to 11: FACE = the parapet face (u 48.056) from 8.45 to 9.75, the deck floor's
  splash to just under the rail top; WALL = the back wall (u 51.894) from 10.5 to 12.5. Both 20 px inside the frame
  under the lens model and the pinhole.
  Reading. The hall's columns cross both regions from that deck, so each region is split by Otsu's threshold on
  luma and the BRIGHT cluster's median luma is the region's (tools/back_wall_hue.bright_rgb); its share of the
  region must be 0.30 or more or the pair is void. r = FACE / WALL, per frame.
  Claim. The median r over the frames, spread half the interquartile range; 15 frames or more.
  The sim. r through the render of b7s_000908 (render-shots/render-match/r01.jpg from back_wall_hue photo3), the
  same regions through the unrolled pinhole, the same split.
  Decision. If the sim's r exceeds the claim by more than 1.5x, the east face is too transparent from the hall: its
  glass above the band takes a hall-side tint whose opacity o makes (1 - o) x WALL_sim + o x tint = claim x WALL_sim,
  as one material for the east face only, and a second render checks it. If the sim's r is within 1.5x or below,
  nothing moves. The deck-side ratio of band to pane (0.847) is relative and is not touched by a uniform tint.

THE RESULT. One frame of 23 passed the share control: in the others the face's bright cluster held under 0.30 of
the region, because the face is dark with a small lit patch where the gallery's interior shows through the glass
near d 3 (see east-elevation.jpg), and Otsu's split on a dark region with one bright patch leaves the patch. The
one survivor read face 164 against wall 162, r 1.013; the sim through b7s_000908 read face 43 against wall 81,
r 0.533. One frame is not a claim. RECORD ONLY: nothing moves. What it does say is that the face from the hall is
not one dark band: part of it shows the lit interior, and the sim's face there reads about half its wall. The next
instrument would read the face in strips along d, each strip its own median without a split.

Run:
  python tools/face_from_hall.py
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, bright_rgb, W, HU, HD, UP, SCRATCH

FACE = [(48.056, 3.0, 8.45), (48.056, 11.0, 8.45), (48.056, 11.0, 9.75), (48.056, 3.0, 9.75)]
WALL = [(51.894, 3.0, 10.5), (51.894, 11.0, 10.5), (51.894, 11.0, 12.5), (51.894, 3.0, 12.5)]
CLASSES = ('b7s', 'b7sp')
SHARE, MINFRAMES, FACTOR = 0.30, 15, 1.5


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def main():
    rows = []
    for cls in CLASSES:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            okf, pf = project(cam, FACE); okw, pw = project(cam, WALL)
            if not (okf and okw): continue
            img = cv2.imread(imgpath)
            if img is None: continue
            a = bright_rgb(img, pf); b = bright_rgb(img, pw)
            if a is None or b is None or a[3] < SHARE or b[3] < SHARE: continue
            rows.append(dict(cls=cls, frame=stem, face=luma(a), wall=luma(b), r=luma(a) / max(luma(b), 1), share_face=a[3], share_wall=b[3]))
    rs = np.array([w['r'] for w in rows])
    med = float(np.median(rs)); spread = float((np.percentile(rs, 75) - np.percentile(rs, 25)) / 2)
    print('photo: %d frames; face luma median %.0f, wall %.0f, r median %.3f spread %.3f -> %s' % (len(rows), np.median([w['face'] for w in rows]), np.median([w['wall'] for w in rows]), med, spread, 'CLAIM' if len(rows) >= MINFRAMES else 'RECORD ONLY'))
    R = json.load(open(SCRATCH + '/back-wall-hue3.json')); p = R['picks'][1]
    rd = cv2.imread('render-shots/render-match/r01.jpg')
    if rd is None: print('no render r01.jpg'); return
    S = rd.shape[0]; fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
    C = W(p['u'], p['d'], p['h']); fh = p['fu'] * HU + p['fd'] * HD; fh /= np.linalg.norm(fh)
    pr = math.radians(p['pitch']); f = fh * math.cos(pr) + UP * math.sin(pr)
    right = np.cross(f, UP); right /= np.linalg.norm(right); up = np.cross(right, f)
    proj = lambda pts: np.array([(S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f)) for X in [W(*q) for q in pts]])
    a = bright_rgb(rd, proj(FACE)); b = bright_rgb(rd, proj(WALL))
    if a is None or b is None: print('sim: a region left the square'); return
    rs_sim = luma(a) / max(luma(b), 1)
    print('sim through %s: face luma %.0f (share %.2f), wall %.0f (share %.2f), r %.3f' % (p['stem'], luma(a), a[3], luma(b), b[3], rs_sim))
    if len(rows) < MINFRAMES: print('VERDICT: record only'); return
    if rs_sim > FACTOR * med:
        o = 1 - med * luma(b) / max(luma(a), 1)   # the opacity of a black tint that brings the sim face to the claim, given what shows through now
        print('VERDICT: the sim face is %.1fx the photo ratio: tint the east face from the hall side; a black tint at opacity %.2f over what now shows would land the claim' % (rs_sim / med, o))
    else:
        print('VERDICT: within %.1fx (%.2fx): nothing moves' % (FACTOR, rs_sim / max(med, 1e-6)))
    json.dump(dict(rows=rows, median=med, spread=spread, sim=rs_sim, sim_face=luma(a), sim_wall=luma(b)), open(SCRATCH + '/face-from-hall.json', 'w'))


if __name__ == '__main__':
    main()
