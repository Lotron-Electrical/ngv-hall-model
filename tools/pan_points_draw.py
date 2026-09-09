# 2026-09-09: LOOK AT THE TRIANGULATED POINTS BEFORE BELIEVING THEM.
# tools/pan_points.py returns 3,611 near-field points around north opening 5 in hall coordinates, and a
# height histogram alone cannot say what they lie ON. A concentration near h 10.5 is a rail, a soffit, a
# lighting truss or a coincidence, and the difference decides whether anything in index.html may move.
# So the points are drawn back into the frame they came from, coloured by height, over the real pixels.
# A structure reads instantly that way: a rail is a line of one colour, a wall is a smooth ramp of colour,
# and scattered confetti is noise that passed the filters.
#   python tools/pan_points_draw.py <class> <frame> <points.csv> [out.jpg] [scale]
import csv
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

cls, frame, csvpath = sys.argv[1], sys.argv[2], sys.argv[3]
out = sys.argv[4] if len(sys.argv) > 4 else 'E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose/points.jpg'
scale = float(sys.argv[5]) if len(sys.argv) > 5 else 0.42

cam, ipath = U.load_class(cls)[frame]
im = cv2.imread(ipath)
rows = list(csv.DictReader(open(csvpath)))
P = np.array([[float(r['u']), float(r['d']), float(r['h'])] for r in rows])
X = O + P[:, 0:1] * HU + P[:, 1:2] * HD + np.stack([np.zeros(len(P)), P[:, 2], np.zeros(len(P))], axis=1)
x, y, z = cam.project(X)
C = cam.center - O
rng = np.linalg.norm(X - cam.center, axis=1)

lo, hi = float(np.percentile(P[:, 2], 2)), float(np.percentile(P[:, 2], 98))
drawn = 0
for k in range(len(P)):
    if z[k] <= 0.3 or not (0 <= x[k] < im.shape[1]) or not (0 <= y[k] < im.shape[0]):
        continue
    t = float(np.clip((P[k, 2] - lo) / max(1e-6, hi - lo), 0.0, 1.0))
    col = cv2.applyColorMap(np.uint8([[int(t * 255)]]), cv2.COLORMAP_JET)[0, 0]
    cv2.circle(im, (int(round(x[k])), int(round(y[k]))), 5, (int(col[0]), int(col[1]), int(col[2])), -1)
    drawn += 1

cv2.putText(im, '%s %s  camera u %.2f d %.2f h %.2f' % (cls, frame, C @ HU, C @ HD, C[1]),
            (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
cv2.putText(im, '%d points, blue h %.2f to red h %.2f, range %.1f to %.1f m' % (drawn, lo, hi, rng.min(), rng.max()),
            (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
im = cv2.resize(im, None, fx=scale, fy=scale)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(out, drawn, 'of', len(P), 'points fell inside this frame')
