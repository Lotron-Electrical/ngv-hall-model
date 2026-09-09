# 2026-09-10: DOES THE SILL ONLY ANSWER WHERE THE MOVE PUT OPENING 3, OR WOULD IT ANSWER ANYWHERE.
#
# tools/opening_shift.py moved opening 3 of the north wall 0.780 m east today, on the drawn spacing and on
# a darkest-window search of the photographs. tools/head_lean.py then gave that move an independent look:
# it selects its rays by u window, and re-windowed onto the new position the SAME rays, detected long ago
# with no knowledge of the opening array, go from 2 head rays to 11, and the sill goes from no consensus
# at all to a consensus on h 8.770 with a near-far split of 0 mm on a null of 12.
#
# THAT IS EXACTLY THE KIND OF RESULT THIS FILE HAS BEEN WRONG ABOUT ALL DAY. A window slid until it finds
# something will find something, and the finder has already been caught agreeing with the model 45 per
# cent of the time by chance (tools/follow_test.py). So the question is not whether a consensus appears
# where the move put it; it is whether a consensus appears ONLY there.
#
# SO THE WINDOW IS SWEPT. The same opening-wide window is slid along the wall in 50 mm steps across the
# whole bay, from well inside the pier west of opening 3 to well inside the pier east of it, and every
# stop is asked the same question with the same code. A sweep that answers everywhere says the move gains
# nothing here. A sweep that answers over a narrow run, with that run containing the moved position and
# not the drawn one, is a second instrument agreeing.
#
# THE INTERNAL CONTROL COMES FREE: opening 5 has 31 sill rays and returns no consensus in head_lean, so
# the test demonstrably can fail on a window with plenty of rays in it. It is not a rubber stamp.
#   python tools/open3_window.py
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
DNORTH = -0.030
INSET = 0.15
TOL = 0.05
WIDTH = 1.213                    # the drawn opening width, held fixed while the window slides
DRAWN_C, MOVED_C = 11.3135, 12.0935
LO, HI, STEP = 9.80, 13.85, 0.05


def solve_h(rays, dfix):
    vd = np.where(np.abs(rays[:, 2]) < 1e-9, 1e-9, rays[:, 2])
    return rays[:, 1] + rays[:, 3] * (dfix - rays[:, 0]) / vd


def consensus(rays, dfix, centre, win=0.30):
    """head_lean's own consensus, copied unchanged so the sweep asks the identical question"""
    vals = solve_h(rays, dfix)
    vals = vals[np.abs(vals - centre) < win]
    if len(vals) < 12:
        return None, 0
    grid = np.arange(centre - win, centre + win, 0.002)
    counts = np.array([int(np.sum(np.abs(vals - g) < TOL)) for g in grid])
    peak = float(grid[int(np.argmax(counts))])
    near = vals[np.abs(vals - peak) < TOL]
    return float(np.median(near)), int(len(near))


A = np.load(os.path.join(WALLS, 'wall-sill-rays.npy'))
rays, UU = A[:, :4], A[:, 4]
print('THE SILL WINDOW SWEPT ACROSS THE BAY THAT HOLDS OPENING 3')
print('   %d sill rays on the wall. The window is %.3f m wide, the drawn opening width, and every stop'
      % (len(rays), WIDTH))
print('   is asked the same question head_lean asks, with the same code.')
print('')
print('   window centre    u span         rays   sill      near-far   null   answers')
hits = []
stops = 0
for cc in np.arange(LO, HI + 1e-9, STEP):
    stops += 1
    lo, hi = cc - WIDTH / 2, cc + WIDTH / 2
    sel = np.logical_and(UU > lo + INSET, UU < hi - INSET)
    sub = rays[sel]
    if len(sub) < 24:
        print('   %7.3f      %6.2f to %6.2f  %5d   too few rays' % (cc, lo, hi, len(sub)))
        continue
    value, n = consensus(sub, DNORTH, 8.740)
    if value is None:
        print('   %7.3f      %6.2f to %6.2f  %5d   no consensus' % (cc, lo, hi, len(sub)))
        continue
    dist = np.abs(sub[:, 0] - DNORTH)
    cut = float(np.median(dist))
    vn = consensus(sub[dist <= cut], DNORTH, value, 0.15)[0]
    vf = consensus(sub[dist > cut], DNORTH, value, 0.15)[0]
    vo = consensus(sub[0::2], DNORTH, value, 0.15)[0]
    ve = consensus(sub[1::2], DNORTH, value, 0.15)[0]
    gap = abs(vn - vf) if (vn is not None and vf is not None) else float('nan')
    null = abs(vo - ve) if (vo is not None and ve is not None) else float('nan')
    good = (gap == gap) and (null == null) and gap < 0.05
    hits.append((cc, value, n, gap, null, good))
    print('   %7.3f      %6.2f to %6.2f  %5d  %6.3f    %5.0f mm %5.0f mm   %s'
          % (cc, lo, hi, n, value, 1000 * gap, 1000 * null, 'yes' if good else 'weak'))
print('')
firm = [h for h in hits if h[5]]
print('   %d window stops across the bay, %d produced any consensus, %d produced one that also survives'
      % (stops, len(hits), len(firm)))
print('   its own near-far split.')
if not firm:
    print('   NOTHING SURVIVES ANYWHERE, so head_lean gains the move no support and takes none away.')
    raise SystemExit(0)
cs = np.array([h[0] for h in firm])
near_moved = float(min(abs(cs - MOVED_C)))
near_drawn = float(min(abs(cs - DRAWN_C)))
print('   the firm stops run from u %.3f to %.3f, and they are %.0f per cent of the bay'
      % (cs.min(), cs.max(), 100.0 * len(firm) / stops))
print('   the drawn position was centred %.3f and the move put it on %.3f' % (DRAWN_C, MOVED_C))
print('   nearest firm stop to the MOVED centre: %.3f m away' % near_moved)
print('   nearest firm stop to the DRAWN centre: %.3f m away' % near_drawn)
# AND THE NEAREST STOP IS THE FLATTERING NUMBER, so the run says its own resolution too. The firm stops
# form a contiguous stretch, and this instrument cannot place the opening better than the width of that
# stretch however close one stop happens to land.
run_c = 0.5 * (float(cs.min()) + float(cs.max()))
run_w = float(cs.max() - cs.min())
print('   THE FIRM RUN IS %.3f m WIDE, so this localises the opening to about %.2f m and no better.'
      % (run_w, run_w / 2))
print('   its centre is u %.3f: the moved position sits %.3f m from that centre, the drawn one %.3f m.'
      % (run_c, abs(MOVED_C - run_c), abs(DRAWN_C - run_c)))
if len(firm) > 0.6 * stops:
    print('   THE SWEEP ANSWERS ALMOST EVERYWHERE, so a consensus where the move put it means nothing.')
    print('   head_lean is not a second instrument on this move and must not be reported as one.')
elif near_moved <= 0.10 and near_drawn > 0.30:
    print('   IT ANSWERS WHERE THE MOVE PUT IT AND NOT WHERE IT WAS DRAWN. Only %d of %d stops answer'
          % (len(firm), stops))
    print('   firmly, so the test is selective rather than automatic, and these rays were detected with')
    print('   no knowledge of where any opening was drawn. That is a second and independent instrument')
    print('   agreeing with the move.')
elif near_moved <= 0.10:
    print('   IT ANSWERS AT BOTH POSITIONS, so it cannot separate them and gives the move no support.')
else:
    print('   IT DOES NOT ANSWER WHERE THE MOVE PUT IT. Whatever these rays support, it is not this move,')
    print('   and that has to be reported as loudly as agreement would have been.')
