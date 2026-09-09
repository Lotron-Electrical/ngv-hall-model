# 2026-09-09: the opening head lean, 40 to 205 mm, has sat on the unmeasured list all day. Ask it again.
#
# It was put there when the wall's depth was an assumption. That changed this evening: the near-far split
# with its own null finds a real minimum and puts the face on d -0.030, with the sill and the head landing
# on the SAME plane from separate ladders of opposite polarity (tools/depth_v.py). That matters here more
# than it looks, because the height a ray reports depends on the depth it is solved on by about 0.69 m per
# metre. Sixty millimetres of depth error is forty of height, which is the bottom of the lean's own range.
# So the lean may never have been a lean at all.
#
# TWELVE OPENINGS, EACH ASKED ON ITS OWN. Every head detection carries the station it came from, so the
# rays can be split by opening and each one solved separately on the measured depth. Twelve heights, one
# spread, and the near-far test run inside each opening to say which of the twelve are measured at all.
#
# AND THE SILL IS THE CONTROL, WHICH IS WHAT MAKES THIS DECIDABLE. The sill and the head are two edges of
# the same twelve openings seen by the same cameras in the same frames. Anything that tilts the whole
# instrument, a systematic pose lean, a drift in the hall frame, an error in the wall plane, moves BOTH by
# the same amount in the same direction. A real difference in how high the heads are built shows up in the
# head and NOT in the sill. Their DIFFERENCE, the opening height, cancels everything common and keeps only
# what is genuinely different between the openings, and neither edge alone can separate those.
#   nothing here needs new imagery: it is entirely a better question put to rays already on disk
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH = -0.030
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.917, 20.130],
        [22.565, 23.778], [26.213, 27.426], [29.963, 31.175], [33.642, 34.853], [37.177, 38.383],
        [40.906, 42.118], [44.526, 45.739]]
INSET = 0.15              # stay clear of the jamb corners, where the head detector meets the jamb
DRAWN = {'head': 11.165, 'sill': 8.740}
TOL = 0.05


def solve_h(rays, dfix):
    vd = np.where(np.abs(rays[:, 2]) < 1e-9, 1e-9, rays[:, 2])
    return rays[:, 1] + rays[:, 3] * (dfix - rays[:, 0]) / vd


def consensus(rays, dfix, centre, win=0.30):
    vals = solve_h(rays, dfix)
    vals = vals[np.abs(vals - centre) < win]
    if len(vals) < 12:
        return None, 0
    grid = np.arange(centre - win, centre + win, 0.002)
    counts = np.array([int(np.sum(np.abs(vals - g) < TOL)) for g in grid])
    peak = float(grid[int(np.argmax(counts))])
    near = vals[np.abs(vals - peak) < TOL]
    return float(np.median(near)), int(len(near))


per = {}
for edge in ('head', 'sill'):
    A = np.load(os.path.join(WALLS, 'wall-%s-rays.npy' % edge))
    rays, UU = A[:, :4], A[:, 4]
    print('')
    print('%s: %d rays, solved on the MEASURED plane d %+.3f' % (edge.upper(), len(rays), DNORTH))
    print('   opening        u span        rays   height    against drawn   near-far   null')
    rows = []
    for i, (lo, hi) in enumerate(OPEN):
        sel = np.logical_and(UU > lo + INSET, UU < hi - INSET)
        sub = rays[sel]
        if len(sub) < 24:
            print('   %2d        %6.2f to %6.2f  %5d   too few rays to ask' % (i, lo, hi, len(sub)))
            continue
        value, n = consensus(sub, DNORTH, DRAWN[edge])
        if value is None:
            print('   %2d        %6.2f to %6.2f  %5d   no consensus in the window' % (i, lo, hi, len(sub)))
            continue
        dist = np.abs(sub[:, 0] - DNORTH)
        cut = float(np.median(dist))
        vnear = consensus(sub[dist <= cut], DNORTH, value, 0.15)[0]
        vfar = consensus(sub[dist > cut], DNORTH, value, 0.15)[0]
        vodd = consensus(sub[0::2], DNORTH, value, 0.15)[0]
        veven = consensus(sub[1::2], DNORTH, value, 0.15)[0]
        gap = abs(vnear - vfar) if (vnear is not None and vfar is not None) else float('nan')
        null = abs(vodd - veven) if (vodd is not None and veven is not None) else float('nan')
        rows.append((i, float((lo + hi) / 2), value, n, gap, null))
        print('   %2d        %6.2f to %6.2f  %5d  %7.3f      %+6.0f mm    %5.0f mm  %5.0f mm'
              % (i, lo, hi, n, value, 1000 * (value - DRAWN[edge]), 1000 * gap, 1000 * null))
    if not rows:
        continue
    per[edge] = {r[0]: r[2] for r in rows}
    heights = np.array([r[2] for r in rows])
    stations = np.array([r[1] for r in rows])
    print('   %d openings answered. Spread %.0f mm, from %.3f to %.3f.'
          % (len(rows), 1000 * float(np.ptp(heights)), heights.min(), heights.max()))
    slope, icept = np.polyfit(stations, heights, 1)
    resid = heights - (slope * stations + icept)
    print('   a straight line through them tilts %+.1f mm per metre of hall, and they sit off it by up to'
          % (1000 * slope))
    print('   %.0f mm, so %s'
          % (1000 * float(np.abs(resid).max()),
             'the spread is mostly ONE TILT and not twelve independent heights'
             if np.abs(resid).max() < 0.5 * np.ptp(heights) else
             'this is not one tilt: the openings disagree individually'))

common = sorted(set(per.get('head', {})).intersection(set(per.get('sill', {}))))
print('')
# five is the floor, and it is a floor rather than a preference: below that a correlation and a
# spread are both meaningless, and above it the openings that answer are the ones with rays.
if len(common) < 5:
    raise SystemExit('too few openings answer on both edges to run the control')
heads = np.array([per['head'][i] for i in common])
sills = np.array([per['sill'][i] for i in common])
print('THE SILL IS THE CONTROL. %d openings answered on both edges.' % len(common))
print('   opening   head        sill       the opening height between them')
for i, a, b in zip(common, heads, sills):
    print('   %2d       %7.3f     %7.3f     %7.3f m' % (i, a, b, a - b))
corr = float(np.corrcoef(heads, sills)[0, 1])
tall = heads - sills
print('')
print('   head spread %.0f mm, sill spread %.0f mm, and they correlate %+.2f'
      % (1000 * float(np.ptp(heads)), 1000 * float(np.ptp(sills)), corr))
print('   the OPENING HEIGHT, which is the head minus the sill and cancels anything that moves both,')
print('   runs %.3f to %.3f, a spread of %.0f mm about a mean of %.3f'
      % (tall.min(), tall.max(), 1000 * float(np.ptp(tall)), float(np.mean(tall))))
print('')
if float(np.ptp(tall)) < 0.5 * float(np.ptp(heads)):
    print('   THE LEAN IS NOT IN THE OPENINGS. Whatever moves the heads moves the sills with it, and the')
    print('   height between them holds far tighter than either edge does. That is the signature of one')
    print('   instrument leaning, not twelve openings built at different heights, and it means the model')
    print('   should keep drawing every head on one level. What the archive can state is the OPENING')
    print('   HEIGHT, %.3f m, which is invariant to the lean.' % float(np.mean(tall)))
else:
    print('   THE LEAN IS REAL AND IT IS IN THE OPENINGS. The height between head and sill varies as much')
    print('   as the edges do, so it is not one instrument leaning: these openings are genuinely not all')
    print('   the same height and drawing them on one level is wrong.')
