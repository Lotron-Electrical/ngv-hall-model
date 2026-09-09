# 2026-09-09: are the balcony parapet's two edges on ONE plane, or 0.40 m apart? And is that even askable?
#
# Everything the model draws on an end wall stands on a single plane uF: the apron, the lower upstand, the
# rail, the fascia, the top upstand, the stone over the head. Nothing has ever tested that. Two free line
# fits made today put two edges of the SAME parapet on stations 0.40 m apart, and they do it at both ends:
#   west   rail top u 4.160   solid upstand top u 3.760   0.400 m
#   east   rail top u 48.397  solid upstand top u 48.005  0.392 m
# Eight millimetres of agreement between two ends fitted from opposite directions looks like a shape.
#
# BUT THE SILL TAUGHT THIS AFTERNOON THAT IT NEED NOT BE ONE. Both of those are two-unknown fits in (u, h)
# on a line at constant (u, h) spanning the hall width, and such a fit is separated only by cameras at
# different distances ALONG the hall. If it is degenerate the answer slides along the median ray, and two
# fits that slide the same way keep their difference while both stations are meaningless. A difference
# that survives at both ends is exactly what a shared slide looks like.
#
# SO ASK THE ONE-UNKNOWN QUESTION INSTEAD, AND ASK IT THE WAY THAT CAN COME BACK NEGATIVE. Fix the station,
# and every ray gives its own height, h = ch + vh*(uf - cu)/vu, with nothing to slide along. Then split the
# rays by how far the camera stood from the end and solve both halves separately:
#   IF THE STATION IS MEASURED, near and far cameras agree only where the plane really is, and diverge as
#   the assumed station moves away from it, because a wrong plane converts to a different height error for
#   a ray that came in shallow than for one that came in steep.
#   IF IT IS DEGENERATE, they agree everywhere, because every candidate station lies on the same slide and
#   no ray can tell one from another.
# A V with a minimum is a measurement of the station. A flat line is proof there is nothing there to
# measure, and it would mean the 0.40 m is not a shape at all.
#
# THE WINDOW HAS TO FOLLOW THE FEATURE. Across the sweep the locus carries the height by about as much as
# the station moves, so a window fixed on the drawn height would walk off the edge and start reporting
# whatever else it found. This steps outward from the free fit and recentres on the previous step, which
# tracks one feature and cannot jump to the course above it.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
DECK = 8.34
DRAWNFACE = {'west': 4.194, 'east': 48.056}
# the free two-unknown fits, each feature's own starting point for the tracker
SEED = {('west', 'rail top'): (4.160, 9.799), ('west', 'solid upstand top'): (3.760, 9.082),
        ('east', 'rail top'): (48.397, 9.865), ('east', 'solid upstand top'): (48.005, 9.067),
        # THE LOWER TIER, fitted for the first time this evening (tools/run_low_band.py). The west end
        # refused both polarities outright, 5 detections and none, so only the east is here.
        ('east', 'lower solid top'): (48.417, 6.781), ('east', 'lower rail top'): (47.672, 6.937),
        # THE SAME FEATURE, RE-SAMPLED ON THE PLANE IT IS NOW BELIEVED TO STAND ON (2026-09-09,
        # tools/run_upstand_replane.py). If the station scan is measuring the building it must land
        # in the same place whichever plane the ladder was walked on; if it follows the ladder, the
        # west recess is an artefact of the same family as the corridor aperture.
        ('west', 'solid top replaned'): (3.710, 9.097),
        ('east', 'solid top replaned'): (48.056, 9.095)}
SRC = {'rail top': '%s-walk-front-far-rays.npy', 'solid upstand top': '%s-up-far-rays.npy',
       'lower solid top': '%s-low-far-rays.npy', 'lower rail top': '%s-lowrail-far-rays.npy',
       'solid top replaned': '%s-upR-far-rays.npy'}
# the arrival cap was measured for cameras standing on the 8.34 deck, so it says nothing about a parapet
# two and a half metres below them. Naming that here rather than quietly applying it anyway.
CAPPED = ('solid upstand top',)
SPAN, STEP, WIN, TOL = 0.70, 0.050, 0.150, 0.05
# the 5th percentile height that light from inside the building reached, against the assumed station, both
# ends at the matched 0.6 m setback (tools/gallery_arrival.py). A SOLID parapet cannot stand in it. Glass
# is not a parapet for this purpose, so this cuts the upstand's locus and says nothing about the rail's.
CAP = {'west': ((3.394, 9.544), (3.594, 9.370), (3.794, 9.189), (3.994, 9.002), (4.194, 8.818),
                (4.394, 8.632), (4.594, 8.446), (4.794, 8.261), (4.994, 8.073), (5.194, 7.886)),
       'east': ((47.056, 8.541), (47.256, 8.650), (47.456, 8.762), (47.656, 8.872), (47.856, 8.975),
                (48.056, 9.078), (48.256, 9.183), (48.456, 9.289), (48.656, 9.401), (48.856, 9.502))}


def cap_at(side, uf):
    xs = [p[0] for p in CAP[side]]
    ys = [p[1] for p in CAP[side]]
    return float(np.interp(uf, xs, ys))


def solve_h(R, uf):
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (uf - R[:, 0]) / vu


def consensus(R, uf, centre):
    h = solve_h(R, uf)
    h = h[np.abs(h - centre) < WIN]
    if len(h) < 30:
        return None, 0
    grid = np.arange(centre - WIN, centre + WIN, 0.002)
    counts = np.array([int(np.sum(np.abs(h - g) < TOL)) for g in grid])
    g = float(grid[int(np.argmax(counts))])
    near = h[np.abs(h - g) < TOL]
    return float(np.median(near)), int(len(near))


def track(R, u0, h0):
    """walk the station outward from the free fit, recentring on the last answer at every step"""
    out = {}
    for direction in (1.0, -1.0):
        centre = h0
        for k in range(0, int(SPAN / STEP) + 1):
            uf = u0 + direction * k * STEP
            hv, n = consensus(R, uf, centre)
            if hv is None:
                break
            out[round(uf, 4)] = (hv, n)
            centre = hv
    return out


for end in ('west', 'east'):
    print('')
    print('%s END, the face drawn on u %.3f' % (end.upper(), DRAWNFACE[end]))
    for feat in ('solid upstand top', 'solid top replaned', 'rail top', 'lower solid top',
                 'lower rail top'):
        if (end, feat) not in SEED:
            continue
        src = os.path.join(POSEDIR, SRC[feat] % end)
        if not os.path.exists(src):
            print('   %s: no saved rays' % feat)
            continue
        A = np.load(src)
        R = A[:, :4]
        u0, h0 = SEED[(end, feat)]
        far = np.abs(R[:, 0] - u0)
        cut = float(np.median(far))
        NEAR, FAR = R[far <= cut], R[far > cut]
        print('')
        print('   %s, %d rays, cameras %.1f to %.1f m off, split on %.1f'
              % (feat, len(R), far.min(), far.max(), cut))
        both = track(R, u0, h0)
        nearT = track(NEAR, u0, h0)
        farT = track(FAR, u0, h0)
        # THE NULL CONTROL, because a V is only evidence if a split that carries no geometry does
        # not produce one. Odd and even rays are the same cameras, the same ladder and the same
        # feature, differing in nothing that could know where the plane is. If the null shows the
        # same V, the V is the tracker recentring and not the building.
        oddT = track(R[0::2], u0, h0)
        evenT = track(R[1::2], u0, h0)
        print('      station    height    rays    near    far   near-far   odd-even   arrivals allow')
        rows = []
        for uf in sorted(both):
            if uf not in nearT or uf not in farT:
                continue
            hv, n = both[uf]
            hn, hf = nearT[uf][0], farT[uf][0]
            null = (abs(oddT[uf][0] - evenT[uf][0])
                    if (uf in oddT and uf in evenT) else float('nan'))
            rows.append((uf, hv, n, hn, hf, abs(hn - hf), null))
        if not rows:
            print('      nothing tracked')
            continue
        for uf, hv, n, hn, hf, gap, null in rows[::2]:
            room = cap_at(end, uf) - hv
            note = ('not applicable' if feat not in CAPPED else
                    ('yes' if room >= -0.05 else 'NO, light got over it'))
            print('      %7.3f   %7.3f   %5d  %6.3f  %6.3f  %5.0f mm   %5.0f mm    %s'
                  % (uf, hv, n, hn, hf, 1000 * gap, 1000 * null, note))
        gaps = np.array([r[5] for r in rows])
        best = rows[int(np.argmin(gaps))]
        print('      the two halves agree most closely on u %.3f, %.0f mm apart there against %.0f mm at'
              % (best[0], 1000 * gaps.min(), 1000 * gaps.max()))
        print('      the worst station on this sweep, a ratio of %.1f'
              % (gaps.max() / max(gaps.min(), 1e-6)))
        nulls = np.array([r[6] for r in rows])
        # A DEFECT IN THE FIRST VERSION OF THIS TOOL, FOUND BY POINTING IT AT THE LOWER TIER. Beating the
        # null was treated as the whole verdict, and it is only half of one. The lower tier's gap falls
        # monotonically across the entire sweep with its smallest value on the EDGE, which is the two
        # halves converging as the plane nears the cameras rather than the feature being found, and the
        # old line called that "real geometry" because the null was small. A V has to have the minimum
        # INSIDE it. tools/depth_v.py already carried this check; this one did not, and the four top-tier
        # results shipped on the old wording were re-run against the new one and all four minimise well
        # inside their sweeps, so nothing shipped on it was wrong.
        edge = best[0] in (rows[0][0], rows[-1][0])
        print('      the null split moves %.0f to %.0f mm across the same sweep, so the '
              'near-far V is %s'
              % (1000 * np.nanmin(nulls), 1000 * np.nanmax(nulls),
                 'NOT a V at all: its minimum sits on the edge of the sweep' if edge else
                 'real geometry' if gaps.max() > 3.0 * np.nanmax(nulls)
                 else 'NOT distinguishable from the tracker recentring'))
        slope = float(np.polyfit([r[0] for r in rows], [r[1] for r in rows], 1)[0])
        print('      the locus runs %+.3f m of height per metre of station' % slope)
        if feat in CAPPED:
            ok = [r for r in rows if cap_at(end, r[0]) - r[1] >= -0.05]
            if ok and len(ok) < len(rows):
                print('      THE ARRIVALS CUT IT. A solid top is only possible from u %.3f to %.3f, because'
                      % (min(r[0] for r in ok), max(r[0] for r in ok)))
                print('      outside that the locus stands in light that reached a camera on the deck.')
            elif ok:
                print('      every station on this sweep clears the arrival cap, so it rules nothing out')
            else:
                print('      no station on this sweep clears the arrival cap, which needs explaining')
