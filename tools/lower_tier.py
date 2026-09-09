# 2026-09-09: the lower end balcony as drawn is 1.75 m high inside, which is not a room. Stop asserting
# the contradiction and try to measure the tier out of it.
#
# THE CONTRADICTION. tools/check_bounds.py now carries it: the lower deck 6.33 and the ceiling over it
# 8.08 were both read off ONE 4K frame, d4_000049, and their difference is 1.75 m of clear height over a
# floor 3.85 m deep with a balustrade drawn on its edge. A balustrade says people stand there. 1.75 m
# says they cannot. Three things could be true and one frame cannot separate them:
#   the 6.32 row is a PARAPET or a fascia and not a floor, so the real deck is lower;
#   the 8.08 row hangs UNDER the real ceiling, so the real ceiling is higher;
#   or the band is not occupied at all, in which case the drawn rail on 7.16 is the wrong element.
#
# WHY THIS BAND CAN BE READ WHEN THE ONE ABOVE IT COULD NOT. Three instruments failed on the gallery
# ceiling because the face plane up there is OPEN AIR: nothing at u 48.056 and h 11 reflects light, so a
# pixel on that path shows whatever stands thirty metres behind it. Below the upper deck the end face is
# SOLID all the way down: a stone ground wall to about 5.3, a dark perforated apron under the lower
# balcony, then that balcony's own parapet. A step in brightness on that plane is a step on a real
# surface, so the oldest instrument in this archive is legitimate here.
#
# ONE UNKNOWN PER RAY. The face station is fixed at the drawn plane and only the HEIGHT is solved, which
# is what a horizontal feature on a vertical plane actually determines. Nothing slides.
#
# THE NULL IS NOT OPTIONAL AND IT IS NOT A FORMALITY. Tonight a null already beat its signal once, on the
# textured parapet, so the same ladder is walked on the north wall's PIERS: plain ashlar between openings
# at the same heights, same lighting, same cameras, same detector, and nothing drawn on it. Whatever the
# piers pile up on is what the machinery does to blank stone, and any end-face peak has to beat it.
#
# AND THE WINDOW HAS TO NOT MATTER. A difference-of-means detector reports a peak inside any smooth
# gradient and that peak walks with the window, which is exactly how a third line above the balcony fronts
# was withdrawn this afternoon. Three half-windows are run, 0.16, 0.28 and 0.44 m, and a height only
# counts if all three put it in the same place.
#
# THE BLIND ZONE IS SUBTRACTED, NOT IGNORED. A difference of means over HWIN samples cannot see within
# HWIN*STEP of either end of its ladder, and with nothing to find it reports that boundary. The ladder is
# run wider than the band of interest and only the interior is kept.
import os
import sys
from collections import defaultdict

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
VY = np.array([0.0, 1.0, 0.0])

STEP = 0.01
HWINS = [8, 14, 22]                       # 0.16, 0.28 and 0.44 m half-windows
HLO, HHI = 4.20, 9.60                     # the ladder
BLO, BHI = 4.20 + 0.44, 9.60 - 0.44       # the band the widest window can actually see
CONTRAST = float(os.environ.get('CONTRAST', '9'))
STRIDE = int(os.environ.get('STRIDE', '1'))
NSTAT = 14
BIN = 0.02
DS = 15.364
DN = -0.030

FACES = {'west': 4.194, 'east': 48.056}
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.917, 20.130],
        [22.565, 23.778], [26.213, 27.426], [29.963, 31.175], [33.642, 34.853], [37.177, 38.383],
        [40.906, 42.118], [44.526, 45.739]]
PIERS = [[OPEN[i][1] + 0.35, OPEN[i + 1][0] - 0.35] for i in range(len(OPEN) - 1)]
PIERS = [p for p in PIERS if p[1] - p[0] > 0.8]

DRAWN = [(5.30, 'ground wall top, unmeasured'), (6.33, 'the lower deck as drawn'),
         (6.85, 'lower upstand top, unmeasured'), (7.16, 'lower rail top, unmeasured'),
         (8.08, 'the ceiling over it as drawn'), (8.34, 'the upper deck')]


def world(u, d, lev):
    return O + u * HU + d * HD + lev * VY


def profile(im, cam, u, d):
    levs = np.arange(HLO, HHI + 1e-9, STEP)
    P = np.array([world(u, d, lv) for lv in levs])
    x, y, z = cam.project(P)
    H, W = im.shape[:2]
    ok = np.logical_and.reduce([z > 0.3, x > 1, y > 1, x < W - 2, y < H - 2])
    if not ok.any():
        return None, None
    best_a, best_b, a = 0, 0, None
    for i, v in enumerate(list(ok) + [False]):
        if v and a is None:
            a = i
        elif not v and a is not None:
            if i - a > best_b - best_a:
                best_a, best_b = a, i
            a = None
    if best_b - best_a < 3 * max(HWINS) + 1:
        return None, None
    sl = slice(best_a, best_b)
    return levs[sl], im[np.rint(y[sl]).astype(int), np.rint(x[sl]).astype(int)].astype(np.float64)


def edges(levs, v, hwin):
    # every step this window can see, not only the strongest: a tier has several horizontals and taking
    # one per profile is how a detector gets told which answer to bring back
    n = len(v)
    if n < 3 * hwin + 2:
        return []
    s = np.array([v[i - hwin:i].mean() - v[i + 1:i + 1 + hwin].mean()
                  for i in range(hwin, n - hwin)])
    mid = levs[hwin:n - hwin]
    out = []
    for i in range(1, len(s) - 1):
        a = abs(s[i])
        if a < CONTRAST:
            continue
        if a >= abs(s[i - 1]) and a > abs(s[i + 1]):
            if BLO <= mid[i] <= BHI:
                out.append((float(mid[i]), float(s[i])))
    return out


acc = {(w, k): defaultdict(float) for w in HWINS for k in ('west', 'east', 'null')}
cnt = {(w, k): 0 for w in HWINS for k in ('west', 'east', 'null')}
nframe = 0
for cls in ('walk', 'night', 'day4k'):
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    keys = sorted(frames)[::STRIDE]
    for k in keys:
        cam, ipath = frames[k]
        if not os.path.exists(ipath):
            continue
        im = cv2.imread(ipath, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        im = cv2.GaussianBlur(im, (5, 5), 0)
        nframe += 1
        q = cam.center - O
        cu = float(q @ HU)
        for end, uf in FACES.items():
            if abs(cu - uf) < 4.0 or abs(cu - uf) > 34.0:
                continue
            for d in np.linspace(1.2, DS - 1.2, NSTAT):
                levs, v = profile(im, cam, uf, d)
                if levs is None:
                    continue
                for w in HWINS:
                    for lv, s in edges(levs, v, w):
                        acc[(w, end)][round(lv / BIN)] += 1.0
                    cnt[(w, end)] += 1
        # THE NULL, on the same frames and the same ladder: plain ashlar between the north openings
        for u0, u1 in PIERS:
            for u in np.linspace(u0 + 0.15, u1 - 0.15, 3):
                levs, v = profile(im, cam, u, DN)
                if levs is None:
                    continue
                for w in HWINS:
                    for lv, s in edges(levs, v, w):
                        acc[(w, 'null')][round(lv / BIN)] += 1.0
                    cnt[(w, 'null')] += 1

print('%d frames read, ladder h %.2f to %.2f, the widest window can see %.2f to %.2f'
      % (nframe, HLO, HHI, BLO, BHI))
print('contrast bar %.0f grey levels, %d stations across each face, %d piers as the null'
      % (CONTRAST, NSTAT, len(PIERS)))
print('')


def peaks(w, key, topn=8):
    hist = acc[(w, key)]
    if not hist or cnt[(w, key)] == 0:
        return []
    out = []
    for kk in sorted(hist):
        # a peak beats both its neighbours, so a broad shoulder is not counted twice
        if hist[kk] >= hist.get(kk - 1, 0.0) and hist[kk] > hist.get(kk + 1, 0.0) and hist[kk] >= 3:
            out.append((hist[kk] / cnt[(w, key)], kk * BIN))
    out.sort(reverse=True)
    return out[:topn]


for key in ('west', 'east', 'null'):
    print('   %-5s  %d profiles at the widest window' % (key, cnt[(HWINS[-1], key)]))
    for w in HWINS:
        pk = peaks(w, key, 6)
        print('     half-window %.2f m: %s'
              % (w * STEP, '  '.join('h %.2f (%.2f/profile)' % (b, a) for a, b in pk) or 'nothing'))
    print('')

# WHAT SURVIVES ALL THREE WINDOWS. A height only counts if every window puts a peak within 30 mm of it,
# because a peak that walks with the window is a gradient and not an edge.
print('   heights that hold through all three windows, and what the null does at the same height:')
held = {}
for key in ('west', 'east'):
    for _, cand in peaks(HWINS[0], key, 40):
        hits, strength = [], []
        for w in HWINS:
            near = [(a, b) for a, b in peaks(w, key, 40) if abs(b - cand) <= 0.03]
            if not near:
                break
            hits.append(max(near)[1])
            strength.append(max(near)[0])
        if len(hits) < len(HWINS):
            continue
        nul = [a for a, b in peaks(HWINS[1], 'null', 40) if abs(b - cand) <= 0.06]
        held.setdefault(key, []).append((float(np.mean(strength)), float(np.mean(hits)),
                                         max(hits) - min(hits), max(nul) if nul else 0.0))
for key in ('west', 'east'):
    rows = sorted(held.get(key, []), reverse=True)[:8]
    print('   %s:' % key)
    if not rows:
        print('     nothing survives three windows')
    for st, lv, sp, nul in rows:
        tag = ''
        for dlev, what in DRAWN:
            if abs(dlev - lv) <= 0.08:
                tag = '  <- %.2f, %s' % (dlev, what)
        beat = ('beats its null %.1fx' % (st / nul)) if nul > 1e-9 else 'null is silent here'
        print('     h %.2f  window spread %.0f mm  %.2f per profile, %s%s'
              % (lv, 1000 * sp, st, beat, tag))
print('')
print('   HOW TO READ THIS. A height that holds through three windows AND beats the pier null by three')
print('   is a real horizontal on that face. The drawn tier needs two of them about 2.4 m apart to be a')
print('   room; 1.75 m apart is what this file currently draws and cannot be walked in.')
