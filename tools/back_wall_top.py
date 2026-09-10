"""HOW HIGH THE WEST GALLERY'S LIT BACK WALL REACHES, PHOTO AND SIM (2026-09-10, after tools/column_tone.py).

The column-tone check exposed this and named it: read through the render of b3_000161, the BACK region carries
brick from about h 11.4 up (luma 85) where the same region in 183 east-deck photographs is one lit cream all the
way to h 12.5. Something in the sim stops the lit wall lower than the hall does. That is a height, and a height
is measurable from the same frames the hue claim already used.

THE RULE, FIXED BEFORE THE RUN.
  The ladder. On the west back wall plane u 0.356, strips 0.10 m tall from h 9.6 to 13.4, each spanning d 3.0 to
  11.0 (the BACK region's own d span, clear of the vent at d 11.8-12.9, the niche at 12.2-13.3 and the cases).
  Frames. The east deck's four classes (b3p, b6gp, b3, b6g), the same set the hue claim read.
  Admission. A strip is read only when its quadrilateral lies 20 px inside the frame under BOTH the lens model
  and the unrolled pinhole (the fold guard the hue tool uses) and covers at least 200 px.
  Reading past the columns. The hall's columns cross this region in every frame, so a strip's value is the 80th
  PERCENTILE of its luma, which is the lit wall between the columns, not the median.
  The reference. Each frame carries its own exposure, so each frame is read against ITSELF: ref = the median of
  its strips between h 10.0 and 11.0, the band the hue claim already established is one lit cream.
  The top. Walking up from 9.6, the first strip whose value falls under 0.55 x ref with a strip below it above
  0.55 x ref. That is the crossing. A frame with no crossing below 13.4 reports NO TOP SEEN and is counted apart;
  a frame whose ladder breaks (an unreadable strip) below its crossing is dropped.
  The claim. The median crossing over the frames, spread half the interquartile range, at least 20 frames or
  record only. Control: the frames that see a top must be at least 0.60 of the frames whose ladder reaches 13.4,
  or the feature is not in view and there is no claim.
  The sim. The render through b3_000161 (render-shots/render-match/r00.jpg, the west pick), the same ladder read
  through the unrolled pinhole, the same 80th percentile, the same 0.55 x ref.
  The decision. If the sim's top lies below the claim by more than the claim's spread plus the ladder's own step
  (0.10), the sim stops the lit wall too low and the geometry that stops it is named and moved so the render
  lands the claim. If it lies within that, or above it, nothing moves.

THE FIRST RUN. 114 east-deck frames see a top and 69 reach 13.4 without one (share 0.62 against a bar of 0.60):
the west gallery's lit back wall ends at h 12.90, spread 0.25. CLAIM. The render through b3_000161 reported NO TOP
by the same rule, and the rule was the thing that failed, not the render: its ladder reads 133 from h 10.1 to 11.4
and 85 from 11.5 up, a step to 0.64 of the reference where the bar was 0.55. In the photograph the lit wall gives
way to something nearly black and 0.55 catches it; in the sim it gives way to brick at 0.64 and 0.55 cannot.

THE SECOND RUN, THE CROSSING READ AS THE STRONGEST FALLING STEP, AMENDED AFTER SEEING THAT AND SAID SO. The top is
the rung whose value divided by the rung below it is the smallest in the ladder, provided that ratio is under 0.85
(a real step, not a gradient) and the rung below stands above 0.55 x ref (the wall is still lit under it). One
instrument now reads both pictures, and a claim under an amended rule is weaker than one under the blind rule.
  A CONTROL THE FIRST RUN DID NOT HAVE: the EAST gallery's back wall read the same way from the WEST deck (b7s,
  b7sp, the EASTBACK region), photo and the render through b7s_000908. index.html draws the two ends from one
  loop, so a defect in that loop must show at both ends; a difference between them would say the defect is not
  in the shared line.

THE SECOND RUN'S RESULT. West: 35 frames see a step and 148 reach 13.4 without one, share 0.19 against a bar of
0.60, so RECORD ONLY under this rule; the 35 that do agree put the top on h 12.90, spread 0.05, the same number the
blind rule got from 114 frames with its control passing. Two rules, two frame sets, one answer to the centimetre.
East: 21 frames see a step and 2 do not, share 0.91; the top is h 13.20, spread 0.10. CLAIM.
THE RENDERS BEFORE THE CHANGE: west 11.50, east 11.20. Both ends stop the lit wall about two metres low, and the
two ends are drawn by one loop, which is what a shared defect looks like.
WHAT STOPS IT, NAMED BY A RAYCAST AND NOT BY THE PICTURE (tools/backtop_probe.mjs). From the b3_000161 eye the ray
to the back wall is clear at h 11.00 and is caught by the mesh 'end-wall' at 44.1 m from h 11.20 up, with
'gallery-back' unseen 3.8 m behind it. index.html drew that quad from W.head 11.090 to W.top, sealing the void the
same file says elsewhere is open to the canopy.
WHAT MOVED: ENDW.stoneBase {west 12.38, east 12.93}, each mapped from its own end's claim through its own pick's
geometry (base_new = base_old + t x (claim - read), t the fraction of the eye-to-wall run standing at the face:
0.9198 west, 0.9210 east). A locus, not a material: the ladder finds where the lit wall stops being lit and cannot
say whether stone begins there.
THE CHECK, RENDERED AFTER THE PUSH: west 12.90 against the claim 12.90 (step to 0.82), east 13.20 against 13.20
(step to 0.77). Both land inside spread + one rung; no correction.
WHAT THE CHECK EXPOSES NEXT, recorded and not measured: over the crossing the render carries stone at luma 94 to 98
where the photograph goes nearly black. The height is now right and the tone above it is not.

Run:
  python tools/back_wall_top.py           # the first run: the 0.55 ladder, west only
  python tools/back_wall_top.py sim       # the render only, against the claim on record
  python tools/back_wall_top.py two       # the second run: strongest-step crossing, west and east, photo and sim
  python tools/back_wall_top.py sim2      # after the push: the renders only, against the claims on record
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, CLASSES, EAST_CLASSES, W, HU, HD, UP, SCRATCH

UWALL = 0.356
D0, D1 = 3.0, 11.0
H0, H1, STEP = 9.6, 13.4, 0.10
REF_BAND = (10.0, 11.0)
PCT = 80
FALL = 0.55
MINPX, MINFRAMES, SEEN_SHARE = 200, 20, 0.60
OUT = SCRATCH + '/back-wall-top.json'
STEP_BAR = 0.85          # the second run: a ratio under this is a step, over it a gradient
CLAIMS = {'west': (12.90, 0.25), 'east': (13.20, 0.10)}   # the second run's record, for sim2

RUNGS = [round(H0 + i * STEP, 3) for i in range(int(round((H1 - H0) / STEP)))]


WEST = dict(u=UWALL, d0=D0, d1=D1, pick='west')
# the second run's control: the east gallery's back wall from the west deck, the EASTBACK region's plane and d span
EAST = dict(u=51.894, d0=6.5, d1=11.0, pick='east')


def strip(h, side=None):
    s = side or WEST
    return [(s['u'], s['d0'], h), (s['u'], s['d1'], h), (s['u'], s['d1'], h + STEP), (s['u'], s['d0'], h + STEP)]


def read(img, poly):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if int(m.sum()) < MINPX:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[m == 1] if img.ndim == 3 else img[m == 1]
    return float(np.percentile(g, PCT)), int(g.size)


def crossing(vals):
    """vals: rung -> value, contiguous from H0. Returns (top or None, the height the ladder reached)."""
    hs = []
    for h in RUNGS:
        if h not in vals:
            break
        hs.append(h)
    if not hs:
        return None, None
    band = [vals[h] for h in hs if REF_BAND[0] <= h < REF_BAND[1]]
    if len(band) < 5:
        return None, None
    ref = float(np.median(band))
    reached = hs[-1] + STEP
    prev_ok = False
    for h in hs:
        hot = vals[h] > FALL * ref
        if prev_ok and not hot:
            return h, reached
        prev_ok = prev_ok or hot
    return None, reached


def step_crossing(vals):
    """THE SECOND RUN. The top is the rung with the smallest ratio to the rung below it, that ratio under
    STEP_BAR, with the rung below still lit (over FALL x ref). Returns (top or None, reached, ratio)."""
    hs = []
    for h in RUNGS:
        if h not in vals:
            break
        hs.append(h)
    if len(hs) < 2:
        return None, None, None
    band = [vals[h] for h in hs if REF_BAND[0] <= h < REF_BAND[1]]
    if len(band) < 5:
        return None, None, None
    ref = float(np.median(band))
    reached = hs[-1] + STEP
    best = None
    for i in range(1, len(hs)):
        lo, hi = vals[hs[i - 1]], vals[hs[i]]
        if lo <= FALL * ref:
            continue
        r = hi / max(lo, 1e-6)
        if best is None or r < best[1]:
            best = (hs[i], r)
    if best is None or best[1] >= STEP_BAR:
        return None, reached, (best[1] if best else None)
    return best[0], reached, best[1]


def ladder(cam, img, side):
    vals = {}
    for h in RUNGS:
        ok, pb = project(cam, strip(h, side))
        if not ok:
            break
        r = read(img, pb)
        if r is None:
            break
        vals[h] = r[0]
    return vals


def sim_vals(pick, rd, side):
    S = rd.shape[0]
    fr = S / 2 / math.tan(math.radians(pick['sqvfov'] / 2))
    C = W(pick['u'], pick['d'], pick['h'])
    fh = pick['fu'] * HU + pick['fd'] * HD
    fh /= np.linalg.norm(fh)
    pr = math.radians(pick['pitch'])
    f = fh * math.cos(pr) + UP * math.sin(pr)
    right = np.cross(f, UP)
    right /= np.linalg.norm(right)
    up = np.cross(right, f)
    proj = lambda X: (S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f))
    vals = {}
    for h in RUNGS:
        Pp = np.array([proj(W(*pt)) for pt in strip(h, side)])
        if (Pp < 0).any() or (Pp > S).any():
            break
        r = read(rd, Pp)
        if r is None:
            break
        vals[h] = r[0]
    return vals


def two():
    """The second run: both ends, photo and render, one instrument."""
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    out = {}
    for name, side, classes in (('west', WEST, CLASSES), ('east', EAST, EAST_CLASSES)):
        rows, noTop = [], 0
        for cls in classes:
            for stem, (cam, imgpath) in sorted(load_class(cls).items()):
                ok0, _ = project(cam, strip(REF_BAND[0], side))
                if not ok0:
                    continue
                img = cv2.imread(imgpath)
                if img is None:
                    continue
                top, reached, r = step_crossing(ladder(cam, img, side))
                if reached is None:
                    continue
                if top is None:
                    if reached >= H1:
                        noTop += 1
                    continue
                rows.append(dict(cls=cls, frame=stem, top=top, ratio=r))
        seen = len(rows)
        share = seen / max(seen + noTop, 1)
        cl = q(np.array([w['top'] for w in rows])) if rows else (float('nan'), float('nan'))
        ok = seen >= MINFRAMES and share >= SEEN_SHARE
        print('%s photo: %d frames see a step, %d reach h %.1f without one (share %.2f); the lit wall ends at h %.2f spread %.2f  %s' % (
            name, seen, noTop, H1, share, cl[0], cl[1], 'CLAIM' if ok else 'RECORD ONLY'))
        out[name] = dict(n=seen, noTop=noTop, claim=(cl if ok else None))
        for i, p in enumerate(R['picks']):
            if p['region'] != side['pick']:
                continue
            rd = cv2.imread('render-shots/render-match/r%02d.jpg' % i)
            if rd is None:
                print('   no render r%02d' % i)
                continue
            v = sim_vals(p, rd, side)
            top, reached, r = step_crossing(v)
            said = ('the lit wall ends at h %.2f (step to %.2f)' % (top, r)) if top else (
                'no step under %.2f (best %s)' % (STEP_BAR, ('%.2f' % r) if r else 'none'))
            print('   sim %s: ladder to h %.2f, %s' % (p['stem'], reached or 0, said))
            print('      %s' % json.dumps({str(k): round(vv, 1) for k, vv in v.items()}))
            out[name]['sim'] = top
            if ok and top:
                gap = cl[0] - top
                bar = cl[1] + STEP
                print('   VERDICT %s: the sim ends %.2f m %s the photo (bar %.2f): %s' % (
                    name, abs(gap), 'below' if gap > 0 else 'above', bar,
                    'THE SIM STOPS THE LIT WALL TOO LOW' if gap > bar else 'within the bar, nothing moves'))
    json.dump(out, open(SCRATCH + '/back-wall-top2.json', 'w'))
    return out


def sim2():
    """THE CHECK after the push: the two renders read by the second run's rule against the claims on record.
    No photograph is opened, so this is cheap enough to run after every change to the end walls."""
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    for name, side in (('west', WEST), ('east', EAST)):
        for i, p in enumerate(R['picks']):
            if p['region'] != side['pick']:
                continue
            rd = cv2.imread('render-shots/render-match/r%02d.jpg' % i)
            if rd is None:
                print('no render r%02d' % i)
                continue
            v = sim_vals(p, rd, side)
            top, reached, r = step_crossing(v)
            c, sp = CLAIMS[name]
            bar = sp + STEP
            said = ('ends at h %.2f (step to %.2f)' % (top, r)) if top else ('no step under %.2f' % STEP_BAR)
            print('%s sim %s: %s  against the claim %.2f spread %.2f' % (name, p['stem'], said, c, sp))
            print('   %s' % json.dumps({str(k): round(vv, 1) for k, vv in v.items()}))
            if top:
                print('   %s (bar %.2f, off by %+.2f)' % ('LANDS' if abs(top - c) <= bar else 'OUTSIDE: correct the base once', bar, top - c))


def photo():
    rows, noTop = [], 0
    for cls in CLASSES:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            ok0, _ = project(cam, strip(REF_BAND[0]))
            if not ok0:
                continue
            img = cv2.imread(imgpath)
            if img is None:
                continue
            vals = {}
            for h in RUNGS:
                ok, pb = project(cam, strip(h))
                if not ok:
                    break
                r = read(img, pb)
                if r is None:
                    break
                vals[h] = r[0]
            top, reached = crossing(vals)
            if reached is None:
                continue
            if top is None:
                if reached >= H1:
                    noTop += 1
                continue
            rows.append(dict(cls=cls, frame=stem, top=top, reached=reached))
    return rows, noTop


def q(a):
    return float(np.median(a)), float((np.percentile(a, 75) - np.percentile(a, 25)) / 2)


def sim_ladder(pick, path):
    rd = cv2.imread(path)
    if rd is None:
        return None
    S = rd.shape[0]
    fr = S / 2 / math.tan(math.radians(pick['sqvfov'] / 2))
    C = W(pick['u'], pick['d'], pick['h'])
    fh = pick['fu'] * HU + pick['fd'] * HD
    fh /= np.linalg.norm(fh)
    pr = math.radians(pick['pitch'])
    f = fh * math.cos(pr) + UP * math.sin(pr)
    right = np.cross(f, UP)
    right /= np.linalg.norm(right)
    up = np.cross(right, f)
    proj = lambda X: (S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f))
    vals = {}
    for h in RUNGS:
        P = np.array([proj(W(*p)) for p in strip(h)])
        if (P < 0).any() or (P > S).any():
            break
        r = read(rd, P)
        if r is None:
            break
        vals[h] = r[0]
    top, reached = crossing(vals)
    return dict(top=top, reached=reached, vals={str(k): round(v, 1) for k, v in vals.items()})


def main(simonly=False):
    if not simonly:
        rows, noTop = photo()
        seen = len(rows)
        share = seen / max(seen + noTop, 1)
        tops = np.array([r['top'] for r in rows]) if rows else np.array([])
        cl = q(tops) if rows else (float('nan'), float('nan'))
        print('%d frames see a top, %d reach h %.1f without one (share seen %.2f)' % (seen, noTop, H1, share))
        if rows:
            print('   by class: %s' % ', '.join('%s %d' % (c, sum(1 for r in rows if r['cls'] == c)) for c in CLASSES))
            print('   the lit wall ends at h %.2f, spread %.2f' % cl)
        ok = seen >= MINFRAMES and share >= SEEN_SHARE
        print('   %s' % ('CLAIM' if ok else 'RECORD ONLY (too few frames, or the top is not in view)'))
        json.dump(dict(n=seen, noTop=noTop, claim=cl if ok else None, rows=rows), open(OUT, 'w'))
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    T = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for i, p in enumerate(R['picks']):
        if p['region'] != 'west':
            continue
        s = sim_ladder(p, 'render-shots/render-match/r%02d.jpg' % i)
        if s is None:
            print('no render r%02d' % i)
            continue
        end = ('the lit wall ends at h %.2f' % s['top']) if s['top'] else 'NO TOP: lit to the end of the ladder'
        print('sim %s: ladder reaches h %.2f, %s' % (p['stem'], s['reached'], end))
        print('   %s' % json.dumps(s['vals']))
        c = T.get('claim')
        if c and s['top']:
            gap = c[0] - s['top']
            bar = c[1] + STEP
            print('VERDICT: the sim ends %.2f m %s the claim %.2f (bar %.2f): %s' % (
                abs(gap), 'below' if gap > 0 else 'above', c[0], bar,
                'THE SIM STOPS THE LIT WALL TOO LOW' if gap > bar else 'within the bar, nothing moves'))
        elif c:
            print('VERDICT: the sim shows no top below h %.1f where the photos end at %.2f: nothing moves' % (H1, c[0]))


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else ''
    (two() if a == 'two' else sim2() if a == 'sim2' else main(a == 'sim'))
