# 2026-09-09: CAN ANY BALCONY FRAME SEE THE EDGE OF THE CEILING OVER AN END BALCONY? A pure geometry
# census, no pixels, no edge finder, no drawn height believed.
#
# Two attempts to read that edge have now failed in the same way. The step detector on the parapet face
# plane returned a boundary out in the middle of the hall (drawn back on b7s_000152 it circles the lit
# west wall over the dark gallery, 30 m away), and the triangulation returned the camera cloud's own
# position, u 49.204 h 9.658, which is what least squares gives when every ray is nearly parallel. Before
# building a third detector it is worth asking whether the picture contains the thing at all.
#
# So this asks the question directly and for EVERY candidate ceiling, not just the drawn one. A soffit
# front edge is a horizontal line (u, h) running the width of the hall. For each candidate over a grid
# spanning the whole gallery depth and a 4 m range of heights, it counts the deck-standing frames that
# have some point of that line inside their picture. A candidate no frame can see is a candidate this
# footage cannot confirm or refuse, and the honest thing is to say so rather than to report a number.
#   python tools/soffit_reach.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK = 8.34
ENDS = {'west': (0.344, -1.0), 'east': (51.906, 1.0)}
CLASSES = ('b1p', 'b3p', 'b5p', 'b7sp', 'b6gp', 'b1', 'b3', 'b4', 'b5', 'b6s', 'b7s', 'b6g')
DS = np.linspace(0.2, 15.2, 61)

cams = {}
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for fr, (cam, ip) in frames.items():
        cams.setdefault(fr, cam)

for end, (uB, s) in ENDS.items():
    uF = uB - s * 3.85
    deck = []
    for fr, cam in cams.items():
        q = cam.center - O
        cu, ch = float(q @ HU), float(cam.center[1] - O[1])
        if ch > DECK + 0.35 and abs(cu - uB) < 6.0:
            deck.append((fr, cam))
    print('')
    print(end.upper(), 'end:', len(deck), 'frames stand on this deck. The drawn edge is u %.3f h 11.100' % uF)
    if not deck:
        continue
    us = np.linspace(min(uF, uB), max(uF, uB), 16)
    hv = np.arange(9.4, 13.45, 0.1)
    grid = np.zeros((len(hv), len(us)), int)
    for ui, uu in enumerate(us):
        pts = np.array([O + uu * HU + dd * HD + np.array([0, 0.0, 0]) for dd in DS])
        for hi, hh_ in enumerate(hv):
            p = pts + np.array([0, float(hh_), 0])
            n = 0
            for fr, cam in deck:
                x, y, z = cam.project(p)
                if np.any((z > 0.3) * (x > 10) * (x < cam.w - 10) * (y > 10) * (y < cam.h - 10)):
                    n += 1
            grid[hi, ui] = n
    print('   frames that can see a candidate edge, rows h 9.4 up to 13.4, columns u %.2f to %.2f'
          % (us[0], us[-1]))
    for hi in range(len(hv) - 1, -1, -4):
        print('     h %5.1f  ' % hv[hi] + ' '.join('%3d' % v for v in grid[hi]))
    di = int(np.argmin(np.abs(us - uF)))
    dj = int(np.argmin(np.abs(hv - 11.1)))
    print('   the DRAWN edge (u %.2f h 11.10) is inside %d of the %d frames' % (uF, grid[dj, di], len(deck)))
    best = np.unravel_index(int(np.argmax(grid)), grid.shape)
    print('   the most visible candidate anywhere on the grid is u %.2f h %.1f, seen by %d frames'
          % (us[best[1]], hv[best[0]], grid[best]))
    print('   candidates no frame can see: %d of %d on the grid' % (int((grid == 0).sum()), grid.size))
