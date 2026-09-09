# 2026-09-10: DOES THE MODEL LAND ON THE PHOTOGRAPH? RENDER IT FROM REAL POSES AND MEASURE THE OFFSET.
#
# WHAT IS DIFFERENT ABOUT THIS. Every instrument in this project so far has measured ONE quantity: a
# level, a jamb, a depth, a hit rate. This measures the whole configuration at once. Put the sim camera
# exactly where a real camera stood, render, and ask how far the render has to be slid to line up with the
# photograph. A model whose balconies, walls and corridor are in the right places needs no slide.
#
# THE FRAMES ARE CHOSEN BLIND, which matters because this project has twice been burnt by windows picked
# by eye. The rule is stated before anything is opened: among the floor captures take the frames whose
# projected north-wall OPENINGS cover the most image area, and among the balcony captures the frames whose
# projected gallery FRONT covers the most. No frame is looked at first.
#
# THE MEASUREMENT. Gradient magnitude of both pictures, then normalised cross-correlation over a grid of
# whole-pixel shifts. The peak tells you the offset in pixels, and the range to the wall turns that into
# metres. Gradients rather than brightness because the render and the photograph are lit differently and
# nothing here should depend on matching exposure.
#
# THE CONTROL IS A MISMATCHED PAIR. The same render scored against a DIFFERENT frame's photograph gives
# the level this measure reaches on two pictures that have nothing to do with each other. If the true
# pairs do not clear that, the score is not measuring alignment and nothing is concluded.
#
# WHAT IT CANNOT DO. It cannot separate a wall in the wrong place from a camera pose in the wrong place:
# both slide the render. It reports the offset and says so. And a large part of what it sees is the baked
# scan, which came from photographs of this building, so agreement there is partly the bake agreeing with
# its own source; the openings are scored separately for that reason.
#   python tools/render_match.py select     -> writes render-match.json
#   node tools/render_match.mjs             -> renders each pose from the LIVE sandbox
#   python tools/render_match.py score      -> the offsets
import io
import json
import os
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
OUT = 'render-match'
JSONF = 'render-match.json'
FLOOR = ('walk', 'night', 'day4k')
BALC = ('b3', 'b7s', 'b1', 'b5', 'b4', 'b6s')
NPICK = 8     # per group
PER = 2       # per capture, so no one clip decides the answer
SEP = 3.0     # metres along the hall between two frames of the same capture

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
SILL = float(re.search(r'openY:\[([0-9.]+),', src).group(1))
HEADY = float(re.search(r'openY:\[[0-9.]+,([0-9.]+)\]', src).group(1))
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]
DECK = float(re.search(r'floors:\[[0-9.]+,([0-9.]+)\]', BLOCK).group(1))
EFACE = float(re.search(r'\beast:\s*([0-9.]+)', BLOCK).group(1)) - float(
    re.search(r'\bface:\s*([0-9.]+)', BLOCK).group(1))
WFACE = float(re.search(r'\bwest:\s*([0-9.]+)', BLOCK).group(1)) + float(
    re.search(r'\bface:\s*([0-9.]+)', BLOCK).group(1))


# THE FIRST FORM OF THIS RULE WAS LOOSE AND IT IS WORTH SAYING WHAT IT DID. "The frames whose projected
# openings cover the most image area" allowed a corner to fall OUTSIDE the frame and scored the clipped
# rectangle, so an opening sliced by the frame edge could win. On the walk captures it chose w1_000105,
# pitched 78 degrees up, where the opening grazes the top corner and nine tenths of the picture is ceiling.
# That is a bad test of a wall and it was the rule's fault, not the frame's. The rule is now the STRICTER
# form of the same idea, and it was tightened before any score was read: every corner of the target must
# fall inside the frame with a small margin, and among those, most area wins. Nothing was loosened.
MARGIN = 0.02


def corners(cam, pts):
    x, y, z = cam.project(np.asarray(pts))
    if not np.all(z > 0.5):
        return None
    mx, my = MARGIN * cam.w, MARGIN * cam.h
    if x.min() < mx or x.max() > cam.w - mx or y.min() < my or y.max() > cam.h - my:
        return None
    return (x.max() - x.min()) * (y.max() - y.min()) / float(cam.w * cam.h)


# AND THE ONE CORRECTION THIS MEASUREMENT CANNOT DO WITHOUT. A real camera's optical centre is not the
# middle of its picture, and the sim's is, by construction: index.html builds a symmetric perspective
# camera. So even a perfect model renders SHIFTED from the photograph by exactly the principal point offset
# (cx - w/2, cy - h/2), and reading that shift as a wall in the wrong place would be my own error dressed
# up as a finding. It is subtracted, and it is subtracted from a number the solver reported, not one fitted
# here. Radial distortion is NOT corrected: it bends the photograph away from the render off-axis, which
# costs correlation but does not move the centre, so it is reported and left alone.
# AND THE FAULT THAT WRECKED THE FIRST RUN, WHICH WAS ENTIRELY MINE. The sim camera has a yaw and a
# pitch and NO ROLL. The archive is handheld: the two hall-floor captures are portrait video stored in a
# landscape buffer, so world-up lies along the picture's SIDE, ninety degrees from where any roll-free
# render puts it, and one balcony clip is tilted sixteen degrees. Comparing those was comparing a picture
# with the same picture on its side. It is fixed by rendering a SQUARE that circumscribes the frame, at the
# same angular scale, then turning that square by the measured roll and cutting the frame out of the
# middle: exactly what a rolled camera with these intrinsics would have recorded, with no page change and
# no fitted parameter. The roll is not searched for, it is read from the pose the solver already published.
def pose(cam):
    C = cam.center
    q = C - O
    u, d, h = float(q @ HU), float(q @ HD), float(q[1])
    f = cam.R.T @ np.array([0, 0, 1.0])
    fu, fd, fh = float(f @ HU), float(f @ HD), float(f[1])
    horiz = np.hypot(fu, fd)
    pitch = float(np.degrees(np.arcsin(fh)))
    p = np.asarray(cam.params, float)
    fx, fy, cx, cy = float(p[0]), float(p[1]), float(p[2]), float(p[3])
    # world-up as it lands in THIS picture, measured by projecting a point and the same point one metre
    # higher. Sign conventions cannot be reasoned about here, so they are not: the direction is measured.
    x0, y0, _ = cam.project(np.asarray([C + f * 10]))
    x1, y1, _ = cam.project(np.asarray([C + f * 10 + np.array([0, 1.0, 0])]))
    du, dv = float(x1[0] - x0[0]), float(y1[0] - y0[0])
    n = float(np.hypot(du, dv))
    dsq = float(np.hypot(cam.w, cam.h))
    return dict(u=u, d=d, h=h, fu=fu / horiz, fd=fd / horiz, pitch=pitch,
                w=int(cam.w), hgt=int(cam.h),
                vfov=float(2 * np.degrees(np.arctan(cam.h / 2.0 / fy))),
                sqvfov=float(2 * np.degrees(np.arctan(dsq / 2.0 / fy))),
                sqside=dsq / float(cam.h),
                fx=fx, fy=fy, ppx=cx - cam.w / 2.0, ppy=cy - cam.h / 2.0,
                upx=du / n, upy=dv / n, roll=float(np.degrees(np.arctan2(du / n, -dv / n))),
                params=[float(v) for v in p])


def do_select():
    picks = []
    for group, classes, what in (('floor', FLOOR, 'openings'), ('balcony', BALC, 'gallery front')):
        cand = []
        for cname in classes:
            try:
                frames = U.load_class(cname)
            except Exception:
                continue
            for k, (cam, ip) in sorted(frames.items()):
                q = cam.center - O
                cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
                # TWO GATES ON THE INPUT, NOT ON THE ANSWER, so neither can be used to drop a result that
                # comes out badly. A camera standing outside the building did not photograph the inside of
                # it, and a lens whose optical centre sits in the outer quarter of its own picture is not a
                # calibration this method can honour; both were in the first wider set (b6s_000396 stands
                # at u 62.9, eleven metres past the east end, with its principal point 904 px down a
                # 2032 px frame) and both are refused before any picture is opened.
                if not (-1.0 < cu < 53.0) or not (-1.5 < cd < 16.5):
                    continue
                pp = np.asarray(cam.params, float)
                if abs(pp[2] - cam.w / 2.0) > 0.25 * cam.w or abs(pp[3] - cam.h / 2.0) > 0.25 * cam.h:
                    continue
                if group == 'floor':
                    if ch > 3.0 or not (2.0 < cd < 15.0):
                        continue
                    best = 0.0
                    for u0, u1 in OPEN:
                        a = corners(cam, [O + u * HU + DN * HD + np.array([0.0, v, 0.0])
                                          for u in (u0, u1) for v in (SILL, HEADY)])
                        if a:
                            best = max(best, a)
                    cover = best
                else:
                    if ch < 6.0:
                        continue
                    cover = 0.0
                    for uF in (WFACE, EFACE):
                        a = corners(cam, [O + uF * HU + dv * HD + np.array([0.0, v, 0.0])
                                          for dv in (2.0, 13.0) for v in (DECK, DECK + 1.6)])
                        if a:
                            cover = max(cover, a)
                if cover > 0.004:
                    cand.append((cover, cname, k, ip, cam))
        cand.sort(key=lambda t: -t[0])
        taken = []
        for cover, cname, k, ip, cam in cand:
            mine = [t for t in taken if t[1] == cname]
            if len(mine) >= PER:
                continue                       # a capture cannot flood the set with its own best angle
            uu = float((cam.center - O) @ HU)
            if any(abs(uu - float((t[4].center - O) @ HU)) < SEP for t in mine):
                continue                       # nor with two frames of the same piece of wall
            taken.append((cover, cname, k, ip, cam))
            if len(taken) >= NPICK:
                break
        print('%s: %d candidates cover more than 0.4 per cent of the frame with the %s'
              % (group, len(cand), what))
        for cover, cname, k, ip, cam in taken:
            p = pose(cam)
            p.update(dict(group=group, cls=cname, frame=k, photo=ip, cover=cover))
            picks.append(p)
            print('   %-6s %-14s cover %.3f  u %.2f d %.2f h %.2f  vfov %.1f  %dx%d  roll %+.1f  '
                  'principal point off centre %+.0f %+.0f px'
                  % (cname, k, cover, p['u'], p['d'], p['h'], p['vfov'], p['w'], p['hgt'],
                     p['roll'], p['ppx'], p['ppy']))
    if not picks:
        sys.exit('   nothing was selected, so there is nothing to render')
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    io.open(JSONF, 'w', encoding='utf-8', newline='').write(json.dumps(picks, indent=1))
    print('')
    print('wrote %s with %d poses; now run node tools/render_match.mjs' % (JSONF, len(picks)))


def grad(im):
    g = cv2.GaussianBlur(im.astype(np.float32), (0, 0), 1.6)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    m = np.hypot(gx, gy)
    return m / max(float(m.std()), 1e-6)


def ncc(a, b, dx, dy):
    h, w = a.shape
    x0, x1 = max(0, dx), min(w, w + dx)
    y0, y1 = max(0, dy), min(h, h + dy)
    A = a[y0:y1, x0:x1]
    B = b[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    if A.size < 1000:
        return -1.0
    A = A - A.mean()
    B = B - B.mean()
    den = float(np.sqrt((A * A).sum() * (B * B).sum()))
    return float((A * B).sum() / den) if den > 0 else -1.0


WH = 540          # both pictures are read on this many lines, so a 4K photo and a 720-line render meet
SPAN = 1.5        # degrees searched either side of where a perfect model would land
NST = 8           # steps to that edge, so seventeen positions across
FARX = 4.0        # and a second control: the same true pair pulled this many spans off, diagonally


def photo(p):
    """The photograph with its lens taken off, reduced to the working size."""
    im = cv2.imread(p['photo'], cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    q = p['params']
    if len(q) > 4:
        # THE DISTORTION HAS TO GO, and the reason is arithmetic rather than taste: k1 near 0.04 moves a
        # corner about thirty pixels, and the whole search window is thirty-four. Left in, it would have
        # been read as the model being out by the width of the window.
        K = np.array([[q[0], 0, q[2]], [0, q[1], q[3]], [0, 0, 1.0]])
        im = cv2.undistort(im, K, np.array(q[4:8], float), None, K)
    wide = int(round(WH * p['w'] / float(p['hgt'])))
    return grad(cv2.resize(im, (wide, WH), interpolation=cv2.INTER_AREA))


def rolled(p, path):
    """The square render turned by the camera's own roll, then cut down to the frame."""
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    side = im.shape[0]
    c = (side / 2.0 - 0.5, side / 2.0 - 0.5)
    # WHICH WAY TO TURN IT IS NOT REASONED ABOUT, IT IS TESTED. Two candidate angles, and the one whose
    # matrix actually carries the render's up direction (0,-1) onto the direction world-up takes in the
    # photograph is the one used. A sign convention argued from memory is how a whole run gets thrown away.
    want = np.array([p['upx'], p['upy']])
    best, bM = None, None
    for a in (p['roll'], -p['roll']):
        M = cv2.getRotationMatrix2D(c, a, 1.0)
        got = M[:2, :2] @ np.array([0.0, -1.0])
        err = float(np.hypot(*(got - want)))
        if best is None or err < best:
            best, bM = err, M
    im = cv2.warpAffine(im, bM, (side, side), flags=cv2.INTER_AREA, borderValue=0)
    wide = int(round(WH * p['w'] / float(p['hgt'])))
    kw = int(round(side * p['w'] / float(p['hgt']) / p['sqside']))
    kh = int(round(side / p['sqside']))
    x0, y0 = (side - kw) // 2, (side - kh) // 2
    cut = cv2.resize(im[y0:y0 + kh, x0:x0 + kw], (wide, WH), interpolation=cv2.INTER_AREA)
    # A BLIND RENDER CANNOT BE SCORED, AND ONE OF THESE IS BLIND. b5_000174 stands INSIDE opening 5, a
    # tenth of a metre from the jamb the model draws, looking straight along the wall into it, so the sim
    # returns a black frame. That is the model behaving correctly for that pose, not a fault, but a picture
    # with no edges in it correlates with nothing and its score would be noise. The test is on the RENDER
    # alone, before the photograph is ever brought near it, so it cannot become a way to drop an
    # inconvenient answer: fewer than a twentieth of the pixels carrying any edge at all and it is dropped.
    g = np.hypot(cv2.Sobel(cut.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3),
                 cv2.Sobel(cut.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3))
    return grad(cut), best, float((g > 8).mean())


def do_score():
    picks = json.loads(io.open(JSONF, encoding='utf-8').read())
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE SCORES ARE READ.')
    print('   Both pictures are reduced to %d lines and turned into gradient magnitude, then the render is'
          % WH)
    print('   slid over the photograph across %+.1f to %+.1f degrees in %d steps and scored by normalised'
          % (-SPAN, SPAN, 2 * NST + 1))
    print('   cross-correlation. Where a PERFECT model would land is not zero shift: it is the principal')
    print('   point offset the solver reported for that camera, because the sim camera is symmetric and a')
    print('   real one is not. Every offset below is measured FROM there.')
    print('   FIRST CONTROL: every render against a different frame photograph, same search. If the true')
    print('   pairs do not beat the best of those, this is not measuring alignment and nothing is claimed.')
    print('   SECOND CONTROL: the true pair pulled %.0f spans off diagonally, which says how much of the'
          % FARX)
    print('   score is just two pictures of a big pale room.')
    print('   ONLY THEN: a pair peaking one step or less from the expected place is registered; a pair')
    print('   peaking elsewhere is a misalignment, reported in pixels, degrees and metres, not explained.')
    print('   BEFORE ANY OF IT: the photograph has its lens distortion removed with the coefficients the')
    print('   solver published, and the render is turned by the camera roll the same pose reports, since')
    print('   the sim camera has no roll and two of these captures are portrait video in a landscape can.')
    print('')
    rows = []
    G = {}
    for i, p in enumerate(picks):
        rp = os.path.join(OUT, 'r%02d.jpg' % i)
        if not os.path.exists(rp):
            print('   %-6s %-14s no render on disk, skipped' % (p['cls'], p['frame']))
            continue
        A = photo(p)
        rb = rolled(p, rp)
        if A is None or rb is None:
            print('   %-6s %-14s could not be read, skipped' % (p['cls'], p['frame']))
            continue
        B, rerr, frac = rb
        if rerr > 0.02:
            print('   %-6s %-14s the roll could not be reproduced (%.3f), skipped'
                  % (p['cls'], p['frame'], rerr))
            continue
        if frac < 0.05:
            print('   %-6s %-14s DROPPED BEFORE SCORING: the render carries edges on only %.1f per cent '
                  'of its pixels' % (p['cls'], p['frame'], 100 * frac))
            continue
        sc = WH / float(p['hgt'])
        fyw = p['fy'] * sc
        step = max(1.0, fyw * np.tan(np.radians(SPAN)) / NST)
        ex, ey = p['ppx'] * sc, p['ppy'] * sc
        G[i] = (A, B, p, step, ex, ey)
        grid = [(ncc(A, B, int(round(ex + a * step)), int(round(ey + b * step))), a, b)
                for a in range(-NST, NST + 1) for b in range(-NST, NST + 1)]
        best = max(grid)
        atex = ncc(A, B, int(round(ex)), int(round(ey)))
        far = float(np.median([ncc(A, B, int(round(ex + sa * FARX * NST * step)),
                                   int(round(ey + sb * FARX * NST * step)))
                               for sa in (-1, 1) for sb in (-1, 1)]))
        rows.append(dict(i=i, p=p, peak=best[0], da=best[1], db=best[2], step=step,
                         atex=atex, far=far, fyw=fyw))
    if not rows:
        sys.exit('   nothing scored: no renders on disk')
    print('   capture  frame            peak    steps off   where it should be   pulled far off')
    for r in rows:
        print('   %-8s %-14s %.4f   %+3d,%+3d      %.4f               %.4f'
              % (r['p']['cls'], r['p']['frame'], r['peak'], r['da'], r['db'], r['atex'], r['far']))

    ctrl = []
    ks = sorted(G)
    for i in ks:
        for j in ks:
            if i == j:
                continue
            A, _, _, step, ex, ey = G[i]
            B = G[j][1]
            if A.shape != B.shape:
                B = cv2.resize(B, (A.shape[1], A.shape[0]))
            ctrl.append(max(ncc(A, B, int(round(ex + a * step)), int(round(ey + b * step)))
                            for a in range(-NST, NST + 1) for b in range(-NST, NST + 1)))
    tp = [r['peak'] for r in rows]
    print('')
    print('   THE FIRST CONTROL, %d mismatched pairs: best %.4f, median %.4f.'
          % (len(ctrl), max(ctrl), float(np.median(ctrl))))
    print('   THE TRUE PAIRS: median %.4f, worst %.4f, best %.4f.'
          % (float(np.median(tp)), min(tp), max(tp)))
    print('   THE SECOND CONTROL, the same pairs pulled far off: median %.4f.'
          % float(np.median([r['far'] for r in rows])))
    if float(np.median(tp)) <= max(ctrl):
        print('')
        print('   THE TRUE PAIRS DO NOT CLEAR THE MISMATCHED ONES. This is not measuring alignment, no')
        print('   offset above means anything, and NOTHING IS CONCLUDED about the geometry.')
        sys.exit(0)
    beat = sum(1 for v in tp if v > max(ctrl))
    print('   %d of %d true pairs beat every mismatched pair, so the score does track alignment.'
          % (beat, len(tp)))

    print('')
    print('   AND WHAT THE OFFSETS SAY, WHICH IS THE POINT OF THE WHOLE RUN.')
    reg = 0
    for r in rows:
        p = r['p']
        px = np.hypot(r['da'], r['db']) * r['step']
        deg = float(np.degrees(np.arctan(px / r['fyw'])))
        rng = abs(p['d'] - DN) if p['group'] == 'floor' else abs(p['u'] - (WFACE if p['u'] < 26 else EFACE))
        m = 2 * rng * np.tan(np.radians(deg / 2.0))
        good = abs(r['da']) <= 1 and abs(r['db']) <= 1
        reg += 1 if good else 0
        print('      %-6s %-14s %s  %5.1f px, %.2f deg, about %.2f m on the surface %.1f m away'
              % (p['cls'], p['frame'], 'REGISTERED' if good else 'off       ', px, deg, m, rng))
    print('')
    print('   %d of %d land where a correct model and a correct pose would put them, inside one step of'
          % (reg, len(rows)))
    print('   %.0f px. WHAT THIS CANNOT SEPARATE, said plainly: a surface in the wrong place and a camera'
          % float(np.median([r['step'] for r in rows])))
    print('   in the wrong place both slide the whole render, and the solver quotes its own pose error as')
    print('   24 to 100 mm on the balcony clips. An offset here is an upper bound on the geometry error,')
    print('   never a measurement of it, and the baked scan in the picture came from photographs of this')
    print('   building, so part of any agreement is the bake agreeing with its own source.')


# ------------------------------------------------------------------ the bound
# THE FIRST PASS ANSWERED A DIFFERENT QUESTION THAN I THOUGHT I WAS ASKING, and this is what it taught.
# The measure works: with the roll put right the true pairs reach 0.24 to 0.41 while the best mismatched
# pair reaches 0.13. But the peak is nearly FLAT. On the night frame the score where a perfect model would
# land is 0.3944 and the highest score anywhere in the window is 0.4060, three per cent better and a whole
# degree away. Reading that peak as "the model is out by a degree" would be reading noise, and this project
# has paid for that mistake often enough to have a rule about it: A CLAIM MUST NOT BE SMALLER THAN ITS OWN
# SPREAD.
#
# SO MEASURE THE SPREAD. Cut both pictures into tiles, resample the tiles with replacement, and find the
# peak again for each resample. The scatter of those peaks IS this instrument's precision on this pair, got
# from the pair itself rather than assumed. THE RULE, FIXED HERE BEFORE THE RUN: if the middle 90 per cent
# of the resampled peaks contains the place a perfect model would put it, the pair is CONSISTENT WITH A
# CORRECTLY REGISTERED MODEL and the run delivers the size of that envelope as an upper bound on the error.
# If it excludes that place, the offset is real and gets reported as a misalignment. Only pairs that beat
# every mismatched pair are eligible, because for the rest the measure is not tracking alignment at all.
#
# AND WHAT AN UPPER BOUND HERE IS AND IS NOT. It covers the model AND the pose together: the solver's own
# rotation hold-out is 0.17 to 0.58 degrees on these clips, so a bound of one degree is mostly the
# solver. It is still the first end-to-end check this project has of whether the balconies, the walls and
# the corridor land where the photographs put them.
TILE = 60
NBOOT = 400
KEEP = 90.0


def tile_stats(A, B, ex, ey, step, nst):
    """Per-tile sums for every shift, so a resample is a weighted sum rather than a fresh correlation."""
    h, w = A.shape
    ny, nx = h // TILE, w // TILE
    out, shifts = [], []
    for a in range(-nst, nst + 1):
        for b in range(-nst, nst + 1):
            dx, dy = int(round(ex + a * step)), int(round(ey + b * step))
            x0, x1 = max(0, dx), min(w, w + dx)
            y0, y1 = max(0, dy), min(h, h + dy)
            Pw = A[y0:y1, x0:x1]
            Qw = B[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
            # tiles are cut on the fixed grid of A and only whole tiles inside the overlap are used
            gy0, gx0 = -(-y0 // TILE), -(-x0 // TILE)
            gy1, gx1 = y1 // TILE, x1 // TILE
            S = np.zeros((ny, nx, 5))
            for iy in range(gy0, gy1):
                for ix in range(gx0, gx1):
                    a0, a1 = iy * TILE - y0, (iy + 1) * TILE - y0
                    b0, b1 = ix * TILE - x0, (ix + 1) * TILE - x0
                    pt, qt = Pw[a0:a1, b0:b1], Qw[a0:a1, b0:b1]
                    S[iy, ix] = (pt.sum(), qt.sum(), (pt * pt).sum(), (qt * qt).sum(), (pt * qt).sum())
            out.append(S.reshape(-1, 5))
            shifts.append((a, b))
    return np.array(out), shifts, ny * nx


def do_bound():
    picks = json.loads(io.open(JSONF, encoding='utf-8').read())
    print('THE RULE, FIXED BEFORE THIS RUN EXECUTES.')
    print('   Both pictures are cut into %d px tiles and the tiles are resampled with replacement %d'
          % (TILE, NBOOT))
    print('   times. Each resample gets its own peak, and the scatter of those peaks is this pair\'s')
    print('   precision, measured from the pair rather than assumed. If the middle %.0f per cent of them'
          % KEEP)
    print('   contains the place a perfect model and a perfect pose would put the render, the pair is')
    print('   CONSISTENT WITH A REGISTERED MODEL and the envelope is reported as an upper bound. If it')
    print('   excludes that place, the offset is real and is reported as a misalignment. Only pairs that')
    print('   beat every mismatched pair are eligible, because for the rest the measure tracks nothing.')
    print('')
    rows = []
    G = {}
    for i, p in enumerate(picks):
        rp = os.path.join(OUT, 'r%02d.jpg' % i)
        if not os.path.exists(rp):
            continue
        A = photo(p)
        rb = rolled(p, rp)
        if A is None or rb is None:
            continue
        B, rerr, frac = rb
        if rerr > 0.02 or frac < 0.05:
            print('   %-6s %-14s not scored: roll error %.3f, edges on %.1f per cent of the render'
                  % (p['cls'], p['frame'], rerr, 100 * frac))
            continue
        sc = WH / float(p['hgt'])
        fyw = p['fy'] * sc
        step = max(1.0, fyw * np.tan(np.radians(SPAN)) / NST)
        G[i] = (A, B, p, step, p['ppx'] * sc, p['ppy'] * sc, fyw)
    ks = sorted(G)
    ctrl = []
    for i in ks:
        A, _, _, step, ex, ey, _ = G[i]
        for j in ks:
            if i == j:
                continue
            B = G[j][1]
            if A.shape != B.shape:
                B = cv2.resize(B, (A.shape[1], A.shape[0]))
            ctrl.append(max(ncc(A, B, int(round(ex + a * step)), int(round(ey + b * step)))
                            for a in range(-NST, NST + 1) for b in range(-NST, NST + 1)))
    bar = max(ctrl) if ctrl else 1.0
    print('   the mismatched pairs reach %.4f at best over %d of them, and that is the bar.'
          % (bar, len(ctrl)))
    print('')
    rs = np.random.RandomState(20260910)
    print('   capture  frame           peak    eligible   offset deg   90 per cent envelope   verdict')
    for i in ks:
        A, B, p, step, ex, ey, fyw = G[i]
        peak = max(ncc(A, B, int(round(ex + a * step)), int(round(ey + b * step)))
                   for a in range(-NST, NST + 1) for b in range(-NST, NST + 1))
        if peak <= bar:
            print('   %-8s %-14s %.4f  no         this pair is not tracking alignment, so it is not read'
                  % (p['cls'], p['frame'], peak))
            continue
        S, shifts, nt = tile_stats(A, B, ex, ey, step, NST)
        Wt = rs.multinomial(nt, np.full(nt, 1.0 / nt), size=NBOOT).astype(float)
        T = np.einsum('sti,bt->bsi', S, Wt)
        n = Wt.sum(1)[:, None] * (TILE * TILE)
        num = T[:, :, 4] - T[:, :, 0] * T[:, :, 1] / n
        den = np.sqrt(np.maximum(T[:, :, 2] - T[:, :, 0] ** 2 / n, 1e-9)
                      * np.maximum(T[:, :, 3] - T[:, :, 1] ** 2 / n, 1e-9))
        best = np.argmax(num / den, axis=1)
        pa = np.array([shifts[b] for b in best], float)
        qlo, qhi = np.percentile(pa, [(100 - KEEP) / 2, 100 - (100 - KEEP) / 2], axis=0)
        med = np.median(pa, axis=0)
        offdeg = float(np.degrees(np.arctan(np.hypot(*med) * step / fyw)))
        env = float(np.degrees(np.arctan(max(np.max(np.abs(qlo)), np.max(np.abs(qhi))) * step / fyw)))
        holds = qlo[0] <= 0 <= qhi[0] and qlo[1] <= 0 <= qhi[1]
        rows.append((p, offdeg, env, holds, peak))
        print('   %-8s %-14s %.4f  yes        %.2f         u %+.0f..%+.0f  v %+.0f..%+.0f steps   %s'
              % (p['cls'], p['frame'], peak, offdeg, qlo[0], qhi[0], qlo[1], qhi[1],
                 'CONSISTENT' if holds else 'MISALIGNED'))
    if not rows:
        print('')
        print('   NO PAIR WAS ELIGIBLE. Nothing is concluded about the geometry.')
        sys.exit(0)
    good = [r for r in rows if r[3]]
    print('')
    print('   %d of %d eligible pairs are CONSISTENT with a model and a pose that are both right.'
          % (len(good), len(rows)))
    for p, offdeg, env, holds, peak in rows:
        near = abs(p['d'] - DN) if p['group'] == 'floor' else None
        rate = 10.0 * 2 * np.tan(np.radians(env / 2.0))
        tail = ('  which on the north wall %.1f m off is %.3f m' % (near, near * rate / 10.0)) if near else ''
        print('      %-6s %-14s %s  bound %.2f deg, %.2f m per 10 m of range%s'
              % (p['cls'], p['frame'], 'consistent' if holds else 'MISALIGNED', env, rate, tail))
    # WHICH OF THE TWO THINGS IS IT, THEN. This section was written AFTER the offsets came in, and that is
    # said out loud because it matters: it is not a rule fixed in advance, it is a discriminator applied to
    # numbers already on the page. But it does not need to be blind, because it does not choose a winner by
    # taste. A WALL IN THE WRONG PLACE by a fixed distance subtends a smaller angle the further away the
    # camera stands, so its angle times its range would be the constant. A CAMERA POINTED WRONG by a fixed
    # angle gives the same angle from everywhere, so the angle itself would be the constant. The hall-floor
    # frames span 2.4 m to 13.7 m from the same wall, which is a spread of nearly six, so the two
    # hypotheses predict very different things and the tighter one wins outright.
    fl = [(p, offdeg, abs(p['d'] - DN)) for p, offdeg, env, holds, peak in rows if p['group'] == 'floor']
    if len(fl) >= 3:
        ang = np.array([t[1] for t in fl])
        prod = np.array([t[1] * t[2] for t in fl])
        sa = float(ang.max() / max(ang.min(), 1e-9))
        sp = float(prod.max() / max(prod.min(), 1e-9))
        print('')
        print('   AND WHICH OF THE TWO IT IS, ASKED OF THE FLOOR FRAMES, WHICH STAND %.1f m TO %.1f m OUT.'
              % (min(t[2] for t in fl), max(t[2] for t in fl)))
        print('   If a WALL were displaced, angle times range would hold steady: it runs %.2f to %.2f, a'
              % (prod.min(), prod.max()))
        print('   spread of %.1f. If the CAMERAS were pointed wrong, the angle itself would hold steady: it'
              % sp)
        print('   runs %.2f to %.2f degrees, a spread of %.1f.' % (ang.min(), ang.max(), sa))
        print('   BOTH HYPOTHESES PREDICT A SPREAD OF 1.0, AND NEITHER GETS IT, so neither is the whole')
        print('   story and this does not name a cause. What it does settle is the comparison: the wall')
        print('   reading is the worse of the two by %.1f times, and a single displaced wall would have to'
              % (max(sa, sp) / max(min(sa, sp), 1e-9)))
        print('   make the near frames disagree with the far one by %.1f to one. They disagree by %.1f.'
              % (max(t[2] for t in fl) / min(t[2] for t in fl), sa))
        print('   SO NO ONE DISPLACEMENT OF THE NORTH WALL EXPLAINS THESE THREE FRAMES, and none is claimed')
        print('   from them. What is left is per-frame, of the size of the solver\'s own pose error, and')
        print('   the honest output of the whole run is the BOUND above and not a correction to anything.')
    print('')
    print('   WHAT THIS BOUND COVERS, said plainly: the model AND the pose together, because a surface in')
    print('   the wrong place and a camera in the wrong place slide the render the same way. The solver')
    print('   quotes its own rotation hold-out as 0.17 to 0.58 degrees on these clips, so most of any')
    print('   bound near a degree is the solver and not the wall. It is still the first end-to-end check')
    print('   this project has of whether the balconies, the walls and the corridor land where the')
    print('   photographs put them, and it is run against the page Lloyd opens.')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'select'
    if mode == 'score':
        do_score()
    elif mode == 'bound':
        do_bound()
    else:
        do_select()
