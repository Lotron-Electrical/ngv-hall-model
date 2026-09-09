# 2026-09-09: WHICH BALCONY FRAMES LOOK UP AT THE CEILING OVER THE BALCONY.
#
# Lloyd, standing on the balconies: "you can see how the ceiling goes above that balcony as well right?
# You can see that in the balcony videos". The model currently says there is NO ceiling over most of that
# deck: ENDW draws a 2.1 m deep front canopy at h 11.1 over the parapet and then leaves the rest open to
# the glass roof (index.html, 'the void behind the front soffit is open to the canopy'). That is a large
# claim about the room and it rests on two hall-floor frames. The balcony clips are the only footage shot
# UNDER whatever is up there, so this lists the frames that can see it: camera standing on a gallery deck,
# view pitched up, at an end of the hall.
#   python tools/balcony_up.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DECKS = [6.33, 8.34]

for cls in ('b1', 'b3', 'b5', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp', 'b6gp'):
    try:
        frames = U.load_class(cls)
    except Exception as exc:
        print(cls, 'could not load:', exc)
        continue
    rows = []
    for fr, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
        fwd = cam.R.T @ np.array([0.0, 0.0, 1.0])
        n = float(np.hypot(float(fwd @ HU), float(fwd @ HD)))
        pitch = float(np.degrees(np.arctan2(float(fwd[1]), n)))
        stand = None
        for dk in DECKS:
            if dk + 0.4 < ch < dk + 2.0:
                stand = dk
        if stand is None:
            continue
        if not (cu < 6.0 or cu > 46.0):
            continue                      # only the two ends carry a balcony
        rows.append((fr, cu, cd, ch, stand, pitch))
    ups = [r for r in rows if r[5] > 8.0]
    print('%-6s %4d frames on a deck at an end, %3d of them pitched up' % (cls, len(rows), len(ups)))
    for r in sorted(ups, key=lambda x: -x[5])[:8]:
        print('        %-12s u %6.2f d %6.2f h %5.2f  on deck %.2f  pitch %+5.1f' % r)
