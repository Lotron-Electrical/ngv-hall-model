"""THE CARPET AGAINST THE LIT GALLERY WALL, FROM BOTH DECKS (2026-09-10, after tools/ends_audit.py).

The whole-elevation audit's east bands h 0 to 2.4 land on the hall carpet at about 19 m from the west
deck and read it at 0.70 to 0.87 of the east gallery's lit band where the render gives 0.34 to 0.38.
That is the largest block left in the audit and it was NOT acted on, because it rested on 23 frames
from one clip, the west's 183 frames never see the floor in that audit (the hall's columns stand in
those rays), and the carpet's brightness is a global lever: dayGainOf('floor') 0.8, which index.html
itself labels "looks, not lux". A global change wants two decks, not one clip. This is the second deck.

THE RULE, FIXED BEFORE THE RUN.
  Patches. A carpet rectangle in front of each end, between the two column rows (d 5.5 to 9.5) and
  clear of the end galleries: WESTPATCH u 8 to 14 (seen from the east deck, b3p, b6gp, b3, b6g),
  EASTPATCH u 35 to 41 (seen from the west deck, b7s, b7sp). h 0.0, the carpet.
  Reference. The same lit band the audit uses, on the gallery that patch's cameras face: the BACK
  region (west wall, h 10 to 12.5) for the east-deck frames, EASTBACK for the west-deck frames.
  Admission. Patch and reference both 20 px inside the frame under the lens model and the pinhole.
  Reading. The 80th percentile of luma in each, the patch divided by the reference: the audit's own
  reading, so the two instruments are the same instrument pointed at a different place.
  Claim, per deck. The median ratio, spread half the interquartile range, at least 20 frames or record
  only. Decision: if BOTH decks put the carpet above the render by more than each one's own spread
  (or 0.10), in the same direction, the floor's day gain moves so the render lands the mean of the
  two claims; if the decks disagree in direction or one is record only, nothing moves and it is said.
  The render. The two picks in render-match.json read the same way.

  python tools/floor_tone.py         # the photographs and the renders
  python tools/floor_tone.py sim     # the renders only
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, BACK, EASTBACK, CLASSES, EAST_CLASSES, W, HU, HD, UP, SCRATCH

PCT, MINPX, MINFRAMES, TOL = 80, 200, 20, 0.10
SIDES = (
    dict(name='west-deck view of the east patch', patch=[(35, 5.5, 0.0), (41, 5.5, 0.0), (41, 9.5, 0.0), (35, 9.5, 0.0)], ref=EASTBACK, classes=EAST_CLASSES, pick='east'),
    dict(name='east-deck view of the west patch', patch=[(8, 5.5, 0.0), (14, 5.5, 0.0), (14, 9.5, 0.0), (8, 9.5, 0.0)], ref=BACK, classes=CLASSES, pick='west'),
)
OUT = SCRATCH + '/floor-tone.json'


def read(img, poly):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if int(m.sum()) < MINPX:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[m == 1]
    return float(np.percentile(g, PCT))


def q(a):
    return float(np.median(a)), float((np.percentile(a, 75) - np.percentile(a, 25)) / 2)


def photo():
    out = {}
    for s in SIDES:
        rs = []
        for cls in s['classes']:
            for stem, (cam, imgpath) in sorted(load_class(cls).items()):
                okp, pp = project(cam, s['patch'])
                okr, pr = project(cam, s['ref'])
                if not (okp and okr):
                    continue
                img = cv2.imread(imgpath)
                if img is None:
                    continue
                a, b = read(img, pp), read(img, pr)
                if a is None or b is None or b < 8:
                    continue
                rs.append(a / b)
        m, sp = q(np.array(rs)) if rs else (float('nan'), float('nan'))
        ok = len(rs) >= MINFRAMES
        print('%s: %d frames, carpet %.3f of the lit band, spread %.3f  %s' % (s['name'], len(rs), m, sp, 'CLAIM' if ok else 'RECORD ONLY'))
        out[s['pick']] = dict(n=len(rs), ratio=m, spread=sp, claim=ok)
    json.dump(out, open(OUT, 'w'))
    return out


def sim():
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    out = {}
    for s in SIDES:
        for i, p in enumerate(R['picks']):
            if p['region'] != s['pick']:
                continue
            rd = cv2.imread('render-shots/render-match/r%02d.jpg' % i)
            if rd is None:
                print('no render r%02d' % i)
                continue
            S = rd.shape[0]
            fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
            C = W(p['u'], p['d'], p['h'])
            fh = p['fu'] * HU + p['fd'] * HD
            fh /= np.linalg.norm(fh)
            pr_ = math.radians(p['pitch'])
            f = fh * math.cos(pr_) + UP * math.sin(pr_)
            right = np.cross(f, UP)
            right /= np.linalg.norm(right)
            up = np.cross(right, f)
            proj = lambda X: (S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f))
            pp = np.array([proj(W(*x)) for x in s['patch']])
            prr = np.array([proj(W(*x)) for x in s['ref']])
            if (pp < 0).any() or (pp > S).any():
                print('%s: the patch is outside the render %s' % (s['name'], p['stem']))
                continue
            a, b = read(rd, pp), read(rd, np.clip(prr, 0, S - 1))
            r = a / max(b, 1)
            print('%s: render %s carpet %.3f of the lit band (carpet %.0f, band %.0f)' % (s['name'], p['stem'], r, a, b))
            out[s['pick']] = r
    return out


def main():
    if not (len(sys.argv) > 1 and sys.argv[1] == 'sim'):
        P = photo()
    else:
        P = json.load(open(OUT))
    S = sim()
    ups = []
    for k in ('west', 'east'):
        if k not in P or k not in S:
            continue
        bar = max(P[k]['spread'], TOL)
        d = P[k]['ratio'] - S[k]
        print('%s: photo %.3f against render %.3f, %+.3f (bar %.2f)%s' % (k, P[k]['ratio'], S[k], d, bar, '' if P[k]['claim'] else '  RECORD ONLY'))
        ups.append((P[k]['claim'], d > bar, d < -bar, P[k]['ratio'], S[k]))
    if len(ups) == 2 and all(u[0] for u in ups) and (all(u[1] for u in ups) or all(u[2] for u in ups)):
        target = float(np.mean([u[3] for u in ups]))
        now = float(np.mean([u[4] for u in ups]))
        print('VERDICT: both decks agree the carpet is %s: land %.3f from %.3f (x%.2f in the render)' % ('too dark' if ups[0][1] else 'too bright', target, now, target / now))
    else:
        print('VERDICT: the decks do not both carry a claim in one direction: nothing moves')


if __name__ == '__main__':
    main()
