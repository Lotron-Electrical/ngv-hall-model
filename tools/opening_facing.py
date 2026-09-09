# 2026-09-09: which way do the lenses standing IN the north openings actually look?
#
# Three clips stand inside apertures on the north wall: b1 in opening 5, b5 in opening 6, b4 in opening 11,
# 340 frames between them and their pans, all at gallery height and all within half a metre of the wall
# plane. That is the one vantage the collimation argument does not reach. Whether any of it is useful for
# the room BEHIND the wall depends entirely on which way the operator was pointing, and a north test with
# a threshold in it can hide the answer, so this prints the distribution rather than a count.
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

print('%-5s %4s   fwd toward the corridor: min / median / max     how many point in at all   tilt'
      % ('clip', 'n'))
for cls in ('b1', 'b1p', 'b4', 'b5', 'b5p'):
    try:
        frames = U.load_class(cls)
    except Exception:
        print('%-5s could not be loaded' % cls)
        continue
    vals, ups = [], []
    for stem, (cam, ip) in frames.items():
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.linalg.norm([float(fwd @ HU), float(fwd @ HD)]))
        vals.append(-float(fwd @ HD) / max(n, 1e-9))     # positive = looking INTO the corridor
        ups.append(float(fwd[1]))
    v = np.array(vals)
    u = np.array(ups)
    print('%-5s %4d   %+.2f / %+.2f / %+.2f      %4d of %d          %+.2f'
          % (cls, len(v), v.min(), float(np.median(v)), v.max(), int((v > 0).sum()), len(v),
             float(np.median(u))))
print('')
print('positive means the optical axis has a component pointing north, into the room behind the wall.')
print('1.00 would be square on to it, 0.00 along the wall, negative back out into the hall.')
