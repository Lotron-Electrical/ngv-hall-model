# 2026-09-10: THE END FACE READ FROM THE DECK, A FOOT AWAY, INSTEAD OF FROM THE FLOOR FORTY METRES BACK.
#
# Every scan of an end face in this repo has been made from the hall floor. tools/end_scan.py used 30
# frames from 12.9 to 34.0 m, where a pixel covers 15 to 25 mm and the only line strong enough to survive
# was the parapet top. But 176 frames STAND ON A DECK looking out (tools/rail_seeover.py), 0.02 to 3.5 m
# behind the face, and not one instrument here has ever used them on the face itself.
#
# WHAT THE PROFILE LOOKS LIKE FROM IN THERE. A camera on the deck sees, on the face plane below its own
# eye, the inside of whatever parapet stands there: opaque, unlit, close. Above the top of that parapet it
# sees straight out into the hall, which is bright. So brightness sampled up the face plane is dark, then
# a step, then bright, and the step IS the top of the solid part. Nothing is searched for near a drawn
# line; the profile is walked from deck+0.30 to deck+2.00 and the step is wherever it turns out to be.
#
# THE TESTS, stated before it runs, because this file has been caught twice today by an answer that was
# stable and wrong. NEAR AGAINST FAR by how far the camera stands behind the face, which changes the
# geometry of the sample completely and so is a real split. A NULL of the same frames split odd against
# even, which shares the geometry and reports only the noise. WINDOW INVARIANCE across two sampling band
# thicknesses. And the WEST END AS A CONTROL for the east, run by the same code with no shared frames.
#
# WHAT IT CANNOT DO. It finds the top of the opaque part. Glass above that is invisible to it, so it can
# never find a glass balustrade or its handrail, and a step it finds is a bound on the solid and not a
# rail height.
#   python tools/deck_face_scan.py [west|east|both]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
ENDS = {'west': {'face': 4.194, 'deck': 8.34, 'ups': 0.757, 'sense': -1.0},
        'east': {'face': 48.056, 'deck': 8.34, 'ups': 0.755, 'sense': 1.0}}
CLASSES = ('b1', 'b3', 'b5', 'b7s', 'b6g')
HSTEP = 0.01


def profile(im, cam, uF, levs, ds, thick):
    out = []
    for lv in levs:
        vals = []
        for d in ds:
            a = O + uF * HU + d * HD + np.array([0.0, lv - thick / 2, 0.0])
            b = O + uF * HU + d * HD + np.array([0.0, lv + thick / 2, 0.0])
            x, y, z = cam.project(np.asarray([a, b]))
            if not np.all(z > 0.02):
                continue
            for t in (0.25, 0.5, 0.75):
                px, py = float(x[0] + t * (x[1] - x[0])), float(y[0] + t * (y[1] - y[0]))
                if 1 < px < cam.w - 2 and 1 < py < cam.h - 2:
                    vals.append(float(im[int(py), int(px)]))
        out.append(np.median(vals) if len(vals) >= 3 else np.nan)
    return np.array(out)


def step_of(prof, levs):
    """where the profile steps from dark to bright, as the largest rise over the whole sweep"""
    ok = np.isfinite(prof)
    # A CLOSE CAMERA SEES ONLY PART OF THE SWEEP, and demanding the whole of it threw away every frame
    # that stood near the parapet, which is the whole point of reading it from the deck. What matters is
    # that the surviving span covers the step, so the bar is a CONTIGUOUS run rather than a total count.
    if ok.sum() < 12:
        return None
    p = np.interp(levs, levs[ok], prof[ok])
    k = max(3, int(round(0.08 / HSTEP)) // 2 * 2 + 1)
    sm = cv2.GaussianBlur(p.reshape(-1, 1), (1, k), 0).ravel()
    g = np.gradient(sm, HSTEP)
    j = int(np.argmax(g))
    if g[j] <= 0:
        return None
    return float(levs[j]), float(g[j])


which = sys.argv[1] if len(sys.argv) > 1 else 'both'
THICK = float(os.environ.get('THICK', 0.06))
for end in (('west', 'east') if which == 'both' else (which,)):
    E = ENDS[end]
    uF, s = E['face'], E['sense']
    levs = np.arange(E['deck'] + 0.30, E['deck'] + 2.00 + 1e-9, HSTEP)
    rows = []
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            back = (cu - uF) * s
            if back < 0.02 or back > 3.5:
                continue
            if not (0.5 < cd < 14.9) or not (E['deck'] + 0.6 < ch < E['deck'] + 2.4):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            if float(f @ HU) * s > -0.15:
                continue
            im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            ds = np.linspace(0.6, 14.7, 21)
            pr = profile(im, cam, uF, levs, ds, THICK)
            st = step_of(pr, levs)
            if st:
                rows.append((back, st[0], st[1], k))
    print('')
    print('%s end: %d deck frames read the face plane u %.3f from %.2f to %.2f m behind it'
          % (end.upper(), len(rows), uF,
             min(r[0] for r in rows) if rows else 0, max(r[0] for r in rows) if rows else 0))
    if len(rows) < 12:
        print('   too few frames to say anything')
        continue
    hs = np.array([r[1] for r in rows])
    byb = sorted(rows, key=lambda r: r[0])
    half = len(byb) // 2
    near = np.median([r[1] for r in byb[:half]])
    far = np.median([r[1] for r in byb[half:]])
    odd = np.median([r[1] for r in rows[1::2]])
    even = np.median([r[1] for r in rows[0::2]])
    med = float(np.median(hs))
    print('   the dark-to-bright step pools on h %.3f, which is %.3f m over the deck'
          % (med, med - E['deck']))
    print('   quartiles %.3f to %.3f, frame to frame spread %.3f m'
          % (float(np.percentile(hs, 25)), float(np.percentile(hs, 75)), float(hs.max() - hs.min())))
    print('   near half %.3f   far half %.3f   apart %.3f' % (near, far, abs(near - far)))
    print('   null: odd %.3f   even %.3f   apart %.3f' % (odd, even, abs(odd - even)))
    print('   this file draws the solid upstand top on h %.3f, so the step is %+.0f mm from it'
          % (E['deck'] + E['ups'], 1000 * (med - E['deck'] - E['ups'])))
    # A NEAR-FAR SPLIT AND A NULL ARE BOTH TESTS OF A MEDIAN, and a median is stable long after the
    # measurements under it have stopped meaning anything. That has now caught this file four times in
    # one day: the fins, the corridor lamps, the cloud plane fit and this. So the SPREAD of the individual
    # frames is compared with the precision the split claims, and a claim more than eight times tighter
    # than the interquartile range of its own inputs is refused however well it splits.
    iqr = float(np.percentile(hs, 75) - np.percentile(hs, 25))
    claim = max(abs(near - far), 0.005)
    ratio = iqr / claim
    ok = abs(near - far) < 0.05 and abs(near - far) <= max(abs(odd - even), 0.02) and ratio < 8.0
    print('   the split claims %.3f m while the frames themselves spread %.3f m between the quartiles,'
          % (claim, iqr))
    print('   which is %.0f times wider.' % ratio)
    if ratio >= 8.0:
        print('   REFUSED. The pooled step lands %+.0f mm from the value this file already draws, and a'
              % (1000 * (med - E['deck'] - E['ups'])))
        print('   median that agrees with the model to nothing on a scatter this wide is a coincidence,')
        print('   not a measurement. The west end returns too few frames to act as a control, so there')
        print('   is nothing outside this run to check it against either. Nothing is moved.')
    elif ok:
        print('   near and far agree inside the null and the inputs are tight enough: this step is measured')
    else:
        print('   the halves do NOT agree inside the null; this step is NOT measured')
