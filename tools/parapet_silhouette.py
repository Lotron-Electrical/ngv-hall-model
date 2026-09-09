# 2026-09-09: THE EAST PARAPET READ AS A SILHOUETTE FROM A METRE BEHIND IT.
#
# Shooting the sim from b7s_000132's own pose and laying it beside the photograph shows one plain
# disagreement: the near geometry at the bottom of the frame. In the photograph the parapet the operator
# is leaning over blocks about the bottom seventh of the picture. In the render, the rail and the deck
# behind it take nearly the bottom two fifths. Whatever else is right in that pair, and most of it is, the
# sim is putting more stone between this camera and the hall than the camera actually had.
#
# That difference is measurable, and it is the one edge on this gallery a silhouette CAN reach. The soffit
# failed three instruments this afternoon because its edge is 55 degrees overhead and off the frame; the
# parapet is 1.05 m in front and below the lens, and it stands as a hard dark boundary against a lit hall.
# The boundary is found by walking each image column with no world geometry in the search, and only then
# turned into a height by meeting its ray with the parapet's face plane. The drawn 9.11 never enters, and
# the answer is free to land anywhere between the deck and the roof.
#   python tools/parapet_silhouette.py [frame ...]
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
UFACE_EAST, UFACE_WEST = 48.056, 4.194
DECK, DRAWN_TOP = 8.34, 9.11
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose'
CONTRAST = 30.0
BAND = 40


def bottom_boundary(grey, x):
    """walking UP from the bottom of column x, the first strong dark-to-bright step"""
    col = grey[:, x].astype(np.float32)
    n = len(col)
    for r in range(n - BAND - 2, BAND, -3):
        below = col[r + 1:r + 1 + BAND].mean()
        above = col[r - BAND:r].mean()
        if above - below > CONTRAST and below < 110.0:
            return r
    return None


frames = {}
for cls in ('b7sp', 'b7s', 'b3p', 'b3', 'b6gp', 'b6g'):
    try:
        frames.update({k: v for k, v in U.load_class(cls).items() if k not in frames})
    except Exception:
        pass

stems = [a for a in sys.argv[1:] if a != 'draw'] or ['b7s_000132']
allh = []
rays = []
for stem in stems:
    if stem not in frames:
        print(stem, 'is not posed')
        continue
    cam, ip = frames[stem]
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    uF = UFACE_EAST if cu > 26.0 else UFACE_WEST
    grey = cv2.GaussianBlur(cv2.imread(ip, cv2.IMREAD_GRAYSCALE), (7, 7), 0)
    # the ladder of heights on the parapet face plane, used ONLY to turn a found pixel into a height
    hs = np.arange(DECK - 0.6, DECK + 3.4, 0.005)
    # THE LADDER HAS TO BE FINE IN DEPTH, not just in height. The camera stands 1.05 m behind this plane,
    # so a 0.25 m step along the hall is a huge stride in pixels and the first run matched only one or two
    # columns out of thirty. 400 stations put the grid well under a pixel where it matters.
    ds = np.linspace(0.2, 15.2, 400)
    pts = np.array([O + uF * HU + dd * HD + np.array([0, float(v), 0]) for dd in ds for v in hs])
    px, py, pz = cam.project(pts)
    gh = np.array([float(v) for _dd in ds for v in hs])
    ok = pz > 0.3
    got = []
    for x in range(100, cam.w - 100, 30):
        r = bottom_boundary(grey, x)
        if r is None:
            continue
        dist = np.where(ok, np.hypot(px - x, py - r), 1e9)
        k = int(np.argmin(dist))
        if float(dist[k]) > 25.0:
            continue
        # the RAY as well as the height, because the height alone assumes the edge stands on the drawn
        # face station. It may not, and one frame cannot tell the two apart: a face 0.2 m nearer the
        # camera reads 0.2 m of height differently. Frames standing at different u can, so the ray is
        # kept and the pair is fitted at the end.
        P = pts[k]
        rel = P - cam.center
        got.append((x, r, float(gh[k]), float(rel @ HU), float(rel[1])))
        rays.append((float(cu), float(ch), float(rel @ HU), float(rel[1])))
    if len(got) < 4:
        print('%-12s only %d columns found a boundary on the face plane' % (stem, len(got)))
        continue
    a = np.array([g[2] for g in got])
    a = a[np.abs(a - np.median(a)) < 0.35]           # the odd column locks onto a column or a truss
    if len(a) < 4:
        print('%-12s the columns did not agree on one edge' % stem)
        continue
    med = float(np.median(a))
    allh.append((stem, cu, cd, ch, len(got), med, float(a.max() - a.min())))
    print('%-12s camera u %6.2f d %6.2f h %5.2f | %2d columns, parapet top h %.3f, spread %.3f'
          % (stem, cu, cd, ch, len(got), med, float(a.max() - a.min())))
    if 'draw' in sys.argv:
        im = cv2.imread(ip)
        for g in got:
            cv2.circle(im, (g[0], g[1]), 14, (0, 255, 255), 3)
        cv2.putText(im, '%s  parapet top h %.3f (drawn %.2f)' % (stem, med, DRAWN_TOP), (40, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 4, cv2.LINE_AA)
        os.makedirs(OUT, exist_ok=True)
        k = 1400.0 / im.shape[0]
        cv2.imwrite(os.path.join(OUT, stem + '-parapet.jpg'),
                    cv2.resize(im, (int(im.shape[1] * k), 1400)), [cv2.IMWRITE_JPEG_QUALITY, 86])

if len(allh) >= 2:
    v = np.array([r[5] for r in allh])
    print('')
    print('%d frames, median parapet top h %.3f, range %.3f. The sim draws %.3f, so this is %+.3f m off.'
          % (len(v), float(np.median(v)), float(v.max() - v.min()), DRAWN_TOP, float(np.median(v)) - DRAWN_TOP))
    print('the deck under it is drawn on %.3f, so the upstand plus rail measures %.3f against a drawn %.3f'
          % (DECK, float(np.median(v)) - DECK, DRAWN_TOP - DECK))

# THE TWO UNKNOWNS TOGETHER. Each detected pixel gives a ray, and the parapet's top edge is a horizontal
# line (u*, h*) running the width of the hall, so vh*u* - vu*h* = vh*cu - vu*ch is linear in both. This is
# the fit the gallery soffit could not support because its frames spanned 0.40 m; here b3 stands on the
# same deck 0.6 to 0.8 m nearer the parapet than b7s, which is most of the unknown itself.
if len(rays) >= 12:
    R = np.array(rays)
    spread = float(R[:, 0].max() - R[:, 0].min())
    A = np.stack([R[:, 3], -R[:, 2]], 1)
    y = R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1]
    sol, _r, _rk, sv = np.linalg.lstsq(A, y, rcond=None)
    cond = float(sv.max() / sv.min()) if sv.min() > 0 else float('inf')
    res = A @ sol - y
    print('')
    print('%d rays from cameras spanning %.2f m of u; the fit puts the edge on u %.3f h %.3f'
          % (len(R), spread, float(sol[0]), float(sol[1])))
    print('   condition number %.0f, residual rms %.4f. The sim draws the face on 48.056 and the top on 9.110.'
          % (cond, float(np.sqrt((res ** 2).mean()))))
    if spread < 0.5:
        print('   THE CAMERAS DID NOT MOVE ENOUGH TO SEPARATE THE TWO. Refused.')
    # THE TEST THAT MATTERS is not where the best line sits, it is whether the DRAWN line is worse. A fit
    # with a 0.28 m residual is not a measurement of anything, but if the sim's own line fits these rays
    # just as badly then the rays cannot choose between them and nothing here refutes the model.
    def rms_for(uu, vv):
        r = R[:, 3] * uu - R[:, 2] * vv - (R[:, 3] * R[:, 0] - R[:, 2] * R[:, 1])
        return float(np.sqrt((r ** 2).mean()))
    best = rms_for(float(sol[0]), float(sol[1]))
    drawn = rms_for(48.056, 9.110)
    print('   residual of the best line %.4f, of the line this file draws %.4f, ratio %.2f'
          % (best, drawn, drawn / max(best, 1e-9)))
    if drawn < best * 1.5:
        print('   THE DRAWN LINE FITS THESE RAYS AS WELL AS THE BEST ONE DOES, so this edge does not')
        print('   refute it and nothing is moved. The pair shot difference stays a QUESTION, not a fault.')
    else:
        print('   the drawn line fits measurably worse, so it is the thing to look at next')
