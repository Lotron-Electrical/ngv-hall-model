# 2026-09-09: the apron's camera halves disagree by 0.2 m everywhere. Ask whether they agree ANYWHERE.
#
# Last night's station scan swept the west apron boundary from u 3.04 to 4.34 and its near-far gap sat
# between 198 and 233 mm at every single station, never dipping. That was read, correctly, as two halves
# of the camera set looking at different things. But there is a second reading that was not tested and it
# is the more interesting one.
#
# A FEATURE AT THE WRONG STATION DOES EXACTLY THIS. The ladder samples on an assumed plane; a real edge
# standing somewhere else projects to different apparent heights for cameras at different distances, and
# the two halves only agree when the assumed plane reaches the true one. If the true station lies OUTSIDE
# the window that was swept, the gap has no minimum to show and the scan reports a flat curve. A flat
# curve inside a narrow window and a flat curve everywhere are different findings, and only one of them
# was actually established.
#
# SO WIDEN THE WINDOW UNTIL IT IS A REAL ANSWER. The west solid upstand turned out to stand 0.484 m behind
# its own face this evening, so a lower tier standing somewhere else entirely is not an exotic idea in
# this building; it is the same discovery one storey down. This sweeps four metres of station instead of
# one and a third, and if the halves converge anywhere in it, that is where the lower tier stands.
#
# AND IF THEY NEVER CONVERGE, that closes the question properly rather than by window size: it would mean
# no single vertical plane explains both halves, which is what genuinely different features look like.
#
# TWO FAULTS IN THE FIRST TWO RUNS OF THIS TOOL, BOTH FOUND BY READING ITS OWN TABLE, and both are the
# reason it now looks the way it does.
#
# ONE, THE NULL HAS TO GATE THE ROWS. At a third of the stations the odd-against-even null itself ran 150
# to 240 mm, which means the tracker is not holding one feature there at all and its near-far number is
# noise about noise. Reading a minimum off those stations would be reading the machinery, so only stations
# whose null stays under 50 mm are read.
#
# TWO, AND WORSE, A FIXED WINDOW ENDS THE SWEEP EARLY AND THEN THE TOOL BLAMES THE GEOMETRY. The first
# version solved every station against a window centred on the DRAWN floor 6.33 and needed 12 rays inside
# it. Far from the truth the solved heights walk out of that window, the station returns nothing, and the
# scan silently stops. It was asked for four metres, it reported 3.8, and its minimum sat on the first
# station that happened to survive. That is not a boundary of the building, it is a boundary of the
# window, and reporting it as either "they converge here" or "they never converge" would have been the
# same mistake twice: the sweep never actually got wide.
#
# SO THE SWEEP RECENTRES AS IT WALKS, the way tools/low_gap.py tracks the lower tier: start at the drawn
# face, step outward, and carry each station's own answer as the next station's window centre, so one edge
# is followed the whole way and the window can never terminate the experiment. The halves and the null are
# then read at the SAME recentred height, not each on a window of their own, because two halves allowed to
# recentre independently can walk onto different edges and manufacture exactly the divergence this tool
# exists to test for.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
SRC = 'west-apron-far-rays.npy'
FACE, DRAWN_FLOOR = 4.194, 6.33
ULO, UHI, STEP = 1.40, 5.60, 0.100
WIN, TOL = 0.40, 0.05
NULLBAR = 0.05


def solve_h(R, uf):
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (uf - R[:, 0]) / vu


def consensus(R, uf, centre, need=12):
    h = solve_h(R, uf)
    h = h[np.abs(h - centre) < WIN]
    if len(h) < need:
        return None
    grid = np.arange(centre - WIN, centre + WIN, 0.002)
    counts = np.array([int(np.sum(np.abs(h - g) < TOL)) for g in grid])
    peak = float(grid[int(np.argmax(counts))])
    return float(np.median(h[np.abs(h - peak) < TOL]))


def track(R, u0, h0):
    """walk outward from the seed recentring each step, so the window cannot end the sweep"""
    out = {}
    for direction in (1.0, -1.0):
        centre, u = h0, u0
        while ULO - 1e-9 <= u <= UHI + 1e-9:
            hv = consensus(R, u, centre)
            if hv is None:
                break
            out[round(u, 3)] = hv
            centre = hv
            u += direction * STEP
    return out


A = np.load(os.path.join(POSEDIR, SRC))
R = A[:, :4]
dist = np.abs(R[:, 0] - FACE)
cut = float(np.median(dist))
NEAR, FAR = R[dist <= cut], R[dist > cut]
print('%d rays, cameras %.1f to %.1f m from the drawn face, split on %.1f, leverage %.2f'
      % (len(R), dist.min(), dist.max(), cut, dist.max() / max(dist.min(), 1e-6)))
print('   near half %d rays, far half %d' % (len(NEAR), len(FAR)))

allt = track(R, FACE, DRAWN_FLOOR)
print('')
print('   the recentring track holds one edge over %d stations, u %.3f to %.3f, of the %.1f m asked for'
      % (len(allt), min(allt), max(allt), UHI - ULO))
print('')
print('   station    all      near      far     they differ by    odd-even')
rows = []
for u in sorted(allt):
    c = allt[u]
    n = consensus(NEAR, u, c)
    f = consensus(FAR, u, c)
    o = consensus(R[0::2], u, c)
    e = consensus(R[1::2], u, c)
    if n is None or f is None:
        continue
    null = abs(o - e) if (o is not None and e is not None) else float('nan')
    rows.append((u, c, n, f, abs(n - f), null))
    print('   %7.3f  %7.3f  %7.3f  %7.3f     %6.0f mm      %5.0f mm'
          % (u, c, n, f, 1000 * abs(n - f), 1000 * null))

if not rows:
    raise SystemExit('nothing tracked anywhere in four metres of station')
stable = [r for r in rows if r[5] < NULLBAR]
print('')
print('   %d of the %d tracked stations keep their null under %.0f mm; the rest have the two arbitrary'
      % (len(stable), len(rows), 1000 * NULLBAR))
print('   halves of the same camera set disagreeing as much as the near-far halves do, so their near-far')
print('   number carries no information and they are not read.')
rows = stable if len(stable) >= 8 else rows
gaps = np.array([r[4] for r in rows])
best = rows[int(np.argmin(gaps))]
edge = best[0] in (rows[0][0], rows[-1][0])
reached = (min(allt) <= ULO + STEP) and (max(allt) >= UHI - STEP)
print('')
print('   the halves come closest on u %.3f, %.0f mm apart, against %.0f mm at the worst station'
      % (best[0], 1000 * gaps.min(), 1000 * gaps.max()))
print('   over the tracked range the gap runs %.0f to %.0f mm, a ratio of %.1f'
      % (1000 * gaps.min(), 1000 * gaps.max(), gaps.max() / max(gaps.min(), 1e-6)))
dip = gaps.max() > 3.0 * max(gaps.min(), 1e-6)
print('')
if dip and not edge:
    print('   THE HALVES DO CONVERGE, and outside the window that was swept last night. The lower tier')
    print('   boundary stands on u %.3f, which is %+.3f m from the face this model draws it on, and the'
          % (best[0], best[0] - FACE))
    print('   height there is %.3f against a drawn floor of %.3f.' % (best[1], DRAWN_FLOOR))
    print('   Last night said two halves were looking at different things. They were looking at the same')
    print('   thing in the wrong place.')
elif not dip:
    print('   THEY NEVER CONVERGE. Over %.1f m of station the gap never comes down: its best and worst'
          % (max(allt) - min(allt)))
    print('   differ by a factor of %.1f, where a real plane gave 12 to 70 on the tier above. No single'
          % (gaps.max() / max(gaps.min(), 1e-6)))
    print('   vertical plane explains both halves, so last night stands and these are genuinely different')
    print('   features. The question is closed on evidence rather than on window size.')
else:
    print('   THE GAP DOES COME DOWN, BY A FACTOR OF %.1f, BUT ITS MINIMUM IS STILL ON THE EDGE of the'
          % (gaps.max() / max(gaps.min(), 1e-6)))
    print('   tracked range, at u %.3f. That is the one shape this test cannot read: two halves closing'
          % best[0])
    print('   monotonically toward a boundary look identical whether a plane sits just past it or the')
    print('   halves are simply converging as the assumed plane nears the cameras, which is the failure')
    print('   the lower tier already showed tonight.')
    if reached:
        print('   The track DID cover the whole %.1f m asked for, so this is no longer the window: the'
              % (UHI - ULO))
        print('   trend runs off the end of four metres of station and widening further only walks the')
        print('   assumed plane into the camera positions themselves.')
    else:
        print('   And the track stopped at u %.3f before the %.3f asked for, so the boundary is still'
              % (min(allt) if best[0] == rows[0][0] else max(allt), ULO if best[0] == rows[0][0] else UHI))
        print('   partly the instrument. What is established is a bound, not a station.')
    print('   WHAT IS KEPT is the bound: no vertical plane between u %.3f and %.3f reconciles the two'
          % (min(allt), max(allt)))
    print('   halves to better than %.0f mm, and the drawn face %.3f is %.0f mm away from reconciling'
          % (1000 * gaps.min(), FACE, 1000 * dict((r[0], r[4]) for r in rows).get(
              min(rows, key=lambda r: abs(r[0] - FACE))[0], float('nan'))))
    print('   them. The apron boundary is not measured and is not claimed.')
