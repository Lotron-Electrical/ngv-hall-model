# 2026-09-10: measure the end balcony's back wall by COUNTING ITS COURSES, which needs no camera pose.
#
# WHY THIS EXISTS. Every height on the end balconies rests on a registered camera, and the frames that
# stand ON the balcony are the ones the registrar could not solve, because the site model it solves
# against is the hall and a frame aimed at the wall beside the operator has almost nothing in it to match.
# So the best views of the balcony are the ones with no pose. A ruler that does not need one is worth more
# here than another detector.
#
# THE RULER IS ALREADY MEASURED AND IT IS IN THIS REPO. The bluestone ashlar of this hall was coursed off
# the 4 mm orthophotos of 1,026 posed frames: north joints on h = 0.080 + 0.304k, south on 0.119 + 0.309k,
# a course of 0.306 m. The end walls are the same stone in the same courses. So a count of joints between
# two features in ONE photograph is a distance in metres, with no camera in the argument at all.
#
# WHAT IT CANNOT DO, said before it is used. A count gives a SEPARATION, never an absolute height, so it
# can test whether the drawn stack is internally the right size and cannot tell you where that stack sits.
# It also assumes the end wall courses with the long walls, which is likely in one build and is not proved.
# Both limits are printed with the answer.
#
# HOW THE JOINTS ARE FOUND. A joint is a dark line across a lit face, so a column of the wall read top to
# bottom is a bright field with narrow dark notches in it. The profile is high-passed against its own
# local median to kill the lighting gradient, and the notches are taken as local minima with a minimum
# separation set well under one course so a real joint is never merged with its neighbour. Perspective is
# handled by NOT assuming a constant pitch: the spacing is reported per gap and the median is quoted with
# its spread, so a strip running away from the camera declares itself.
#   python tools/wall_courses.py <clip> <frame> <x0> <x1> <y0> <y1> <out.jpg>
# x and y are fractions of the frame, so the same call works whatever the clip's resolution.
import os
import sys

import cv2
import numpy as np

B2 = 'E:/sitecapture-captures/ngv-video/balcony2'
COURSE = 0.306
CLIP, FR = sys.argv[1], int(sys.argv[2])
X0, X1, Y0, Y1 = [float(a) for a in sys.argv[3:7]]
OUT = sys.argv[7]
NSTRIP = int(os.environ.get('NSTRIP', '7'))
MINSEP = int(os.environ.get('MINSEP', '22'))

src = '%s/%s/images' % (B2, CLIP)
name = [n for n in sorted(os.listdir(src)) if ('%06d' % FR) in n]
if not name:
    sys.exit('no frame %d in %s' % (FR, CLIP))
im = cv2.imread(os.path.join(src, name[0]))
H, W = im.shape[:2]
gx0, gx1 = int(X0 * W), int(X1 * W)
gy0, gy1 = int(Y0 * H), int(Y1 * H)
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float64)
g = cv2.GaussianBlur(g, (5, 5), 0)

allpitch = []
draw = im.copy()
report = []
for si, xc in enumerate(np.linspace(gx0 + 20, gx1 - 20, NSTRIP)):
    c0, c1 = int(xc) - 14, int(xc) + 14
    prof = g[gy0:gy1, c0:c1].mean(axis=1)
    if len(prof) < 80:
        continue
    k = 61
    med = np.array([np.median(prof[max(0, i - k // 2):i + k // 2 + 1]) for i in range(len(prof))])
    hp = prof - med
    rows = []
    for i in range(2, len(hp) - 2):
        if hp[i] < -1.2 and hp[i] <= hp[i - 1] and hp[i] < hp[i + 1] and hp[i] <= hp[i - 2] \
                and hp[i] < hp[i + 2]:
            if not rows or i - rows[-1] >= MINSEP:
                rows.append(i)
            elif hp[i] < hp[rows[-1]]:
                rows[-1] = i
    if len(rows) < 4:
        continue
    gaps = np.diff(np.array(rows))
    keep = gaps[np.logical_and(gaps > MINSEP, gaps < 4 * np.median(gaps))]
    allpitch += list(keep)
    report.append((si, int(xc), len(rows), rows[0] + gy0, rows[-1] + gy0, float(np.median(keep))))
    for r in rows:
        cv2.line(draw, (c0, gy0 + r), (c1, gy0 + r), (0, 230, 255), 3, cv2.LINE_AA)
    cv2.putText(draw, '%d' % si, (c0, gy0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 230, 255), 3)

cv2.rectangle(draw, (gx0, gy0), (gx1, gy1), (60, 255, 60), 3)
if not report:
    sys.exit('no strip produced enough joints; move the window or lower the bar')

P = np.array(allpitch, dtype=np.float64)
pitch = float(np.median(P))
print('%s %s   frame %d x %d,   window x %d-%d  y %d-%d' % (CLIP, name[0], W, H, gx0, gx1, gy0, gy1))
print('')
print('   strip   x      joints   first row   last row   pitch px')
for si, xc, n, r0, r1, p in report:
    print('   %-6d  %-6d %-8d %-11d %-10d %.1f' % (si, xc, n, r0, r1, p))
print('')
print('   %d gaps over %d strips, median pitch %.1f px, quartiles %.1f to %.1f'
      % (len(P), len(report), pitch, np.percentile(P, 25), np.percentile(P, 75)))
print('   spread %.0f%% of a course, which is what perspective and joint quality cost here'
      % (100 * (np.percentile(P, 75) - np.percentile(P, 25)) / pitch))
print('')
print('   ONE COURSE IS %.3f m (measured: north joints h = 0.080 + 0.304k, south 0.119 + 0.309k, from'
      % COURSE)
print('   the 4 mm orthophotos of 1,026 posed frames). So in this window %.1f px is one course and the'
      % pitch)
print('   window spans %.2f m of wall.' % ((gy1 - gy0) / pitch * COURSE))
print('')
print('   TO USE IT: read two features off %s, take the row difference, divide by %.1f, times %.3f.'
      % (OUT, pitch, COURSE))
print('   This is a SEPARATION and never an absolute height, and it assumes the end wall courses with the')
print('   long walls, which is likely in one build and is not proved here.')
s = 1400.0 / max(H, W)
cv2.imwrite(OUT, cv2.resize(draw, None, fx=s, fy=s), [cv2.IMWRITE_JPEG_QUALITY, 92])
print('   wrote %s' % OUT)
