# 2026-09-09: THE CEILING OVER THE END BALCONIES, TRIANGULATED FROM ITS OWN EDGE.
#
# Yesterday's census said the 179 frames standing on a west or east gallery deck never point upward, so
# the soffit could not be read the ordinary way. That census also noticed the thing this tool uses: those
# frames carry a dark band across the top of the picture, and the boundary of that band is the soffit's
# FRONT EDGE seen from underneath. The edge is a horizontal line running the width of the hall, so one
# frame gives a ray to it and two frames standing in different places give the line itself.
#
# WHY THIS IS NOT THE FOLLOW TRAP AGAIN. Every earlier reading of a level started from the drawn height
# and walked to the nearest gradient, so the answer partly reproduced the drawing (fitted gains of 0.66
# to 0.81 across this project). Here nothing is walked toward. A scan path is projected up the parapet
# face plane over the WHOLE range h 8.6 to 13.4, the biggest bright-below dark-above step on it is taken,
# and the only thing kept is the PIXEL where that step falls. The drawn 11.1 never enters, and the drawn
# face station uF is not assumed either: it only shapes the scan path, while the ray that comes out of it
# is whatever the picture says. The height and the depth of the edge then come from a linear fit across
# frames standing in different places, which is triangulation and cannot follow anything.
#
#   a ray from centre C through the found point P meets the edge line (u*, h*) when
#       (u* - cu)/vu = (h* - ch)/vh      ->      vh*u* - vu*h* = vh*cu - vu*ch
#   which is linear in the two unknowns, so every reading is one row of a least squares problem and the
#   conditioning is visible: it needs frames whose u differ, and it says so when they do not.
#   python tools/soffit_edge.py [east|west|both]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
YU = np.array([0.0, 1.0, 0.0])
FACE, DECK = 3.85, 8.34
ENDS = {'west': (0.344, -1.0), 'east': (51.906, 1.0)}
HLO, HHI, HSTEP = 8.60, 13.40, 0.01
WIN = 0.35                     # the half window the step statistic averages over, in metres of height
MINC = 10.0                    # a step smaller than this is not a boundary
MAXR = 6.0                     # metres: a ceiling over the deck you stand on is not 30 m away
CLASSES = ('b1p', 'b3p', 'b5p', 'b7sp', 'b6gp', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s', 'b6g')
levels = np.arange(HLO, HHI + 1e-9, HSTEP)
NWIN = int(round(WIN / HSTEP))


def scan(cam, img, uF, dd):
    """the biggest bright-below dark-above step on the parapet face plane, and where it falls"""
    pts = np.array([O + uF * HU + dd * HD + np.array([0, float(v), 0]) for v in levels])
    x, y, z = cam.project(pts)
    ok = (z > 0.4) * (x > 25) * (x < cam.w - 25) * (y > 25) * (y < cam.h - 25)
    # THE LONGEST UNBROKEN VISIBLE RUN, not the whole span: a scan path that leaves the frame and comes
    # back is two different pieces of wall and averaging across the gap would invent a step.
    a = b = None
    i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            if a is None or (j - i) > (b - a):
                a, b = i, j
            i = j + 1
        else:
            i += 1
    if a is None or (b - a) < 3 * NWIN:
        return None
    xi = np.clip(np.round(x[a:b + 1]), 0, img.shape[1] - 1).astype(np.int32)
    yi = np.clip(np.round(y[a:b + 1]), 0, img.shape[0] - 1).astype(np.int32)
    v = img[yi, xi].astype(np.float32)
    # ONLY OVERHEAD BOUNDARIES COUNT. Without this the biggest bright-below dark-above step on the path
    # is the hall's own horizon, near the camera's eye level, and the fit then returns the camera's own
    # height because every ray is horizontal: the first run of this tool did exactly that (u 49.204,
    # h 9.640, sitting inside the camera cloud). A ceiling is above the person standing under it, which
    # is a fact about ceilings and not a fact about the drawing, so rays rising less than 5 degrees are
    # not candidates. Nothing narrows the search around 11.1; the range stays 8.6 to 13.4.
    rel = pts[a:b + 1] - cam.center
    up = rel[:, 1] / np.maximum(1e-6, np.hypot(rel @ HU, rel @ HD))
    rng = np.linalg.norm(rel, axis=1)
    # AND ONLY NEARBY ONES. The visibility census (tools/soffit_reach.py) showed the drawn edge really is
    # inside 11 of the 163 east deck frames and 7 of the 16 west ones, so reach was never the problem. The
    # problem was that the same scan path also crosses 30 m of hall, and drawn back on b7s_000152 the step
    # it chose circled the lit west wall over the dark gallery at the far end of the building. A ceiling
    # over the deck a person is standing on is within a few metres of them, which is again a fact about
    # ceilings rather than about the drawing, so far-field steps are not candidates.
    best, besti = -1e9, None
    for i in range(NWIN, len(v) - NWIN):
        if up[i] < 0.0875 or rng[i] > MAXR:
            continue
        d = float(v[i - NWIN:i].mean() - v[i + 1:i + 1 + NWIN].mean())
        if d > best:
            best, besti = d, i
    if besti is None or best < MINC:
        return None
    j = a + besti
    return float(levels[j]), best, pts[j], float(np.degrees(np.arctan(up[besti])))


def run(end):
    uB, s = ENDS[end]
    uF = uB - s * FACE
    seen, rows = set(), []
    for cls in CLASSES:
        try:
            frames = U.load_class(cls)
        except Exception:
            continue
        for fr, (cam, ip) in sorted(frames.items()):
            if fr in seen:
                continue
            seen.add(fr)
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
            if ch < DECK + 0.35 or abs(cu - uB) > 6.0:
                continue                 # standing on this end's top deck
            img = None
            for dd in np.linspace(1.0, 14.5, 10):
                if img is None:
                    img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        break
                    img = cv2.GaussianBlur(img, (5, 5), 0)
                got = scan(cam, img, uF, dd)
                if got is None:
                    continue
                hv, contrast, P, elev = got
                r = P - cam.center
                vu, vh = float(r @ HU), float(r @ YU)
                rows.append((fr, cu, cd, ch, dd, hv, contrast, vu, vh, elev))
    print('')
    print(end.upper(), 'end: the drawn edge is u %.3f h 11.100' % uF)
    if len(rows) < 6:
        print('   only', len(rows), 'readings, which is not enough to fit a line')
        return
    frs = sorted(set(r[0] for r in rows))
    cus = np.array([r[1] for r in rows])
    els = np.array([r[9] for r in rows])
    print('   %d readings from %d frames, cameras standing u %.2f to %.2f (a %.2f m baseline)'
          % (len(rows), len(frs), cus.min(), cus.max(), cus.max() - cus.min()))
    print('   the boundaries found sit %.1f to %.1f degrees above the camera' % (els.min(), els.max()))
    A = np.array([[r[8], -r[7]] for r in rows])
    yv = np.array([r[8] * r[1] - r[7] * r[3] for r in rows])
    sol, _res, rank, sv = np.linalg.lstsq(A, yv, rcond=None)
    cond = float(sv.max() / sv.min()) if sv.min() > 0 else float('inf')
    ustar, hstar = float(sol[0]), float(sol[1])
    resid = A @ sol - yv
    print('   the fit puts the edge on u %.3f h %.3f, condition number %.0f, residual rms %.4f'
          % (ustar, hstar, cond, float(np.sqrt((resid ** 2).mean()))))
    if cond > 200:
        print('   THAT CONDITION NUMBER MEANS THE CAMERAS DID NOT MOVE ENOUGH. The two unknowns trade off')
        print('   along the sightline, so this pair of numbers is one ray, not a position. Refused.')
    # what the reading is if the drawn face station is taken as given, which is a weaker claim but a check
    found = np.array([r[5] for r in rows])
    print('   holding the face station on the drawn %.3f instead, the edge reads h %.3f, spread %.3f'
          % (uF, float(np.median(found)), float(found.max() - found.min())))
    per = {}
    for r in rows:
        per.setdefault(r[0], []).append(r[5])
    good = [(f, float(np.median(v)), len(v)) for f, v in per.items() if len(v) >= 3]
    good.sort(key=lambda t: t[1])
    for f, m, n in good[:4] + good[-4:]:
        print('        %-12s %d readings, median h %.3f' % (f, n, m))


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    for e in (('west', 'east') if which == 'both' else (which,)):
        run(e)
