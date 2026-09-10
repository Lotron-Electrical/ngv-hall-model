"""THE EAST RENDER PICK, CHOSEN FOR A CLEAR LINE AND NOT FOR SIZE (2026-09-10, tools/ends_audit.py).

The east's render pick b7s_000908 was chosen by back_wall_hue.py as the frame with the widest EASTBACK
region. Drawn on its render, that region is covered about four fifths by the sim's own columns, so its
80th percentile reads column edges and lamps rather than wall, and every east render band this evening
carried that. The photograph from the same pose has the real columns in it too, but the region's
80th percentile there sits between them; the sim's do not leave it the same gap.

THE RULE. For every west-deck frame (b7s, b7sp) that holds the EASTBACK region 20 px inside the frame
under both the lens model and the pinhole, project the twelve columns (EVENT.cols, radius COL_R_SIM)
as thick lines from the floor to h 13 and count the region's pixels they do not cover. The pick is the
frame with the largest clear FRACTION among those whose region covers at least MINPX pixels, so a
small clean region cannot beat a large clean one by much and a large covered one cannot win at all.
The chosen pose replaces picks[1] in render-shots/render-match.json and back-wall-hue3.json; the west
pick is untouched. The photograph side of the audit does not change, because it never depended on
which frame was rendered.

  python tools/east_pick.py            # rank and write the pick
  python tools/east_pick.py --dry      # rank only
"""
import os, sys, json, math
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from underside_geom import load_class
from back_wall_hue import project, EASTBACK, EAST_CLASSES, W, SCRATCH
from opening_tone import pose

COLS = [[7.71, 3.82], [7.53, 11.41], [14.94, 3.86], [14.88, 11.29], [22.3, 3.86], [22.17, 11.33], [29.67, 3.77], [29.96, 11.15], [37.18, 3.84], [36.82, 11.52], [44.54, 3.80], [44.23, 11.27]]
COL_R_SIM = 0.42     # the drawn column with its eight bars, generous so a near miss counts as covered
MINPX = 20000


def clear_fraction(cam):
    ok, pb = project(cam, EASTBACK)
    if not ok:
        return None
    m = np.zeros((cam.h, cam.w), np.uint8)
    cv2.fillPoly(m, [pb.astype(np.int32)], 1)
    n = int(m.sum())
    if n < MINPX:
        return None
    cov = np.zeros_like(m)
    for u, d in COLS:
        P = np.array([W(u, d, 0.0), W(u, d, 13.0)])
        x, y, z = cam.project(P)
        if (z <= 0.5).any():
            continue
        dist = float(np.linalg.norm(P.mean(0) - cam.center))
        wpx = max(2, int(round(2 * COL_R_SIM * cam.params[0] / dist)))
        cv2.line(cov, (int(x[0]), int(y[0])), (int(x[1]), int(y[1])), 1, wpx)
    clear = int(((m == 1) & (cov == 0)).sum())
    return clear / n, n


def main():
    rows = []
    for cls in EAST_CLASSES:
        for stem, (cam, imgpath) in sorted(load_class(cls).items()):
            r = clear_fraction(cam)
            if r is None:
                continue
            rows.append((r[0], r[1], cls, stem, cam))
    rows.sort(key=lambda t: -t[0])
    for f, n, cls, stem, _ in rows[:8]:
        print('%s %s: clear %.2f of %d px' % (cls, stem, f, n))
    if not rows or '--dry' in sys.argv:
        return
    f, n, cls, stem, cam = rows[0]
    p = pose(cam)
    D = np.array([W(*q) for q in EASTBACK]) - cam.center
    ang = [math.degrees(math.acos(float((d / np.linalg.norm(d)) @ cam.R[2]))) for d in D]
    sqv = min(120.0, 2 * max(ang) + 6)
    pick = dict(u=round(p['u'], 3), d=round(p['d'], 3), h=round(p['h'], 3), fu=round(p['fu'], 4), fd=round(p['fd'], 4), pitch=round(p['pitch'], 2), w=p['w'], hgt=p['h_px'], vfov=round(p['vfov'], 2),
                sqvfov=round(sqv, 1), sqside=round(max(2.0, math.tan(math.radians(sqv / 2)) / math.tan(math.radians(p['vfov'] / 2))), 3), roll=round(p['roll'], 2), cls=cls, frame=int(stem.split('_')[1]), stem=stem, region='east')
    for path in ('render-shots/render-match.json', SCRATCH + '/back-wall-hue3.json'):
        J = json.load(open(path))
        picks = J if isinstance(J, list) else J['picks']
        print('%s: picks[1] was %s, now %s (clear %.2f)' % (path, picks[1]['stem'], stem, f))
        picks[1] = pick
        json.dump(J, open(path, 'w'), indent=1)


if __name__ == '__main__':
    main()
