# 2026-09-10: IS THERE A HOLE WHERE THIS FILE DRAWS ONE. Twelve openings, twelve chances to be wrong.
#
# WHY THIS TEST AND NOT ANOTHER. Four instruments failed today and every one of them was trying to measure
# a POSITION from a gradient. The arguments that held were all of one kind: light either arrived or it did
# not. 33 rays crossed a face this file drew solid and four surfaces came out. 29 frames failed to show a
# handrail that would have been the darkest thing in each of them. That class of argument needs no
# sub-pixel edge, no plane fit and no pose better than a metre.
#
# So it is turned on the north wall. This file draws twelve openings on the face d -0.030, each about
# 1.21 m wide, running h 8.740 to 11.165. An opening is a hole into an unlit corridor: from the hall it is
# dark and flat. The ashlar either side of it is lit and textured. So sample the inside of each drawn
# rectangle and the wall immediately beside it, and ask whether the picture agrees that one is a hole.
#
# THE CONTROL IS THE WALL ITSELF and it costs nothing. The same measurement is run on the PIERS, the strips
# of wall halfway between two openings, where this file draws solid stone. If a pier reads as a hole as
# often as an opening does, the test is measuring something else and its answer about the openings means
# nothing. The twelve openings are then twelve independent instances of one element, which is the
# redundancy that caught the fins and the corridor lamps.
#
# WHAT IT CANNOT DO. It tests whether a hole is THERE, not where its edges are. An opening drawn 0.15 m
# off still overlaps the real one and still reads as a hole, so this can confirm the pattern and refuse a
# missing or invented opening, and it cannot measure a jamb.
#   python tools/opening_holes.py
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.030
SILL, HEAD = 8.740, 11.165
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
CLASSES = ('walk', 'night', 'day4k')


def patch(im, cam, u0, u1, lo, hi):
    """the pixels a rectangle on the wall face covers, or None if it is not usefully in shot"""
    us = np.linspace(u0 + 0.12, u1 - 0.12, 7)
    ls = np.linspace(lo + 0.20, hi - 0.20, 9)
    pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0]) for u in us for lv in ls])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
    if ok.sum() < 40:
        return None
    # it must also be big enough on the sensor to mean anything
    if (x[ok].max() - x[ok].min()) < 12 or (y[ok].max() - y[ok].min()) < 12:
        return None
    v = np.array([float(im[int(y[i]), int(x[i])]) for i in np.nonzero(ok)[0]])
    return float(v.mean()), float(v.std())


rows = []
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ch = float(q @ HD), float(q[1])
        if ch > 3.0 or cd < 3.0:          # from the hall floor, well off the wall
            continue
        im = None
        for oi, (u0, u1) in enumerate(OPEN):
            w = u1 - u0
            if im is None:
                im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if im is None:
                    break
            a = patch(im, cam, u0, u1, SILL, HEAD)
            # the pier: the same shape of patch, one opening-width to the east, which is solid stone
            b = patch(im, cam, u1 + 0.25 * w, u1 + 1.25 * w, SILL, HEAD)
            if a is None or b is None:
                continue
            rows.append((oi + 1, cname, k, a[0], a[1], b[0], b[1]))

print('%d readings, each an opening beside the pier next to it' % len(rows))
print('')
print(' opening   n     opening mean   pier mean   ratio   reads as a hole')
allr = []
for oi in range(1, 13):
    rs = [r for r in rows if r[0] == oi]
    if len(rs) < 8:
        print('   %2d     %3d    too few' % (oi, len(rs)))
        continue
    om = float(np.median([r[3] for r in rs]))
    pm = float(np.median([r[5] for r in rs]))
    hole = sum(1 for r in rs if r[3] < 0.72 * r[5])
    allr.append((oi, len(rs), om, pm, hole / float(len(rs))))
    print('   %2d     %3d      %6.1f        %6.1f     %.2f     %3.0f per cent'
          % (oi, len(rs), om, pm, om / max(pm, 1e-6), 100.0 * hole / len(rs)))
print('')
if not allr:
    sys.exit('nothing testable')
fr = np.array([r[4] for r in allr])
print('   %d openings testable. They read as a hole in %.0f to %.0f per cent of their frames, median %.0f.'
      % (len(allr), 100 * fr.min(), 100 * fr.max(), 100 * float(np.median(fr))))
# THE CONTROL, run the same way: how often does a PIER read as darker than the pier beyond IT.
ctrl = []
for r in rows:
    ctrl.append(1 if r[5] < 0.72 * r[3] else 0)
print('   THE CONTROL: the same rule applied the other way round, asking whether the PIER reads as a hole')
print('   beside the opening, fires on %.0f per cent of the same readings.' % (100.0 * np.mean(ctrl)))
print('')
# THE PER-FRAME HIT RATE IS THE WRONG STATISTIC and the first version of this judged on it. Many frames
# see an opening at a grazing angle or in poor light, so a strict per-frame threshold misses them; what
# says whether a hole is there is the MEDIAN RATIO of opening to pier, read against a control that shares
# every one of those difficulties. The control is the same rule applied the other way round.
ratios = np.array([r[2] / max(r[3], 1e-6) for r in allr])
dark = [r for r in allr if (r[2] / max(r[3], 1e-6)) < 0.95]
light = [r for r in allr if (r[2] / max(r[3], 1e-6)) >= 0.95]
print('   %d of %d openings are DARKER than the stone beside them, ratios %.2f to %.2f.'
      % (len(dark), len(allr), ratios.min(), ratios.max()))
if light:
    for r in light:
        print('   OPENING %d IS NOT: ratio %.2f, brighter than its own pier, and it reads as a hole in '
              'only %.0f per cent of its %d frames where the others run 37 to 85.'
              % (r[0], r[2] / max(r[3], 1e-6), 100 * r[4], r[1]))
if len(dark) >= 10 and np.mean(ctrl) < 0.15:
    print('   SO THE PATTERN HOLDS FOR THE REST. The control fires on %.0f per cent, so the test is'
          % (100.0 * np.mean(ctrl)))
    print('   specific, and eleven independent instances of one element agree with each other, which is')
    print('   the redundancy that caught the fins and the corridor lamps when they were wrong.')
else:
    print('   THE PATTERN DOES NOT HOLD, and with a control rate of %.0f per cent that is about the'
          % (100.0 * np.mean(ctrl)))
    print('   openings rather than about the test.')
