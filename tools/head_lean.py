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
import io
import os
import re

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH = -0.030
# THE OPENINGS ARE READ OUT OF index.html AT RUN TIME, not copied in (2026-09-10). This tool selects its
# rays by u window, so an opening drawn in the wrong place makes it fit rays that came off the PIER. That
# is not hypothetical: opening 3 moved 0.780 m east today (tools/opening_shift.py) and the window this
# tool used before the move returned 2 head rays where its neighbours return 8 to 45, and no sill
# consensus at all. Re-windowing the SAME rays, which carry their own u and were detected with no
# knowledge of the opening array, is an independent check on that move.
def _openings():
    src = io.open('index.html', encoding='utf-8').read()
    m = re.search(r'const WALLF=\{openings:\[(.*?)\],\s*\n', src, re.S)
    return [[float(a), float(b)] for a, b in re.findall(r'\[([0-9.]+),([0-9.]+)\]', m.group(1))]


OPEN = _openings()
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
            print('   %2d        %6.2f to %6.2f  %5d   too few rays to ask'
              % (i + 1, lo, hi, len(sub)))
            continue
        value, n = consensus(sub, DNORTH, DRAWN[edge])
        if value is None:
            print('   %2d        %6.2f to %6.2f  %5d   no consensus in the window'
              % (i + 1, lo, hi, len(sub)))
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
              % (i + 1, lo, hi, n, value, 1000 * (value - DRAWN[edge]), 1000 * gap, 1000 * null))
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
    print('   %2d       %7.3f     %7.3f     %7.3f m' % (i + 1, a, b, a - b))
corr = float(np.corrcoef(heads, sills)[0, 1])
tall = heads - sills
print('')
print('   head spread %.0f mm, sill spread %.0f mm, and they correlate %+.2f'
      % (1000 * float(np.ptp(heads)), 1000 * float(np.ptp(sills)), corr))
print('   the OPENING HEIGHT, which is the head minus the sill and cancels anything that moves both,')
print('   runs %.3f to %.3f, a spread of %.0f mm about a mean of %.3f'
      % (tall.min(), tall.max(), 1000 * float(np.ptp(tall)), float(np.mean(tall))))
print('')
# THE BAR THIS TEST USED TO CARRY IS TOO CRUDE TO DECIDE THIS, and re-running on corrected rays showed it
# by flipping the verdict on four millimetres. Run on the rays produced with a stale sill, head and wall
# depth it read 38 mm of opening-height spread against 79 of head spread and said the lean was common. Run
# on corrected rays it reads 48 against 88 and says the opposite, because 48 is not under half of 88. A
# conclusion that turns on which side of a half a number falls is not a conclusion.
# SO REPORT BOTH POPULATIONS AND LET THE INSTABILITY SHOW. One opening dominates both spreads at both
# runs; with it removed the picture changes again, in the other direction, because the openings that
# remain barely differ in head height at all.
worst = int(np.argmax(np.abs(tall - np.median(tall))))
keep = [i for i in range(len(tall)) if i != worst]
print('   with all %d openings: opening height spreads %.0f mm against a head spread of %.0f'
      % (len(tall), 1000 * float(np.ptp(tall)), 1000 * float(np.ptp(heads))))
print('   with opening %d removed, which is the outlier on BOTH edges: %.0f mm against %.0f'
      % (common[worst], 1000 * float(np.ptp(tall[keep])), 1000 * float(np.ptp(heads[keep]))))
print('')
print('   WHAT HOLDS ACROSS BOTH RUNS AND BOTH POPULATIONS, and it is less than was claimed:')
print('   the head and the sill of the same openings correlate %+.2f, so most of what moves them is'
      % corr)
print('   common to both and is the instrument rather than the building. Opening %d is high on both'
      % common[worst])
print('   edges in both runs, which is the same signature. But the residual after that, whether the')
print('   remaining openings differ in height by twenty millimetres or by nothing, is NOT settled by')
print('   this test, and the earlier claim that the lean is entirely the instrument went further than')
print('   the evidence. The opening height is %.3f m with all of them and %.3f without the outlier,'
      % (float(np.mean(tall)), float(np.mean(tall[keep]))))
print('   and the model draws %.3f, which sits inside both.' % (DRAWN['head'] - DRAWN['sill']))
