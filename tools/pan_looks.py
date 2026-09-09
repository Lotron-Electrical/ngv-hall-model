# 2026-09-09: WHERE THE NEW FRAMES ARE POINTING. The whole claim is that the pan chaining recovers the
# frames aimed at the balcony rather than down the hall, so that claim has to be checked, not assumed.
# For every frame in a pan model this prints where the camera stands in hall coordinates and which way it
# looks, split into the component along the hall (u) and the component across it (d). A frame aimed down
# the hall has almost all of its look in u; a frame aimed at the parapet, the deck or the back wall of the
# balcony has most of it in d or straight down.
#   python tools/pan_looks.py <class>
import json
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

cls = sys.argv[1]
frames = U.load_class(cls)
spec = U.CLASSES[cls]
qpath = os.path.join(spec['model'], 'pan-quality.json')
qual = json.load(open(qpath))['frames'] if os.path.exists(qpath) else {}

rows = []
for stem, (cam, _path) in frames.items():
    c = cam.center - O
    look = cam.R.T @ np.array([0.0, 0.0, 1.0])
    q = qual.get(stem + '.png', {})
    rows.append((stem, float(c @ HU), float(c @ HD), float(cam.center[1] - O[1]),
                 float(look @ HU), float(look @ HD), float(look[1]), q.get('hops'), q.get('centre')))
rows.sort(key=lambda r: r[0])

along = np.array([abs(r[4]) for r in rows])
across = np.array([abs(r[5]) for r in rows])
down = np.array([r[6] for r in rows])
anch = np.array([1 if r[7] == 0 else 0 for r in rows])
print(cls, len(rows), 'frames:', int(anch.sum()), 'anchors and', int(len(rows) - anch.sum()), 'pan-chained')
print('')
print('  HOW MUCH OF THE LOOK IS ALONG THE HALL (1.0 = straight down it, 0 = square across it)')
for label, sel in [('anchors', anch == 1), ('pan-chained', anch == 0)]:
    if sel.sum() < 2:
        continue
    print('   ', label.ljust(12), 'median', round(float(np.median(along[sel])), 2),
          ' quartiles', round(float(np.percentile(along[sel], 25)), 2), round(float(np.percentile(along[sel], 75)), 2),
          ' | across median', round(float(np.median(across[sel])), 2),
          ' | looking down median', round(float(np.median(down[sel])), 2))
turned = np.logical_and(anch == 0, along < 0.5)
print('')
print('   ', int(turned.sum()), 'pan-chained frames are turned more than 60 degrees off the hall axis,')
print('    which is what looking at the balcony itself means. Anchors that turned:',
      int(np.logical_and(anch == 1, along < 0.5).sum()))
print('')
print('  the twelve most turned-away frames, which no accepted set contains')
order = np.argsort(along + (anch * 10.0))
for k in order[:12]:
    r = rows[k]
    print('   ', r[0], 'u', round(r[1], 2), 'd', round(r[2], 2), 'h', round(r[3], 2),
          '| look along', round(r[4], 2), 'across', round(r[5], 2), 'down', round(r[6], 2),
          '|', r[8])
