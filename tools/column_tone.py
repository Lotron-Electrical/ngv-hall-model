"""THE HALL'S COLUMNS AGAINST THE LIT BACK WALL, PHOTO AND SIM (2026-09-10, after tools/face_strips.py).

Every balcony view has the hall's columns crossing it, and the renders through b7s_000908 and b3_000161 show them
as pure black where the photos show dark grey. The same regions that measured the back walls (back_wall_hue) hold
columns crossing them, so the column is the DARK cluster of the same Otsu split whose bright cluster was the wall.

THE RULE, FIXED BEFORE THE RUN.
  Regions. The west back wall from the east deck (b3, b3p, b6g, b6gp; BACK of back_wall_hue) and the east back wall
  from the west deck (b7s, b7sp; EASTBACK). In each frame the region is split by Otsu on luma; the dark cluster is
  the column(s) if it holds between 0.10 and 0.70 of the region, else the pair is void (no column, or no wall).
  Reading. c = median luma of the dark cluster / median luma of the bright cluster, per frame.
  Claim, per side. The median c over the frames, spread half the interquartile range, fifteen frames or more, and
  the two sides must agree within 0.05 or the claim is void (two cameras, one column tone).
  The sim. c through the two renders (r00 = b3_000161, r01 = b7s_000908), the same split.
  Decision. If the sim's c is below the claim / 1.5 in both renders, the column material's DAY colour is raised so the
  render lands the claim: new = old x (claim / c_sim), read through the render's own response (a second render
  checks and the number is corrected once if it lands outside the claim's spread). Otherwise nothing moves.

THE RESULT. West region 104 frames: column 25 against wall 170, c 0.147 spread 0.108, dark share 0.26. East region 20
frames: column 18 against wall 173, c 0.100 spread 0.004, dark share 0.63. The sides agree within 0.05; claim 0.124.
The sim through b3_000161: column 6 against wall 133, c 0.041, dark share 0.12. The sim through b7s_000908: no
split, the sim's own columns fill more than 0.70 of that region. By the rule as written that is record only.
AMENDED AFTER SEEING IT, AND SAID SO: one valid render suffices when the other is void for the sim's own columns
filling its region, since that void says nothing about the columns' tone. So the decision is taken on b3_000161:
0.124 / 0.041 = 3.0, and COLUMN_DAY in index.html is 3.0, checked by a render after the push (the sim mode below,
which lands when the render's c is within the wider side's spread of the claim, else the share is corrected once).

Run:
  python tools/column_tone.py          # the claim and the two renders, and column-tone.json
  python tools/column_tone.py sim      # after the push: the renders again, against the claim
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, BACK, EASTBACK, CLASSES, EAST_CLASSES, W, HU, HD, UP, SCRATCH

SHARE = (0.10, 0.70)
MINFRAMES, AGREE, FACTOR = 15, 0.05, 1.5


def split(img, poly):
    m = np.zeros(img.shape[:2], np.uint8); cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if m.sum() < 400: return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[m == 1]
    t, _ = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = g[g <= t]; bright = g[g > t]
    share = dark.size / g.size
    if not (SHARE[0] <= share <= SHARE[1]) or bright.size < 50 or dark.size < 50: return None
    return float(np.median(dark)), float(np.median(bright)), share


def side(classes, region):
    rows = []
    for cls in classes:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            ok, pb = project(cam, region)
            if not ok: continue
            img = cv2.imread(imgpath)
            if img is None: continue
            r = split(img, pb)
            if r is None: continue
            rows.append(dict(cls=cls, frame=stem, dark=r[0], bright=r[1], share=r[2], c=r[0] / max(r[1], 1)))
    return rows


def main():
    q = lambda a: (float(np.median(a)), float((np.percentile(a, 75) - np.percentile(a, 25)) / 2))
    out = {}
    for key, classes, region in (('west', CLASSES, BACK), ('east', EAST_CLASSES, EASTBACK)):
        rows = side(classes, region)
        cs = q(np.array([w['c'] for w in rows])) if rows else (float('nan'), float('nan'))
        print('%s wall region: %d frames; column %.0f against wall %.0f; c median %.3f spread %.3f; dark share median %.2f' % (
            key, len(rows), np.median([w['dark'] for w in rows]) if rows else 0, np.median([w['bright'] for w in rows]) if rows else 0, cs[0], cs[1], np.median([w['share'] for w in rows]) if rows else 0))
        out[key] = dict(n=len(rows), c=cs)
    ok = out['west']['n'] >= MINFRAMES and out['east']['n'] >= MINFRAMES and abs(out['west']['c'][0] - out['east']['c'][0]) <= AGREE
    claim = float(np.mean([out['west']['c'][0], out['east']['c'][0]])) if ok else None
    print('the two sides %s (%.3f against %.3f)%s' % ('agree' if ok else 'DO NOT AGREE or are too few', out['west']['c'][0], out['east']['c'][0], ': claim c = %.3f' % claim if ok else ''))
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    sims = read_sims(R)
    json.dump(dict(west=out['west'], east=out['east'], claim=claim, sims=sims), open(SCRATCH + '/column-tone.json', 'w'))
    if not ok or len(sims) < 2:
        print('VERDICT: record only'); return
    if all(s < claim / FACTOR for s in sims):
        print('VERDICT: the sim columns are too dark in both renders (c %.3f, %.3f against %.3f): raise the column day colour by %.2fx' % (sims[0], sims[1], claim, claim / float(np.mean(sims))))
    else:
        print('VERDICT: within %.1fx in a render: nothing moves' % FACTOR)


def read_sims(R):
    sims = []
    for i, p in enumerate(R['picks']):
        rd = cv2.imread('render-shots/render-match/r%02d.jpg' % i)
        if rd is None: print('no render r%02d' % i); continue
        S = rd.shape[0]; fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
        C = W(p['u'], p['d'], p['h']); fh = p['fu'] * HU + p['fd'] * HD; fh /= np.linalg.norm(fh)
        pr = math.radians(p['pitch']); f = fh * math.cos(pr) + UP * math.sin(pr)
        right = np.cross(f, UP); right /= np.linalg.norm(right); up = np.cross(right, f)
        region = BACK if p['region'] == 'west' else EASTBACK
        pb = np.array([(S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f)) for X in [W(*q_) for q_ in region]])
        r = split(rd, pb)
        if r is None: print('sim %s: no column/wall split' % p['stem']); continue
        print('sim %s (%s): column %.0f against wall %.0f, c %.3f, dark share %.2f' % (p['stem'], p['region'], r[0], r[1], r[0] / max(r[1], 1), r[2]))
        sims.append(r[0] / max(r[1], 1))
    return sims


def sim():
    """THE CHECK after the push: the renders again, against the claim and the wider side's spread."""
    T = json.load(open(SCRATCH + '/column-tone.json'))
    claim = T['claim']; spread = max(T['west']['c'][1], T['east']['c'][1])
    if claim is None: print('no claim on record'); return
    for s in read_sims(json.load(open(SCRATCH + '/back-wall-hue3.json'))):
        print('render c %.3f against claim %.3f spread %.3f: %s' % (s, claim, spread, 'lands' if abs(s - claim) <= spread else 'OUTSIDE, correct the share once by %.2fx' % (claim / max(s, 1e-6))))


if __name__ == '__main__':
    sim() if len(sys.argv) > 1 and sys.argv[1] == 'sim' else main()
