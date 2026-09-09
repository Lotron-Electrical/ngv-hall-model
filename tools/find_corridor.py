# 2026-09-10: find the frames shot INSIDE the corridor behind the north brick wall, out of 900 that were
# mostly shot looking out of it.
#
# WHY IT MATTERS. The corridor is the least measured thing in this model. Its width 1.420 comes from one
# crossing of a lamp locus with a back wall, its ceiling 10.947 from the same crossing, and its floor 8.34
# is not measured at all. tools/opening_probe.py established why: from the hall floor an opening is 100 to
# 150 px wide carrying under 20 grey levels of signal, the head soffit stands over the reveal so upward
# sightlines end on its underside, and no posed frame in the archive is inside that room.
# BUT LLOYD STOOD IN IT. b1, b4 and b5 are all posed with the camera on d -0.45 to +0.12, which is IN the
# openings, h 9.07 to 10.14. Every accepted frame of those clips points OUT at the hall, because that is
# what the registrar could solve. The frames where he turned round are still in the extraction, unposed.
#
# HOW TO FIND THEM WITHOUT A POSE. A frame looking out of an opening carries two things a frame looking
# into the corridor cannot: the stained-glass canopy, which is the most saturated thing in this building,
# and the hall's pink event carpet. A frame inside the corridor has neither, is darker, and is full of
# straight horizontal stone joints. So score every frame on saturation, on how much of it is carpet, and
# on how much horizontal edge it carries, and rank. Nothing here is a measurement; it is a way of not
# having to look at nine hundred frames by hand, and every frame it nominates gets looked at.
#   python tools/find_corridor.py <clip> [<clip> ...]
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
TOP = int(os.environ.get('TOP', '14'))

for clip in sys.argv[1:]:
    src = '%s/%s/images' % (B2, clip)
    if not os.path.isdir(src):
        print('%s: no frames' % clip)
        continue
    names = sorted(n for n in os.listdir(src) if n.lower().endswith(('.png', '.jpg', '.jpeg')))
    rows = []
    for n in names:
        im = cv2.imread(os.path.join(src, n))
        if im is None:
            continue
        s = 260.0 / max(im.shape[:2])
        im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
        hue, sat_c, val = cv2.split(cv2.cvtColor(im, cv2.COLOR_BGR2HSV))
        sat = float(sat_c.mean())
        # the carpet: a broad pink to salmon band, bright, low to middling saturation
        carpet = float(np.logical_and.reduce([
            np.logical_or(hue < 12, hue > 168), sat_c > 25, sat_c < 110, val > 95]).mean())
        # the glass: small very saturated patches
        glass = float(np.logical_and(sat_c > 150, val > 120).mean())
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
        gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3))
        horiz = float((gy.mean() + 1e-6) / (gx.mean() + 1e-6))
        dark = 1.0 - float(val.mean()) / 255.0
        score = (1.0 - min(1.0, glass * 14)) * (1.0 - min(1.0, carpet * 4)) * (0.4 + 0.6 * dark) \
            * min(1.6, horiz)
        rows.append((score, n, sat, carpet, glass, horiz, dark))
    rows.sort(reverse=True)
    print('%s: %d frames' % (clip, len(rows)))
    print('   score  frame            sat   carpet   glass   horiz/vert   dark')
    for r in rows[:TOP]:
        print('   %.3f  %-16s %5.1f  %6.3f  %6.4f  %8.2f  %7.2f'
              % (r[0], r[1].rsplit('.', 1)[0], r[2], r[3], r[4], r[5], r[6]))
    runs, cur = [], []
    for r in sorted(rows[:TOP], key=lambda z: z[1]):
        k = int(''.join(c for c in r[1] if c.isdigit())[-6:])
        if cur and k - cur[-1] <= 12:
            cur.append(k)
        else:
            if cur:
                runs.append(cur)
            cur = [k]
    if cur:
        runs.append(cur)
    print('   runs worth looking at: %s' % ', '.join('%d-%d' % (r[0], r[-1]) for r in runs))
    print('')
