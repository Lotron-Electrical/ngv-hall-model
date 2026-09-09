# 2026-09-09: the lower tier refused to say WHERE it is, so ask it the question it can answer.
#
# The lower gallery was fitted for the first time this evening (tools/run_low_band.py) and the east end
# returned two strong-looking lines: the solid upstand top on 341 rays with a 56 mm residual, the rail top
# on 91 with 28 mm, found by OPPOSITE polarities so neither detector could have found the other's edge.
# The west end refused both outright, 5 detections and none, so there is nothing to cross-check against.
#
# AND BOTH EAST FITS FAIL THE NEAR-FAR TEST. The near-far gap falls monotonically across the whole sweep
# with its minimum sitting on the edge, which is the two halves converging as the plane nears the cameras
# and not the feature being found, and the worst-to-best ratio is 1.7 and 1.6 where the top tier gave 12
# to 70. Neither line's STATION is measured, so neither line's HEIGHT is a number, only a locus.
#
# SO STOP ASKING FOR THE HEIGHTS AND ASK FOR THE GAP BETWEEN THEM. Both loci have almost the same slope,
# 0.186 and 0.204 m of height per metre of station, because they are the same geometry seen from the same
# cameras. Their DIFFERENCE therefore barely moves as the station is swept: a drift common to both cancels
# out of it, exactly as the common jamb drift cancelled out of the openings' agreement an hour ago. If the
# difference holds steady across the whole plausible station range, then how far the lower rail stands
# above the lower solid IS measured, even though neither of them individually is.
#
# THAT IS WORTH HAVING, because the model draws the two 0.37 m apart on the strength of one 2009
# photograph of bar stools behind glass, and nothing has ever checked it.
import os

import numpy as np

POSEDIR = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
FLOOR = 6.33
DRAWN_UP, DRAWN_RAIL = 0.52, 0.89
SEED = {'solid': (48.417, 6.781), 'rail': (47.672, 6.937)}
SRC = {'solid': 'east-low-far-rays.npy', 'rail': 'east-lowrail-far-rays.npy'}
US = np.arange(47.40, 49.001, 0.050)
WIN, TOL = 0.150, 0.05


def solve_h(R, uf):
    vu = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (uf - R[:, 0]) / vu


def consensus(R, uf, centre):
    h = solve_h(R, uf)
    h = h[np.abs(h - centre) < WIN]
    if len(h) < 25:
        return None
    grid = np.arange(centre - WIN, centre + WIN, 0.002)
    counts = np.array([int(np.sum(np.abs(h - g) < TOL)) for g in grid])
    g = float(grid[int(np.argmax(counts))])
    return float(np.median(h[np.abs(h - g) < TOL]))


tracks = {}
for key in ('solid', 'rail'):
    R = np.load(os.path.join(POSEDIR, SRC[key]))[:, :4]
    u0, h0 = SEED[key]
    out = {}
    # walk out from the free fit in both directions, recentring, so one edge is followed throughout
    for direction in (1.0, -1.0):
        centre = h0
        u = u0
        while 47.30 <= u <= 49.10:
            hv = consensus(R, u, centre)
            if hv is None:
                break
            out[round(u, 3)] = hv
            centre = hv
            u += direction * 0.050
    tracks[key] = out
    print('%-6s %d rays, tracked over %d stations from %.3f to %.3f'
          % (key, len(R), len(out), min(out), max(out)))

print('')
print('   station   solid top   rail top   the gap between them')
gaps = []
for u in US:
    k = round(float(u), 3)
    ks = min(tracks['solid'], key=lambda x: abs(x - k))
    kr = min(tracks['rail'], key=lambda x: abs(x - k))
    if abs(ks - k) > 0.03 or abs(kr - k) > 0.03:
        continue
    g = tracks['rail'][kr] - tracks['solid'][ks]
    gaps.append((k, tracks['solid'][ks], tracks['rail'][kr], g))
    print('   %7.3f    %8.3f   %8.3f   %8.3f m' % (k, tracks['solid'][ks], tracks['rail'][kr], g))

if not gaps:
    raise SystemExit('the two tracks do not overlap, so no gap can be formed')
g = np.array([r[3] for r in gaps])
print('')
print('   across %.2f m of assumed station the two individual heights move %.3f and %.3f m,'
      % (gaps[-1][0] - gaps[0][0], np.ptp([r[1] for r in gaps]), np.ptp([r[2] for r in gaps])))
print('   but the GAP between them moves only %.3f m, from %.3f to %.3f.'
      % (float(np.ptp(g)), g.min(), g.max()))
print('   MEASURED GAP %.3f m, against a drawn %.3f.' % (float(np.mean(g)), DRAWN_RAIL - DRAWN_UP))
if float(np.ptp(g)) < 0.05:
    print('')
    print('   THIS ONE IS A MEASUREMENT AND THE TWO HEIGHTS ARE NOT. The common drift cancels: whatever')
    print('   station the lower tier really stands on, its rail stands %.3f m above its solid, and the'
          % float(np.mean(g)))
    print('   model draws %.3f. Two detectors of opposite polarity found the two edges, so this is not'
          % (DRAWN_RAIL - DRAWN_UP))
    print('   one detector reporting its own window twice.')
    print('   Drawn from the same floor that is drawn now, the rail goes %.3f to %.3f.'
          % (DRAWN_RAIL, DRAWN_UP + float(np.mean(g))))
else:
    print('')
    print('   THE GAP MOVES TOO, so the common drift does not cancel and there is nothing here to keep.')
