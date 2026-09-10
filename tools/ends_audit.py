"""BOTH ENDS OF THE HALL, FLOOR TO CEILING, PHOTOGRAPH AGAINST RENDER, BAND BY BAND.

Lloyd, 2026-09-10: "keep going until both ends of the hall are correct including from the floor up to
the ceiling and in between". This is the instrument that decides when that is true, and it is the
verify command on the locked goal, so it must be able to come back NEGATIVE.

WHY A PROFILE AND NOT A LIST OF FEATURES. Every tool in this repo so far has measured ONE feature at
a time: a head, a sill, a station, a hue, a top. A hall end is not a list of features, it is a
continuous elevation, and the parts nobody has named are exactly the parts nobody has checked. So this
reads the WHOLE height as one profile and asks the only question that does not need to know what each
band is made of: does the photograph's tone profile up the end match the render's?

THE RULE.
  The ladder. On each end's back-wall plane (west u 0.356, east u 51.894), bands 0.20 m tall from
  h 0.0 to 13.4, spanning the d range that end's frames can hold (west d 3.0 to 11.0, east 6.5 to 11.0,
  the spans back_wall_hue.py established as clear of the vent, the niche, the cases and the corner).
  A band is a horizontal slice of the ELEVATION as the opposite deck sees it: the ray may land on the
  parapet, the deck, the recess, the back wall or the stone, and the audit does not need to know which.
  Frames. West: the east deck (b3p, b6gp, b3, b6g). East: the west deck (b7s, b7sp).
  Admission. A band is read only when its quadrilateral lies 20 px inside the frame under BOTH the lens
  model and the unrolled pinhole (the fold guard) and covers at least 200 px.
  Reading. The 80th percentile of luma inside the band, which reads the lit surface between the hall's
  columns rather than the columns.
  Exposure. Every band is divided by its own frame's reference band (h 10.0 to 11.0, the lit cream that
  back_wall_hue.py measured in 183 frames and that both pictures carry), so nothing here depends on a
  camera's exposure or on the render's tone map at the top end.
  The claim, per band. The median ratio over the frames, spread half the interquartile range. At least
  20 frames or the band is UNMEASURED and cannot pass or fail.
  The render. The same ladder through the same pose (b3_000161 west, b7s_000908 east), the same
  percentile, the same reference band.
  The verdict, per band. PASS when |render - photo| <= max(the band's own spread, TOL). Else FAIL.
  The verdict, per end. Every measured band passes AND at least MIN_COVER of the bands are measured, so
  an audit cannot be passed by measuring nothing.

  python tools/ends_audit.py            # the audit; exit 0 only when both ends pass
  python tools/ends_audit.py --refresh  # re-read the photographs (slow) and cache the profile
  python tools/ends_audit.py -v         # every band, not just the failures

THE RENDERS MUST BE NEWER THAN index.html, or the audit refuses: an audit of a stale picture of the sim
is worse than no audit. Re-shoot with
  bash ~/scripts/headless-chrome.sh start 9334
  node tools/serve.js --port 8877 &
  cd render-shots && CDP_PORT=9334 SHOT_URL=http://127.0.0.1:8877/index.html node ../tools/render_match.mjs
"""
import os, sys, json, math, time
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, CLASSES, EAST_CLASSES, W, HU, HD, UP, SCRATCH

H0, H1, STEP = 0.0, 13.4, 0.20
REF_BAND = (10.0, 11.0)
PCT = 80
MINPX, MINFRAMES = 200, 20
TOL = 0.10           # a band inside this of the photograph is right, whatever its own spread says
MIN_COVER = 0.70     # at least this share of the bands must be measured, or the end cannot pass
CACHE = SCRATCH + '/ends-audit-photo.json'

RUNGS = [round(H0 + i * STEP, 3) for i in range(int(round((H1 - H0) / STEP)))]
ENDS = (
    dict(name='west', u=0.356, d0=3.0, d1=11.0, classes=CLASSES, pick='west'),
    dict(name='east', u=51.894, d0=6.5, d1=11.0, classes=EAST_CLASSES, pick='east'),
)


def band(h, e):
    return [(e['u'], e['d0'], h), (e['u'], e['d1'], h), (e['u'], e['d1'], h + STEP), (e['u'], e['d0'], h + STEP)]


def read(img, poly):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    if int(m.sum()) < MINPX:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[m == 1] if img.ndim == 3 else img[m == 1]
    return float(np.percentile(g, PCT))


def profile_from_vals(vals):
    """vals: rung -> luma. Returns rung -> ratio against the frame's own reference band, or None."""
    ref = [vals[h] for h in vals if REF_BAND[0] <= h < REF_BAND[1]]
    if len(ref) < 3:
        return None
    r = float(np.median(ref))
    if r < 8:
        return None
    return {h: vals[h] / r for h in vals}


def photo_profiles():
    out = {}
    for e in ENDS:
        per = {}
        n = 0
        for cls in e['classes']:
            for stem, (cam, imgpath) in sorted(load_class(cls).items()):
                ok0, _ = project(cam, band(REF_BAND[0], e))
                if not ok0:
                    continue
                img = cv2.imread(imgpath)
                if img is None:
                    continue
                vals = {}
                for h in RUNGS:
                    ok, pb = project(cam, band(h, e))
                    if not ok:
                        continue
                    v = read(img, pb)
                    if v is not None:
                        vals[h] = v
                p = profile_from_vals(vals)
                if p is None:
                    continue
                n += 1
                for h, r in p.items():
                    per.setdefault(h, []).append(r)
        out[e['name']] = dict(n=n, bands={str(h): [float(np.median(v)),
                                                   float((np.percentile(v, 75) - np.percentile(v, 25)) / 2),
                                                   len(v)] for h, v in per.items()})
        print('%s: %d frames carry a profile, %d bands hold %d frames or more' % (
            e['name'], n, sum(1 for v in per.values() if len(v) >= MINFRAMES), MINFRAMES))
    return out


def render_profile(e):
    R = json.load(open(SCRATCH + '/back-wall-hue3.json'))
    for i, p in enumerate(R['picks']):
        if p['region'] != e['pick']:
            continue
        path = 'render-shots/render-match/r%02d.jpg' % i
        rd = cv2.imread(path)
        if rd is None:
            return None, 'no render at %s' % path
        if os.path.getmtime(path) < os.path.getmtime('index.html'):
            return None, 'the render %s is older than index.html: re-shoot it' % path
        S = rd.shape[0]
        fr = S / 2 / math.tan(math.radians(p['sqvfov'] / 2))
        C = W(p['u'], p['d'], p['h'])
        fh = p['fu'] * HU + p['fd'] * HD
        fh /= np.linalg.norm(fh)
        pr = math.radians(p['pitch'])
        f = fh * math.cos(pr) + UP * math.sin(pr)
        right = np.cross(f, UP)
        right /= np.linalg.norm(right)
        up = np.cross(right, f)
        proj = lambda X: (S / 2 + fr * ((X - C) @ right) / ((X - C) @ f), S / 2 - fr * ((X - C) @ up) / ((X - C) @ f))
        vals = {}
        for h in RUNGS:
            P = np.array([proj(W(*q)) for q in band(h, e)])
            if (P < -2).any() or (P > S + 2).any():
                continue
            v = read(rd, np.clip(P, 0, S - 1))
            if v is not None:
                vals[h] = v
        pf = profile_from_vals(vals)
        return pf, (None if pf else 'the render carries no reference band')
    return None, 'no pick for %s' % e['name']


def main():
    verbose = '-v' in sys.argv
    if '--refresh' in sys.argv or not os.path.exists(CACHE):
        json.dump(photo_profiles(), open(CACHE, 'w'))
    P = json.load(open(CACHE))
    bad = 0
    for e in ENDS:
        ph = P[e['name']]['bands']
        rf, err = render_profile(e)
        if rf is None:
            print('%s: CANNOT AUDIT: %s' % (e['name'], err))
            bad += 1
            continue
        fails, measured, unmeasured = [], 0, []
        for h in RUNGS:
            k = str(h)
            if k not in ph or ph[k][2] < MINFRAMES:
                unmeasured.append(h)
                continue
            if h not in rf:
                fails.append((h, ph[k][0], None, ph[k][1]))
                measured += 1
                continue
            measured += 1
            d = abs(rf[h] - ph[k][0])
            bar = max(ph[k][1], TOL)
            if d > bar:
                fails.append((h, ph[k][0], rf[h], bar))
            elif verbose:
                print('   h %5.2f  photo %.3f  render %.3f  pass' % (h, ph[k][0], rf[h]))
        cover = measured / len(RUNGS)
        print('%s: %d bands of %d measured (cover %.2f, bar %.2f), %d fail' % (
            e['name'], measured, len(RUNGS), cover, MIN_COVER, len(fails)))
        for h, a, b, bar in fails:
            print('   h %5.2f to %5.2f  photo %.3f  render %s  (bar %.3f)  FAIL' % (
                h, h + STEP, a, ('%.3f' % b) if b is not None else 'not in frame', bar))
        if unmeasured and verbose:
            print('   unmeasured: %s' % ', '.join('%.1f' % h for h in unmeasured))
        if fails or cover < MIN_COVER:
            bad += 1
    print('VERDICT: %s' % ('BOTH ENDS PASS' if bad == 0 else 'NOT YET: %d end(s) fail' % bad))
    sys.exit(0 if bad == 0 else 1)


if __name__ == '__main__':
    main()
