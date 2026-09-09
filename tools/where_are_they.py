# 2026-09-09: before filtering cameras, look at where they actually are. The first run of
# tools/corridor_from_opening.py kept nothing, and a filter that keeps nothing is either a true refusal or
# a wrong assumption, and those look identical from the outside. This tells them apart.
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
CLASSES = os.environ.get('CLASSES', 'b1 b1p b3 b3p b4 b5 b5p b7s b7sp b6g b6gp walk night day4k').split()

print('%-6s %5s   u range          d range          h range      facing north  near wall'
      % ('clip', 'n'))
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        print('%-6s could not be loaded' % cls)
        continue
    cu, cd, ch, north = [], [], [], 0
    for stem, (cam, ip) in frames.items():
        q = cam.center - O
        cu.append(float(q @ HU))
        cd.append(float(q @ HD))
        ch.append(float(cam.center[1] - O[1]))
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
        if n > 1e-6 and float(fwd @ HD) / n < -0.30:
            north += 1
    cu, cd, ch = np.array(cu), np.array(cd), np.array(ch)
    near = int((np.abs(cd - (-0.090)) < 1.2).sum())
    print('%-6s %5d   %6.2f to %6.2f   %6.2f to %6.2f   %5.2f to %5.2f   %5d       %5d'
          % (cls, len(cu), cu.min(), cu.max(), cd.min(), cd.max(), ch.min(), ch.max(), north, near))

# AND THE ONE QUESTION THAT MATTERS: is there ANY lens anywhere in the archive inside a north aperture?
print('')
best = []
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception:
        continue
    for stem, (cam, ip) in frames.items():
        q = cam.center - O
        d = float(q @ HD)
        h = float(cam.center[1] - O[1])
        if 8.3 < h < 11.4 and d < 2.0:
            best.append((d, stem, float(q @ HU), h))
best.sort()
print('%d lenses sit at opening height and within 2 m of the wall plane; the ten closest:' % len(best))
for d, stem, u, h in best[:10]:
    print('   %-22s u %6.2f  d %+6.3f  h %6.3f' % (stem, u, d, h))
