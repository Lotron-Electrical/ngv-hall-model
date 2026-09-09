# 2026-09-10: a labelled height ladder drawn on an end face, cropped to it, and turned the right way up,
# so the end wall can be LOOKED at against the numbers instead of only scanned.
#
# The lesson this repo learned on 2026-09-09 was that seven clips and 5,300 frames had only ever been fed
# to detectors and never displayed, and that a detector answers the question it was set. The end faces have
# had the same treatment: every number on them came out of a gradient search. This draws the ladder every
# 0.25 m in grey with a label every 0.5 m, marks the levels ENDW actually draws in green, and cuts the
# frame down to the face so a person can see which grey line the real edge sits on.
#   python tools/end_ladder.py <class> <frame> <west|east> <out.jpg> [hlo] [hhi]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
FACE = {'west': 4.194, 'east': 48.056}
DRAWN = [('ground top', 5.30), ('apron', 5.40), ('low deck', 6.33), ('low upstand', 6.85),
         ('low rail', 7.16), ('slab soffit', 8.08), ('top deck', 8.34), ('top parapet', 9.02),
         ('head', 11.09)]
cls, fr, end, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
hlo = float(sys.argv[5]) if len(sys.argv) > 5 else 4.0
hhi = float(sys.argv[6]) if len(sys.argv) > 6 else 11.6
uF = FACE[end]
cam, ip = U.load_class(cls)[fr]
im = cv2.imread(ip)


def pt(d, lev):
    X = O + uF * HU + d * HD + np.array([0.0, lev, 0.0])
    x, y, z = cam.project(np.asarray([X]))
    return (float(x[0]), float(y[0])) if z[0] > 0.3 else None


# the visible band of d on this frame, so the ladder is drawn only where the face is actually in shot
vis = [d for d in np.arange(0.4, 15.0, 0.2)
       if all(p is not None and 1 < p[0] < cam.w - 2 and 1 < p[1] < cam.h - 2
              for p in (pt(d, hlo), pt(d, hhi)))]
if len(vis) < 3:
    sys.exit('%s %s: the %s face is not in this frame' % (cls, fr, end))
d0, d1 = vis[0], vis[-1]
lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
lo, aa, bb = cv2.split(lab)
lo = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(lo)
im = cv2.cvtColor(cv2.merge([lo, aa, bb]), cv2.COLOR_LAB2BGR)

xs, ys = [], []
lev = hlo
while lev <= hhi + 1e-9:
    a, b = pt(d0, lev), pt(d1, lev)
    if a and b:
        half = round(lev * 2) / 2
        major = abs(lev - half) < 1e-6
        cv2.line(im, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])),
                 (170, 170, 170) if major else (95, 95, 95), 2 if major else 1, cv2.LINE_AA)
        xs += [a[0], b[0]]
        ys += [a[1], b[1]]
    lev = round(lev + 0.25, 3)
for nm, lev in DRAWN:
    a, b = pt(d0, lev), pt(d1, lev)
    if a and b:
        cv2.line(im, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (0, 235, 0), 2, cv2.LINE_AA)
x0, x1 = int(max(0, min(xs) - 30)), int(min(cam.w, max(xs) + 30))
y0, y1 = int(max(0, min(ys) - 30)), int(min(cam.h, max(ys) + 30))
sub = im[y0:y1, x0:x1]
# world up runs along the image column axis in these portrait clips. A clockwise turn sends source +x to
# dest +y, so if h grows toward smaller x the picture wants a clockwise turn to stand up.
pa, pb = pt(d0, hlo), pt(d0, hhi)
sh, sw = sub.shape[:2]
mode = 'none'
if abs(pb[0] - pa[0]) > abs(pb[1] - pa[1]):
    mode = 'cw' if pb[0] < pa[0] else 'ccw'
    sub = cv2.rotate(sub, cv2.ROTATE_90_CLOCKWISE if mode == 'cw' else cv2.ROTATE_90_COUNTERCLOCKWISE)
elif pb[1] > pa[1]:
    mode = 'flip'
    sub = cv2.rotate(sub, cv2.ROTATE_180)
s = 1500.0 / max(sub.shape[:2])
sub = cv2.resize(sub, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)


def torow(lev):
    """the row a level lands on AFTER the crop, the turn and the resize.

    THE FIRST VERSION SPACED THE LABELS EVENLY and they did not sit on their own lines. h to image row is
    not linear under perspective, and the crop does not start exactly on hlo, so an evenly spaced ladder
    of numbers beside a projected ladder of lines is two different rulers side by side. Each label is now
    carried through the same transform as the line it belongs to."""
    q = pt(0.5 * (d0 + d1), lev)
    if q is None:
        return None
    cx, ry = q[0] - x0, q[1] - y0
    if mode == 'cw':
        r = cx
    elif mode == 'ccw':
        r = sw - 1 - cx
    elif mode == 'flip':
        r = sh - 1 - ry
    else:
        r = ry
    return int(round(r * s))


H2 = sub.shape[0]
lev = round(hlo * 2) / 2
while lev <= hhi + 1e-9:
    row = torow(lev)
    if row is not None and 12 < row < H2 - 6:
        col = (0, 235, 0) if any(abs(lev - v) < 1e-6 for _, v in DRAWN) else (200, 200, 200)
        cv2.putText(sub, '%.2f' % lev, (6, row + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
    lev = round(lev + 0.5, 3)
for nm, dlev in DRAWN:
    row = torow(dlev)
    if row is not None and 12 < row < H2 - 6:
        cv2.putText(sub, nm, (sub.shape[1] - 190, row - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 235, 0), 1, cv2.LINE_AA)
q = cam.center - O
cv2.putText(sub, '%s %s  %s face  cam u %.1f d %.1f h %.2f  range %.1f m'
            % (cls, fr, end, q @ HU, q @ HD, q[1], abs(q @ HU - uF)),
            (6, H2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 1, cv2.LINE_AA)
cv2.imwrite(out, sub, [cv2.IMWRITE_JPEG_QUALITY, 93])
print('%s  d %.1f to %.1f  %dx%d' % (out, d0, d1, sub.shape[1], sub.shape[0]))
