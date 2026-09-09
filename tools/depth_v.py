# 2026-09-09: the corridor's depth was called unmeasurable by the weaker of the two available tests.
#
# tools/corridor_locus.py swept the assumed back wall depth and reported how many rays agreed at each one.
# The count came back flat, 83 to 90 across d -3.6 to -1.2, and that was read as "the depth is not in this
# data". It is worth being precise about what a flat COUNT actually proves, which is less than it looks:
# the count is how many rays fall inside a 50 mm tolerance of the consensus peak, and a wrong plane moves
# every ray's answer in the same direction before it spreads them, so the peak simply follows and keeps
# most of its rays. A count is a blunt instrument for conditioning.
#
# THE END WALLS SUPPLIED A SHARPER ONE THIS EVENING, AND IT HAS NEVER BEEN POINTED AT THIS ROOM. Split the
# rays by how far the camera stood from the plane and solve the two halves separately. A wrong plane costs
# a ray that came in shallow a different amount of height than one that came in steep, so near and far
# cameras agree only where the plane really is and part either side of it. That test found a station on the
# end walls where the free fit had produced a 0.40 m fiction, and it found it with the east end as an
# unasked control that landed on an independently drawn face to one millimetre.
#
# AND IT CARRIES ITS OWN NULL, which is why it is worth trusting. Odd rays against even is the same
# cameras, the same ladder and the same feature, differing in nothing that could know where the plane is.
# Whatever the null does is what the machinery does on its own, and only what the near-far split does over
# and above the null is a fact about the building.
#
# SO ASK BOTH WALLS THE SAME QUESTION. The north wall's own depth was declared unmeasurable by a flat
# inlier count too (tools/face_depth_scan.py), on the same reasoning, so it goes through the same test
# here as a second case. Whatever comes back, it is the first time either wall has been asked properly.
#   TARGET=corridor python tools/depth_v.py     TARGET=head python tools/depth_v.py
import os

import numpy as np

WALLS = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls'
TARGET = os.environ.get('TARGET', 'corridor')
CFG = {
    # file, seed depth, seed height, half-sweep, step, tracking window
    'corridor': ('corridor-ceiling-rays.npy', -2.090, 10.806, 1.20, 0.100, 0.220),
    # seeds pointed at the measured wall, 2026-09-09. They only say where the tracker starts, but a tool
    # that starts from a superseded number is one more place for a stale constant to hide.
    'head': ('wall-head-rays.npy', -0.030, 11.165, 0.24, 0.020, 0.060),
    'sill': ('wall-sill-rays.npy', -0.030, 8.740, 0.24, 0.020, 0.060),
}
SRC, D0, H0, SPAN, STEP, WIN = CFG[TARGET]
TOL = 0.05
LAMPTOP = 10.990          # the highest lamp triangulated inside the corridor, tools/corridor_lamp.py
BAR = 3.0                 # the near-far split has to beat its own null by this much to count


def solve_h(R, dfix):
    vd = np.where(np.abs(R[:, 2]) < 1e-9, 1e-9, R[:, 2])
    return R[:, 1] + R[:, 3] * (dfix - R[:, 0]) / vd


def consensus(R, dfix, centre):
    h = solve_h(R, dfix)
    h = h[np.abs(h - centre) < WIN]
    if len(h) < 25:
        return None, 0
    grid = np.arange(centre - WIN, centre + WIN, 0.002)
    counts = np.array([int(np.sum(np.abs(h - g) < TOL)) for g in grid])
    g = float(grid[int(np.argmax(counts))])
    near = h[np.abs(h - g) < TOL]
    return float(np.median(near)), int(len(near))


def track(R):
    """walk the depth outward from the seed, recentring on the previous step so one feature is followed"""
    out = {}
    for direction in (1.0, -1.0):
        centre = H0
        for k in range(0, int(round(SPAN / STEP)) + 1):
            dv = D0 + direction * k * STEP
            hv, n = consensus(R, dv, centre)
            if hv is None:
                break
            out[round(dv, 4)] = (hv, n)
            centre = hv
    return out


A = np.load(os.path.join(WALLS, SRC))
R = A[:, :4]
print('%s: %d rays from cameras standing d %.2f to %.2f, the plane seeded on %+.3f'
      % (TARGET.upper(), len(R), R[:, 0].min(), R[:, 0].max(), D0))
dist = np.abs(R[:, 0] - D0)
cut = float(np.median(dist))
NEAR, FAR = R[dist <= cut], R[dist > cut]
print('   near cameras stand %.2f to %.2f m off the plane and far ones %.2f to %.2f, split on %.2f'
      % (dist[dist <= cut].min(), cut, cut, dist.max(), cut))

# THE LEVERAGE IS THE WHOLE TEST, AND IT CAN BE STATED AS A NUMBER BEFORE ANY FITTING HAPPENS. Near and
# far cameras can only disagree about a wrong plane in proportion to how differently they see it, so what
# matters is the RATIO of the two halves' distances, not the split itself. On the end walls that ratio was
# 42 over 5. Anything near 1 means the two halves are the same instrument twice and the test has nothing
# to work with, whatever it then prints.
lever = float(dist.max() / max(dist.min(), 1e-6))
print('   the far half stands %.2f times as distant as the near half, and that ratio IS the leverage'
      % lever)

both, nearT, farT = track(R), track(NEAR), track(FAR)
oddT, evenT = track(R[0::2]), track(R[1::2])
rows = []
for dv in sorted(both):
    if dv not in nearT or dv not in farT or dv not in oddT or dv not in evenT:
        continue
    hv, n = both[dv]
    rows.append((dv, hv, n, nearT[dv][0], farT[dv][0],
                 abs(nearT[dv][0] - farT[dv][0]), abs(oddT[dv][0] - evenT[dv][0])))
if not rows:
    raise SystemExit('nothing tracked, so the question cannot be put this way to these rays')

print('')
print('   plane      height    rays     near     far    near-far   odd-even')
for dv, hv, n, hn, hf, gap, null in rows:
    print('   %+.3f   %8.3f   %5d  %7.3f %7.3f   %5.0f mm   %5.0f mm'
          % (dv, hv, n, hn, hf, 1000 * gap, 1000 * null))

gaps = np.array([r[5] for r in rows])
nulls = np.array([r[6] for r in rows])
best = rows[int(np.argmin(gaps))]
print('')
print('   the two halves agree most closely on the plane %+.3f, %.0f mm apart there, against %.0f mm at'
      % (best[0], 1000 * gaps.min(), 1000 * gaps.max()))
print('   the worst plane on this sweep. The null split runs %.0f to %.0f mm over the same sweep.'
      % (1000 * nulls.min(), 1000 * nulls.max()))
ratio = gaps.max() / max(nulls.max(), 1e-6)
print('   ratio %.1f against a bar of %.1f, on a leverage of %.2f' % (ratio, BAR, lever))
# A MINIMUM AT THE EDGE OF THE SWEEP IS NOT A MINIMUM. If the gap falls all the way to one end it
# is tracking how far the plane is from the cameras rather than where the feature is, because the
# two halves necessarily converge as the plane approaches them. A real V has the plane inside it.
edge = best[0] in (min(r[0] for r in rows), max(r[0] for r in rows))
if edge:
    print('   AND THE MINIMUM SITS ON THE EDGE OF THE SWEEP, so it is not a minimum at all: the gap')
    print('   is still falling where the sweep stops, which is the two halves converging as the')
    print('   plane nears the cameras, and not the feature being found.')
if ratio > BAR and not edge:
    print('')
    print('   THE DEPTH IS MEASURED. Near and far cameras part as the plane moves away from %+.3f by far'
          % best[0])
    print('   more than the null split can account for, so these rays do separate the depth from the')
    print('   height after all and the flat inlier count was the blunt instrument, not the evidence.')
    print('   The feature sits on h %.3f there, from %d rays.' % (best[1], best[2]))
    if TARGET == 'corridor':
        print('   Against the lamps: the highest hangs on %.3f, so this clears it by %+.3f m.'
              % (LAMPTOP, best[1] - LAMPTOP))
else:
    print('')
    print('   THE DEPTH IS STILL NOT MEASURED, and now it has been refused by the sharper test as well as')
    print('   the blunt one. Near and far cameras track each other across the whole sweep no better than')
    print('   odd rays track even, which is what it looks like when every candidate plane lies on one')
    print('   slide and no ray can tell them apart. The locus stands and a single number would be a')
    print('   fiction. This is a stronger refusal than the count was, because it can distinguish a')
    print('   degenerate fit from a merely noisy one and it says degenerate.')
