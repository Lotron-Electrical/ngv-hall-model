# 2026-09-10: THE SOFFIT DEPTH OVER THE END GALLERIES, MEASURED AS A SEPARATION ALONG ITS OWN PLANE.
#
# WHAT THIS NUMBER IS. Over each end gallery the model draws a soffit on h 11.090, ENDW.head, running from
# the gallery face back toward the end wall by ENDW.soffitDepth, 2.1 m: west from u 4.194 back to 2.094,
# east from 48.056 back to 50.156. Behind the back edge the bay is open to the canopy. The head was measured
# at both ends on 2026-09-09 (tools/soffit_back.py, 13 and 24 mm ray medians). The DEPTH was not: the same
# tool peeled five lines at each end and every one sat within 0.9 m of the face, and the three tools before
# it had all gone looking for a boundary in one picture at a time. The 2.1 rests on two hall-floor frames
# read by eye (w2_000252, d4_000049) and has never had an instrument on it.
#
# HOW IT IS MEASURED, AND WHY THIS IS NOT THE FOURTH FAILURE OF THE SAME IDEA. Sample every posed frame
# along a sweep in u ON the soffit plane, across the width of the hall, and stack the profiles with each
# frame normalised to its own mean. Walking inward from the face, a ray to a point on that plane hits the
# soffit's underside until it passes the back edge, then continues to whatever lies beyond. So the sweep
# carries TWO edges: the front edge at the face and the back edge at the depth, and the number read is
# their SEPARATION. A common error in the head, in the face, in the camera height or in the pointing moves
# both edges along the sweep together and cancels out of a separation, which is the discipline that has
# held up everywhere else in this file: DIFFERENCE OUT THE SOFT TERM. The earlier tools fitted one edge
# per frame and needed each frame to show it; this one needs the stack to show it, which is a weaker ask
# by a factor of the frame count.
#
# WHICH FRAMES. The rail on the gallery front (9.799 west, 9.865 east) hides the back edge from anyone
# standing close: a camera 1.6 m up needs to stand 14 m out for the ray to the drawn back edge to clear the
# rail, and 19 m out for the far end of the search band to clear it. So only cameras 20 m or more out from
# the face are used, and the rail cannot enter the sweep as a false edge. The pan-chained balcony sets are
# left out, their own quality file rating them poor at the far end of the hall.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED.
#   1. The front edge is the strongest gradient within 0.25 m of the face; the back edge is the strongest
#      gradient inside the drawn depth plus or minus 0.75 m, declared here. The slab ruler learnt what an
#      open aperture finds and it is not being learnt twice.
#   2. THE FIRST CONTROL IS AN INVENTED PLANE, the same sweep on h 12.20, a metre above the soffit where
#      the bay is open. If it peaks as hard as the real plane inside the same band, this is reading the
#      picture and not the building, and nothing is concluded.
#   3. THE SECOND CONTROL IS THE OTHER END. Two soffits, two readings. A depth the two ends do not agree on
#      to within five sweep steps, 0.10 m, is not claimed from either. The slab ruler asked for two steps
#      of 10 mm from cameras 30 m away and could not have been satisfied by a perfect building; a soffit
#      seen from 20 to 45 m with poses good to 25 mm at the face resolves about 0.1 m along this sweep,
#      and the tolerance is set to what the instrument can do, before it runs.
#   4. Nothing is claimed finer than that tolerance.
#
# WHAT IT CANNOT DO. It cannot fix where the soffit IS, only how deep it is, which is the price of the
# cancellation and the point of the tool. If the back edge is photometrically invisible, dark underside
# meeting dark wall, the band will hold noise, the invented plane will match it, and the rule says so.
#   hwq run --gb 4 --label "soffit ruler" -- python -u tools/soffit_ruler.py
import io
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = ('walk', 'night', 'day4k', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s', 'b6g')
USTEP = 0.020
FRONT = 0.25
BAND = 0.75
TOL = 5 * USTEP
DS = np.linspace(2.0, 13.4, 20)
NULLH = 12.20
MINOUT = 20.0
MINFRAMES = 15
MARGIN = 30

src = io.open('index.html', encoding='utf-8').read()
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]


def endw(k):
    return float(re.search(r'\b' + k + r':\s*(-?[0-9.]+)', BLOCK).group(1))


HEAD = endw('head')
DEPTH = endw('soffitDepth')
WFACE = endw('west') + endw('face')
EFACE = endw('east') - endw('face')


def profile(cam, img, us, hplane):
    got = np.zeros(len(us))
    cnt = np.zeros(len(us))
    for d in DS:
        pts = np.array([O + u * HU + d * HD + np.array([0.0, hplane, 0.0]) for u in us])
        x, y, z = cam.project(pts)
        ok = z > 0.5
        ok = np.logical_and(ok, x > MARGIN)
        ok = np.logical_and(ok, x < cam.w - MARGIN)
        ok = np.logical_and(ok, y > MARGIN)
        ok = np.logical_and(ok, y < cam.h - MARGIN)
        if ok.sum() < 0.8 * len(us):
            continue
        xi = np.clip(x.astype(int), 0, img.shape[1] - 1)
        yi = np.clip(y.astype(int), 0, img.shape[0] - 1)
        v = img[yi, xi].astype(np.float64)
        got[ok] += v[ok]
        cnt[ok] += 1
    if (cnt > 0).sum() < 0.8 * len(us):
        return None
    out = np.full(len(us), np.nan)
    nz = cnt > 0
    out[nz] = got[nz] / cnt[nz]
    if np.isnan(out).any():
        return None
    return out - out.mean()


def stack(us, hplane, uface, s):
    """s is the direction from the face toward the end wall: -1 west, +1 east. Cameras must stand on the
    hall side of the face by MINOUT so the rail cannot reach into the sweep."""
    rows, used = [], {}
    for cn in CLASSES:
        try:
            fr = U.load_class(cn)
        except Exception:
            continue
        for k, (cam, ip) in sorted(fr.items()):
            q = cam.center - O
            cu, ch = float(q @ HU), float(q[1])
            if ch > HEAD - 0.3:
                continue
            if s * (cu - uface) > -MINOUT:
                continue
            img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            p = profile(cam, img, us, hplane)
            if p is None:
                continue
            rows.append(p)
            used[cn] = used.get(cn, 0) + 1
    if len(rows) < MINFRAMES:
        return None, used
    return np.mean(np.asarray(rows), axis=0), used


def grad(prof):
    g = np.abs(np.gradient(prof))
    return np.convolve(g, np.ones(3) / 3.0, mode='same')


def peak(xs, g, lo, hi):
    win = np.logical_and(xs >= lo, xs <= hi)
    if not win.any():
        return None, 0.0
    i = int(np.argmax(np.where(win, g, -1)))
    return float(xs[i]), float(g[i])


def run(name, uface, s):
    xs = np.arange(-FRONT - 0.1, DEPTH + BAND + 1e-9, USTEP)      # depth into the bay from the face
    us = uface + s * xs
    prof, used = stack(us, HEAD, uface, s)
    if prof is None:
        print('   %-5s NOT ENOUGH FRAMES SEE THIS SOFFIT: %s. Nothing is read from this end.'
              % (name, ', '.join('%s %d' % t for t in used.items()) or 'none'))
        return None
    g = grad(prof)
    xf, gf = peak(xs, g, -FRONT, FRONT)
    xb, gb = peak(xs, g, DEPTH - BAND, DEPTH + BAND)
    nprof, _ = stack(us, NULLH, uface, s)
    if nprof is None:
        nb = float('nan')
    else:
        _, nb = peak(xs, grad(nprof), DEPTH - BAND, DEPTH + BAND)
    print('   %-5s %d frames, %s' % (name, sum(used.values()),
                                     ', '.join('%s %d' % t for t in sorted(used.items()))))
    print('         front edge on x %+.3f (%.3f), back edge on x %.3f (%.3f): a depth of %.3f m'
          % (xf, gf, xb, gb, xb - xf))
    print('         the invented plane on h %.2f peaks at %.3f inside the same back band' % (NULLH, nb))
    return dict(name=name, depth=xb - xf, xf=xf, xb=xb, gf=gf, gb=gb, nb=nb, frames=sum(used.values()))


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   The soffit over each end gallery is drawn on h %.3f running %.2f m back from the face. A'
          % (HEAD, DEPTH))
    print('   sweep in u ON that plane, every %.0f mm, sampled in every posed frame standing %.0f m or'
          % (1000 * USTEP, MINOUT))
    print('   more out from the face and stacked with each frame normalised to its own mean, carries two')
    print('   edges: the front edge at the face and the back edge at the depth. The number read is their')
    print('   SEPARATION, so a common error in head, face, height or pointing cancels. The front edge is')
    print('   searched within %.2f m of the face, the back edge inside the drawn depth plus or minus %.2f m,'
          % (FRONT, BAND))
    print('   both declared here. THE FIRST CONTROL is an invented plane on h %.2f judged in the same'
          % NULLH)
    print('   band. THE SECOND CONTROL is the other end: two soffits, two readings, and a depth the ends')
    print('   do not agree on to within %.2f m is not claimed. Nothing finer than that is claimed.' % TOL)
    print('')
    west = run('west', WFACE, -1)
    east = run('east', EFACE, +1)
    print('')
    got = [r for r in (west, east) if r]
    if not got:
        print('   NEITHER END CAN BE READ. The drawn %.2f m stands untested.' % DEPTH)
        sys.exit(0)
    live = [r for r in got if r['gb'] > r['nb']]
    dead = [r for r in got if r['gb'] <= r['nb']]
    for r in dead:
        print('   %-5s DOES NOT BEAT ITS INVENTED PLANE (%.3f against %.3f): its back band holds the'
              % (r['name'], r['gb'], r['nb']))
        print('         picture, not the building, and nothing is read from this end.')
    if not live:
        print('')
        print('   NEITHER END BEATS ITS INVENTED PLANE, so NOTHING IS CONCLUDED about the soffit depth and')
        print('   the drawn %.2f m stands exactly as untested as it was.' % DEPTH)
        sys.exit(0)
    for r in live:
        print('   %-5s beats its invented plane (%.3f against %.3f): depth %.3f m against %.2f drawn'
              % (r['name'], r['gb'], r['nb'], r['depth'], DEPTH))
    if len(live) < 2:
        print('')
        print('   ONLY ONE END SPEAKS, so by the rule above no depth is claimed. A single reading of %.3f m'
              % live[0]['depth'])
        print('   against %.2f drawn, and a second end would be needed before that could move anything.'
              % DEPTH)
        sys.exit(0)
    a, b = live[0]['depth'], live[1]['depth']
    if abs(a - b) > TOL:
        print('')
        print('   THE TWO ENDS DISAGREE BY %.3f m, more than the %.2f m tolerance, so they are not'
              % (abs(a - b), TOL))
        print('   measuring one depth and no number is claimed from either. The drawn %.2f m stands'
              % DEPTH)
        print('   untested.')
        sys.exit(0)
    m = 0.5 * (a + b)
    print('')
    print('   BOTH ENDS AGREE: %.3f m against %.2f m drawn, a difference of %+.0f mm.'
          % (m, DEPTH, 1000 * (m - DEPTH)))
    if abs(m - DEPTH) <= TOL:
        print('   Inside the tolerance, so the drawn depth is CONFIRMED rather than corrected, and for the')
        print('   first time it is a measurement.')
    else:
        print('   Outside the tolerance at both ends independently, so the drawn depth is wrong by that')
        print('   much and the file should carry %.2f m.' % m)


if __name__ == '__main__':
    main()
