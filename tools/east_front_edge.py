"""HOW HIGH THE EAST GALLERY'S FRONT READS DARK FROM THE HALL (2026-09-10, after tools/ends_audit.py).

The audit's east bands say the front of the east gallery reads dark (0.17 to 0.18 of the lit band) up to
plane h 9.2 and is lit from 9.4, which on the face plane is 0.90 to 1.08 m above the deck. The sim's
dark stops at the setback solid's top, 0.755 above the deck, and from there up the hall sees the lit
back wall through clear glass. Two earlier instruments bear on this and disagree with the audit:
end_face_scan.py put the east solid's top on 9.095 (0.755) from the hall's own rays, and rail_band.py
found one flat bar in 29 DECK frames and deleted the drawn handrail. So before anything moves, the
question is put to the frames directly, as a ladder, the way back_wall_top.py asked the back wall.

THE RULE. On the east FACE plane (u 48.056, d 6.5 to 11), rungs 0.05 m tall from h 8.40 (the deck) to
9.90 (past the rail top). Every west-deck frame (b7s, b7sp) that holds the rung and the EASTBACK
reference region 20 px inside the frame. Reading: the 80th percentile of luma in the rung divided by the
80th percentile of the reference, so exposure cancels. The dark band's TOP in a frame is the first rung,
walking up from the deck, whose value exceeds 0.55 of the reference with the rung below it under 0.55.
Claim: the median top over the frames, spread half the interquartile range, at least 15 frames, and the
spread must be under 0.15 m or the frames do not agree on an edge and there is no claim.
The render: the same ladder through the east pick, the same rule.

  python tools/east_front_edge.py          # the photographs and the render
  python tools/east_front_edge.py sim      # the render only
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, EASTBACK, EAST_CLASSES, W, HU, HD, UP, SCRATCH

UF, D0, D1 = 48.056, 6.5, 11.0
H0, H1, STEP = 8.40, 9.90, 0.05
PCT, MINPX, MINFRAMES, FALL, MAXSPREAD = 80, 150, 15, 0.55, 0.15
RUNGS = [round(H0 + i * STEP, 3) for i in range(int(round((H1 - H0) / STEP)))]
OUT = SCRATCH + '/east-front-edge.json'


def rung(h):
    return [(UF, D0, h), (UF, D1, h), (UF, D1, h + STEP), (UF, D0, h + STEP)]


def read(g, poly):
    m = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if int(m.sum()) < MINPX:
        return None
    return float(np.percentile(g[m == 1], PCT))


def top_of(vals, ref):
    prev_dark = False
    for h in RUNGS:
        if h not in vals:
            return None
        lit = vals[h] > FALL * ref
        if prev_dark and lit:
            return h
        prev_dark = not lit
    return None


def photo(classes=EAST_CLASSES, facing=None):
    tops, n = [], 0
    for cls in classes:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            okr, pr = project(cam, EASTBACK)
            ok0, _ = project(cam, rung(H0))
            if not (okr and ok0):
                continue
            if facing is not None and float(cam.R[2] @ HU) < facing:
                continue
            img = cv2.imread(imgpath)
            if img is None:
                continue
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ref = read(g, pr)
            if ref is None or ref < 8:
                continue
            vals = {}
            for h in RUNGS:
                ok, pb = project(cam, rung(h))
                if not ok:
                    break
                v = read(g, pb)
                if v is None:
                    break
                vals[h] = v
            n += 1
            t = top_of(vals, ref)
            if t is not None:
                tops.append(t)
    if not tops:
        print('no frame finds an edge'); return None
    a = np.array(tops)
    m, sp = float(np.median(a)), float((np.percentile(a, 75) - np.percentile(a, 25)) / 2)
    ok = len(tops) >= MINFRAMES and sp < MAXSPREAD
    print('photo: %d of %d frames find a top; the dark front ends at h %.3f (%.3f above the deck), spread %.3f  %s' % (
        len(tops), n, m, m - 8.34, sp, 'CLAIM' if ok else 'RECORD ONLY'))
    json.dump(dict(n=len(tops), top=m, spread=sp, claim=ok), open(OUT, 'w'))
    return m


def sim():
    p = json.load(open(SCRATCH + '/back-wall-hue3.json'))['picks'][1]
    rd = cv2.imread('render-shots/render-match/r01.jpg', 0)
    S = rd.shape[0]
    fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
    C = W(p['u'], p['d'], p['h'])
    fh = p['fu'] * HU + p['fd'] * HD; fh /= np.linalg.norm(fh)
    pr_ = math.radians(p['pitch']); f = fh * math.cos(pr_) + UP * math.sin(pr_)
    right = np.cross(f, UP); right /= np.linalg.norm(right); up = np.cross(right, f)
    proj = lambda pts: np.array([(S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f)) for X in [W(*q) for q in pts]])
    ref = read(rd, np.clip(proj(EASTBACK), 0, S - 1))
    vals = {h: read(rd, proj(rung(h))) for h in RUNGS}
    vals = {h: v for h, v in vals.items() if v is not None}
    t = top_of(vals, ref)
    print('render %s: the dark front ends at %s' % (p['stem'], ('h %.3f (%.3f above the deck)' % (t, t - 8.34)) if t else 'no edge'))
    print('   ' + ' '.join('%.2f:%.2f' % (h, vals[h] / ref) for h in RUNGS if h in vals))
    return t


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else ''
    if a == 'walk':
        # THE TIE-BREAKER: the same ladder from the hall FLOOR, the walk classes facing east (forward along +u over
        # 0.7). A different clip, a different day, a different height, and no deck for anyone to stand on in front.
        photo(classes=('walk',), facing=0.7)
    elif a != 'sim':
        photo()
    sim()
