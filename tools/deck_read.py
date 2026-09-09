# 2026-09-09: THE EAST PARAPET READ OFF THE BALCONY WALK, both unknowns at once.
#
# tools/deck_cloud.py triangulated 164,198 points from the clips that stand ON the east top gallery, and
# 144,419 of them came from b3 alone, which is the clip where Lloyd walks along that gallery: 25 accepted
# frames and 140 with the pan poses, from d 3.98 to d 7.50. That walk is the thing every earlier attempt on
# this edge lacked. The silhouette fit refused because all its cameras sat within 0.68 m of one u, so a face
# nearer the lens and a top higher up traded off along the sightline and could not be separated.
#
# A CLOUD DOES NOT HAVE THAT PROBLEM. Each point is triangulated from two rays a metre or more apart along
# the walk, so it lands at its own u, d and h with no line to slide along. The parapet in front of the
# operator is 1.0 to 1.5 m away, which is the range at which this instrument gave the south wall a 0.03 m
# sheet. What comes back is not a fitted line but a solid: a coping with a top surface, an inner face the
# operator is leaning over, and a deck behind it.
#
# NOTHING DRAWN IS SEARCHED FOR. The window is the whole near field, 46.0 to 50.5 in u and 7.6 to 11.0 in h,
# which is 2 m either side of the drawn face and 1.5 m either side of the drawn top. The peaks are wherever
# the points are; the drawn stations are printed beside them.
#   python tools/deck_read.py [cloud.npy]
import os
import sys

import numpy as np

CLOUD = sys.argv[1] if len(sys.argv) > 1 else \
    'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/walls/cloud-deck-east.npy'
UFACE, UBACK, DECK, TOP, SOFFIT = 48.056, 51.906, 8.34, 9.11, 11.1
DWALK = (3.6, 7.9)                 # the d band b3 walked, plus 0.3 m either side
A = np.load(CLOUD)
print('%d points in %s' % (len(A), os.path.basename(CLOUD)))

W = A[np.logical_and.reduce((A[:, 0] > 46.0, A[:, 0] < 50.5,
                             A[:, 1] > DWALK[0], A[:, 1] < DWALK[1],
                             A[:, 2] > 7.6, A[:, 2] < 11.0))]
print('%d of them in the near field beside the walk: u 46.0-50.5, d %.1f-%.1f, h 7.6-11.0'
      % (len(W), DWALK[0], DWALK[1]))
if len(W) < 200:
    raise SystemExit('not enough near-field points beside the walk to read a surface')


def sheets(vals, lo, hi, step, label, drawn, n=6):
    edges = np.arange(lo, hi + 1e-9, step)
    h, _ = np.histogram(vals, bins=edges)
    sm = np.convolve(h, np.ones(3), 'same')
    picked = []
    for k in np.argsort(sm)[::-1]:
        c = float(0.5 * (edges[k] + edges[k + 1]))
        if any(abs(c - p[0]) < 0.12 for p in picked):
            continue
        picked.append((c, int(h[max(0, k - 1):k + 2].sum())))
        if len(picked) >= n:
            break
    print('')
    print('   %s' % label)
    for c, cnt in picked:
        near = min(drawn, key=lambda dv: abs(dv - c))
        print('      %8.3f  %5d points   nearest drawn %8.3f   %+.3f' % (c, cnt, near, c - near))
    return picked


sheets(W[:, 0], 46.0, 50.5, 0.02, 'ACROSS: where the stone stands in u', [UFACE, UFACE + 0.5, UBACK])
sheets(W[:, 2], 7.6, 11.0, 0.02, 'UP: the levels beside the walk', [DECK, TOP, SOFFIT])

# THE COPING AS A SOLID, which is what separates the two unknowns. A camera on the deck looking down the
# hall sees the TOP of the parapet as a near-horizontal band and its inner face as a near-vertical one. So:
# take the highest level that carries a real sheet of points, then ask where in u that sheet begins and ends.
# Its top is the parapet top and its west edge is the face. Neither is inferred from the other.
lo, hi = 8.6, 10.4
edges = np.arange(lo, hi + 1e-9, 0.02)
cnt, _ = np.histogram(W[:, 2], bins=edges)
floor_n = max(12, int(0.004 * len(W)))
tops = [k for k in range(len(cnt)) if cnt[k] >= floor_n]
print('')
print('   a level counts as a sheet at %d points per 20 mm; %d of the 90 levels qualify' % (floor_n, len(tops)))
if tops:
    k = max(tops)
    hband = (float(edges[k] - 0.06), float(edges[k + 1] + 0.02))
    band = W[np.logical_and(W[:, 2] > hband[0], W[:, 2] < hband[1])]
    print('   the highest one runs h %.3f to %.3f and holds %d points' % (hband[0], hband[1], len(band)))
    us = np.sort(band[:, 0])
    print('   in u that sheet spans %.3f to %.3f, 5th to 95th percentile %.3f to %.3f'
          % (us[0], us[-1], float(np.percentile(us, 5)), float(np.percentile(us, 95))))
    print('   drawn: top %.3f, face %.3f. so the top reads %+.3f and its west edge %+.3f'
          % (TOP, UFACE, 0.5 * (hband[0] + hband[1]) - TOP, float(np.percentile(us, 5)) - UFACE))

# AND THE DECK BEHIND IT, the one level a camera standing on it can only see by looking down and back. If
# the walk caught any of it the level is its own check on the pair above, because a deck and a parapet top
# measured from the same cloud cannot both be wrong in the same direction and still be 0.77 m apart.
B = A[np.logical_and.reduce((A[:, 0] > UFACE + 0.2, A[:, 0] < UBACK,
                             A[:, 1] > DWALK[0], A[:, 1] < DWALK[1],
                             A[:, 2] > 7.4, A[:, 2] < 12.6))]
print('')
print('   %d points behind the drawn face (u %.2f to %.2f) beside the walk' % (len(B), UFACE + 0.2, UBACK))
if len(B) >= 60:
    sheets(B[:, 2], 7.4, 12.6, 0.02, 'UP, behind the face: the gallery levels', [DECK, TOP, SOFFIT], n=5)
else:
    print('   too few to read a level behind the face; the walk did not look back at the deck')
