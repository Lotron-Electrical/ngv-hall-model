# 2026-09-09: WHICH FOOTAGE ACTUALLY WALKS ALONG A BALCONY, and how much of that walk is posed.
#
# Lloyd, 2026-09-09: "in one of the videos I referenced I walk along the balcony. I'm telling you but
# you're not listening that that is footage of the balcony." He is right, and the reason the archive has
# not used it is visible only when the posed cameras are laid out as a PATH rather than counted.
#
# Every previous read of these galleries quoted a camera span of 0.68 m and called the fit ill-conditioned.
# That is the span of the ACCEPTED frames, and the accepted frames are the ones aimed down the hall, because
# the site model they were solved against carries the hall and almost no surface on a balcony. A frame taken
# while walking past the parapet has little in that model to match, so it was refused. The walk is in the
# clip; it is not in the poses. That is a gate, not a fact about the footage.
#
# So this lays the posed cameras out in FRAME ORDER: where each stands in the hall frame, how far it moved
# from the one before, and the length of the whole traced route. A pan sits at one station for dozens of
# frames. A WALK keeps moving. Beside it goes the raw extracted frame count, so the gap between what Lloyd
# shot and what has a pose is on the page in numbers.
#   python tools/balcony_walk.py
import os
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECK, LOWER = 8.34, 6.33
CLASSES = ('b1', 'b3', 'b4', 'b5', 'b6s', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp', 'day4k')


def fnum(stem):
    t = stem.rsplit('_', 1)[-1]
    return int(t) if t.isdigit() else -1


print('POSED CAMERAS STANDING ABOVE THE HALL FLOOR, IN FRAME ORDER')
print('a pan sits still, a walk keeps moving. lower deck %.2f, top deck %.2f' % (LOWER, DECK))
for cls in CLASSES:
    try:
        frames = U.load_class(cls)
    except Exception as e:
        print('')
        print('%-6s could not be loaded: %s' % (cls, str(e).split('\n')[0][:70]))
        continue
    raw = U.CLASSES[cls].get('frames')
    nraw = len(os.listdir(raw)) if raw and os.path.isdir(raw) else 0
    rows = []
    for stem, (cam, _ip) in frames.items():
        q = cam.center - O
        ch = float(cam.center[1] - O[1])
        if ch < LOWER - 0.6:
            continue                                    # standing on the hall floor, not on a balcony
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        rows.append((fnum(stem), stem, float(q @ HU), float(q @ HD), ch,
                     float(fwd @ HU), float(fwd @ HD)))
    print('')
    print('%-6s %4d posed frames, %4d of them above the floor, out of %d extracted'
          % (cls, len(frames), len(rows), nraw))
    if not rows:
        continue
    rows.sort()
    P = np.array([[r[2], r[3], r[4]] for r in rows])
    steps = np.linalg.norm(np.diff(P, axis=0), axis=1) if len(P) > 1 else np.array([0.0])
    walked = float(steps.sum())
    print('   u %6.2f to %6.2f (%.2f m)   d %6.2f to %6.2f (%.2f m)   h %5.2f to %5.2f'
          % (P[:, 0].min(), P[:, 0].max(), np.ptp(P[:, 0]),
             P[:, 1].min(), P[:, 1].max(), np.ptp(P[:, 1]), P[:, 2].min(), P[:, 2].max()))
    print('   route through the posed frames %.2f m long, biggest single gap %.2f m'
          % (walked, float(steps.max())))
    for r in rows:
        print('      %-14s u %6.2f d %6.2f h %5.2f  looking u %+.2f d %+.2f'
              % (r[1], r[2], r[3], r[4], r[5], r[6]))
