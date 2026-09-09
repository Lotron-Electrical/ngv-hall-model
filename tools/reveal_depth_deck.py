# 2026-09-10: THE WALL THICKNESS READ FROM THE DECKS, WHERE THE FAR REVEAL OF AN OPENING FACES THE CAMERA.
#
# WHY THIS WORKS WHERE reveal_depth.py COULD NOT. From inside an opening the corridor arris is behind the
# operator's shoulder and no frame turned round (317 frames, none with the band in view). But a camera on
# an END DECK looking along the hall sees the nearest openings nearly along the wall, and the reveal on
# the FAR jamb of each of those openings faces it square: a stone strip openDepth wide, from the hall arris
# to the corridor arris, with the unlit corridor beyond. From the east deck the west reveals of openings
# 11 and 12 (163 posed frames, day4k and b3); from the west deck the east reveals of openings 1 and 2
# (b7s, four frames, and the pan set). Nothing about the sightline is subtle: it crosses the face above the
# parapet and enters the wall plane inside the aperture, which the code checks per frame before reading.
#
# THE INSTRUMENT is reveal_depth.py's, unchanged: sweeps in d ON the reveal plane at seven heights, each
# frame read on its own, the number read being the SEPARATION of the hall arris and the corridor arris so
# a pose shift common to both cancels, and an invented plane in the open air of the aperture as the null.
#
# THE DECISION RULE, FIXED BEFORE THE NUMBERS ARE OPENED, the same as reveal_depth.py's.
#   1. Hall arris = strongest gradient within 0.15 m of the drawn -0.030. Corridor arris = strongest
#      gradient within 0.35 m of the drawn -0.930. A frame that does not show both is not read.
#   2. THE NULL, per frame: the same sweep on an invented plane 0.60 m into the aperture from the jamb,
#      judged in the corridor band. A frame whose real plane does not beat it is a miss.
#   3. A jamb is LIVE when eight or more frames read it and the real plane beats the invented one in
#      seventy percent of them or more.
#   4. THE SECOND CONTROL is agreement: two live jambs or more from two different openings, medians
#      within 0.10 m. A jamb whose 10th-to-90th half-width exceeds 0.15 m is reported but not used.
#   5. The number claimed is the median over the usable jambs, to no better than 0.05 m.
#
# WHAT IT CANNOT DO. The east deck reads the far reveals from 3 to 8 m off, with 15 to 25 degrees between
# the sightline and the wall; the pan sets are left out because their far-field rotation error (0.36 deg)
# is a 50 mm shift on a strip 900 mm wide. It reads four openings and speaks for those.
#
# THE RESULT (2026-09-10, first run). East deck, 163 frames: opening 12's far reveal is read by none of
# them (the full sweep is never inside the frame at three heights), opening 11's by ten, and on those ten
# the real plane beats the invented one in five, 50% where the rule asks 70%, with a separation median of
# 0.780 m and a 10th-to-90th half-width of 0.245. Not live. West deck, 7 frames: neither reveal read. So
# by the rule written before the run no thickness is claimed, and openDepth 0.90 stands untested by a
# second route: from inside the openings nobody turned round, and from the decks too few frames hold a
# whole reveal and the null holds its own on those that do. The 0.780 median from ten frames with a
# 0.245 half-width is recorded and not used: a claim must not be smaller than its own spread.
#   hwq run --gb 3 --label "reveal depth from the decks" -- python -u tools/reveal_depth_deck.py
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
DECKS = {'east': ('day4k', 'b3'), 'west': ('b7s',)}
DSTEP = 0.010
FRONTW = 0.15
BACKW = 0.35
HS = (9.0, 9.3, 9.6, 9.9, 10.2, 10.5, 10.8)
MINFR = 8
BEAT = 0.70
TOL = 0.10
SPREADMAX = 0.15
MARGIN = 20
NULLOFF = 0.60

src = io.open('index.html', encoding='utf-8').read()
mo = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
OPEN = [(float(a), float(b)) for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', mo.group(1))]
DN = float(re.search(r'dNorth:(-?[0-9.]+)', src).group(1))
DEPTH = float(re.search(r'openDepth:\s*([0-9.]+)', src).group(1))
_i = src.index('const ENDW={')
BLOCK = src[_i:src.index('\n', _i)]
WFACE = float(re.search(r'\bwest:\s*([0-9.]+)', BLOCK).group(1)) + float(re.search(r'\bface:\s*([0-9.]+)', BLOCK).group(1))
EFACE = float(re.search(r'\beast:\s*([0-9.]+)', BLOCK).group(1)) - float(re.search(r'\bface:\s*([0-9.]+)', BLOCK).group(1))
DR = DN - DEPTH
DS = np.arange(DN + 0.30, DR - 0.70 - 1e-9, -DSTEP)
# from the east deck the far reveal is the WEST jamb (u0) of openings 12 and 11; from the west deck the EAST
# jamb (u1) of openings 1 and 2. s is the direction from the jamb into the aperture.
TARGETS = {'east': [(12, OPEN[11][0], +1), (11, OPEN[10][0], +1)],
           'west': [(1, OPEN[0][1], -1), (2, OPEN[1][1], -1)]}


def sweep(cam, img, uplane):
    got = np.zeros(len(DS))
    cnt = np.zeros(len(DS))
    for h in HS:
        pts = np.array([O + uplane * HU + d * HD + np.array([0.0, h, 0.0]) for d in DS])
        x, y, z = cam.project(pts)
        ok = z > 0.5
        ok = np.logical_and(ok, x > MARGIN)
        ok = np.logical_and(ok, x < cam.w - MARGIN)
        ok = np.logical_and(ok, y > MARGIN)
        ok = np.logical_and(ok, y < cam.h - MARGIN)
        if ok.sum() < 0.9 * len(DS):
            continue
        xi = np.clip(x.astype(int), 0, img.shape[1] - 1)
        yi = np.clip(y.astype(int), 0, img.shape[0] - 1)
        v = img[yi, xi].astype(np.float64)
        got[ok] += v[ok]
        cnt[ok] += 1
    if (cnt > 0).sum() < 0.9 * len(DS) or cnt.max() < 3:
        return None
    out = np.full(len(DS), np.nan)
    nz = cnt > 0
    out[nz] = got[nz] / cnt[nz]
    if np.isnan(out).any():
        return None
    return out - out.mean()


def grad(prof):
    g = np.abs(np.gradient(prof))
    return np.convolve(g, np.ones(3) / 3.0, mode='same')


def peak(g, lo, hi):
    win = np.logical_and(DS >= lo, DS <= hi)
    i = int(np.argmax(np.where(win, g, -1)))
    return float(DS[i]), float(g[i])


def through_aperture(cu, cd, uj, s, u0, u1):
    """does the ray from the camera to the reveal's mid-depth cross the wall plane inside this opening?"""
    tu, td = uj, DR + 0.5 * DEPTH
    t = (DN - cd) / (td - cd) if abs(td - cd) > 1e-6 else -1
    if t <= 0 or t > 1:
        return False
    uw = cu + t * (tu - cu)
    return u0 + 0.05 < uw < u1 - 0.05


def main():
    print('THE DECISION RULE, WRITTEN OUT BEFORE THE NUMBERS ARE OPENED.')
    print('   From an end deck the far reveal of the nearest openings faces the camera. Each reveal plane is')
    print('   swept in d over %d heights per frame; the number read is the SEPARATION of the hall arris' % len(HS))
    print('   (strongest gradient within %.2f of %.3f) and the corridor arris (within %.2f of %.3f).'
          % (FRONTW, DN, BACKW, DR))
    print('   The null is the same sweep on an invented plane %.2f m into the aperture, judged in the corridor'
          % NULLOFF)
    print('   band. A jamb is live with %d frames and the real plane winning %.0f%% of them; two live jambs'
          % (MINFR, 100 * BEAT))
    print('   from two openings within %.2f m, half-widths under %.2f m, are needed to claim, to 0.05 m.'
          % (TOL, SPREADMAX))
    print('')
    results = {}
    for deck, classes in DECKS.items():
        frames = []
        for cn in classes:
            try:
                fr = U.load_class(cn)
            except Exception as ex:
                print('   %s: not loaded (%s)' % (cn, ex))
                continue
            for k, (cam, ip) in sorted(fr.items()):
                q = cam.center - O
                cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
                ondeck = (cu < WFACE + 0.3) if deck == 'west' else (cu > EFACE - 0.3)
                if ondeck and ch > 9.0:
                    frames.append((cn, k, cam, ip, cu, cd, ch))
        print('   %s deck: %d posed frames standing on it' % (deck, len(frames)))
        for oi, uj, s in TARGETS[deck]:
            u0, u1 = OPEN[oi - 1]
            seps, wins, used = [], 0, {}
            for cn, k, cam, ip, cu, cd, ch in frames:
                if not through_aperture(cu, cd, uj, s, u0, u1):
                    continue
                img = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                prof = sweep(cam, img, uj)
                if prof is None:
                    continue
                g = grad(prof)
                df, gf = peak(g, DN - FRONTW, DN + FRONTW)
                db, gb = peak(g, DR - BACKW, DR + BACKW)
                nprof = sweep(cam, img, uj + s * NULLOFF)
                if nprof is None:
                    continue
                _, nb = peak(grad(nprof), DR - BACKW, DR + BACKW)
                seps.append(df - db)
                wins += 1 if gb > nb else 0
                used[cn] = used.get(cn, 0) + 1
            if not seps:
                print('      opening %2d far jamb u %.3f: no frame reads it' % (oi, uj))
                continue
            seps = np.array(seps)
            n = len(seps)
            med = float(np.median(seps))
            p10, p90 = float(np.percentile(seps, 10)), float(np.percentile(seps, 90))
            half = 0.5 * (p90 - p10)
            live = n >= MINFR and wins / n >= BEAT
            usable = live and half <= SPREADMAX
            results[oi] = dict(n=n, wins=wins, med=med, p10=p10, p90=p90, half=half, live=live, usable=usable)
            print('      opening %2d far jamb u %.3f: %3d frames (%s), real beats invented in %3d (%.0f%%)'
                  % (oi, uj, n, ', '.join('%s %d' % t for t in sorted(used.items())), wins, 100.0 * wins / n))
            print('         separation median %.3f m, 10th to 90th %.3f to %.3f (half-width %.3f): %s'
                  % (med, p10, p90, half, 'LIVE and usable' if usable else
                     'live but SPREAD TOO WIDE to use' if live else 'not live' + ('' if n >= MINFR else ' (too few frames)')))
    print('')
    use = {k: r for k, r in results.items() if r['usable']}
    if len(use) < 2:
        print('   FEWER THAN TWO USABLE JAMBS (%d), so by the rule above no thickness is claimed and the drawn'
              % len(use))
        print('   %.2f m stands untested by this.' % DEPTH)
        return
    meds = [r['med'] for r in use.values()]
    if max(meds) - min(meds) > TOL:
        print('   THE USABLE JAMBS DISAGREE: medians %s, spread %.3f m over the %.2f tolerance, so no number'
              % (', '.join('%.3f' % m for m in meds), max(meds) - min(meds), TOL))
        print('   is claimed and %.2f stands untested.' % DEPTH)
        return
    m = float(np.median(meds))
    print('   %d USABLE JAMBS AGREE: medians %s, claimed as %.2f m against %.2f drawn, %+.0f mm.'
          % (len(use), ', '.join('%.3f' % v for v in meds), round(m, 2), DEPTH, 1000 * (m - DEPTH)))
    if abs(m - DEPTH) <= 0.05:
        print('   Inside 0.05 m: the drawn thickness is CONFIRMED, and for the first time it is a measurement.')
    else:
        print('   Outside 0.05 m at every usable jamb: the drawn thickness is wrong by that much and the file')
        print('   should carry %.2f m.' % round(m, 2))


if __name__ == '__main__':
    main()
