# 2026-09-10: THE RAIL CANNOT BE TALLER THAN THE SIGHTLINE THAT GOT PAST IT.
#
# tools/pose_pair.py rendered this model from b3_000100's own solved camera, standing ON the east deck at
# u 48.22 d 5.43 h 9.81, and put a solid black band across the middle of a view that is open in the
# photograph. Naming the mesh needs no renderer at all, only the numbers this file already carries.
#
# WHAT IS DRAWN ON THE EAST FACE PLANE u 48.056, top to bottom: stone from the head 11.09 up, then nothing
# until the handrail 9.805 to 9.865, a GLASS rail 9.095 to 9.865, the solid parapet upstand 8.34 to 9.095,
# the fascia 8.08 to 8.34. Only two of those are opaque, the upstand and the 60 mm handrail, and the
# question this asks is whether either of them stands where a sightline that plainly worked went through.
#
# THE HANDRAIL WAS THE FIRST GUESS AND THIS TOOL KILLED IT. Written on 2026-09-10 to confirm that the
# handrail is what blocks the view, it does the opposite: the lowest sightline at each end passes BELOW
# the handrail and ABOVE the solid upstand, threading the glass, so no opaque surface this file draws on
# that face stands in the way. The guess is withdrawn and the band in the render is still unexplained.
#
# AND THAT TURNS THE PICTURE INTO A MEASUREMENT. The operator saw the hall: the frame contains the canopy,
# both long walls, the truss, the carpet and people. So the sightline that produced it was NOT blocked, so
# nothing solid stood where that ray crossed the face plane. Project the ray, find the crossing height,
# and the rail top at that end cannot be above it. This is the same shape of argument gallery_lamp.py used
# on the soffit: light arrived, therefore nothing was in the way, therefore a bound.
#
# WHICH RAY. The optical axis, because it is the one ray guaranteed to be looking at whatever the frame is
# a picture of. Rays further down in the frame would give a tighter bound and need the image read to know
# they are hall and not deck, so they are not used. The bound is therefore conservative on purpose.
#
# WHAT IT CANNOT DO. It bounds the rail from above and can never place it, and it assumes the pose. A
# frame whose camera is wrong by 0.2 m in h moves its bound by 0.2 m, so the bound is reported per frame
# and the spread is printed rather than hidden in a minimum.
#   python tools/rail_seeover.py
import sys

import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
ENDS = {'west': {'face': 4.194, 'deck': 8.34, 'rail': 1.459, 'ups': 0.757, 'sense': -1.0},
        'east': {'face': 48.056, 'deck': 8.34, 'rail': 1.525, 'ups': 0.755, 'sense': 1.0}}
CLASSES = ('b1', 'b3', 'b5', 'b7s', 'b6g', 'b1p', 'b3p', 'b5p', 'b7sp')

for end, E in ENDS.items():
    uF, s = E['face'], E['sense']
    rows = []
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in frames.items():
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            # standing ON this end's deck: behind the face, inside the hall's width, at deck height
            if (cu - uF) * s < 0.0 or (cu - uF) * s > 3.5:
                continue
            if not (0.5 < cd < 14.9) or not (E['deck'] + 0.6 < ch < E['deck'] + 2.4):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            fu = float(f @ HU)
            # it must be LOOKING OUT of the gallery, or its axis never crosses the face at all
            if fu * s > -0.15:
                continue
            t = (uF - cu) / fu
            if t <= 0:
                continue
            X = cam.center + t * f
            qq = X - O
            rows.append((cname, k, cu, cd, ch, float(qq[1]), float(qq @ HD), t))
    print('')
    print('%s end, face u %.3f, deck %.2f, this file draws the rail top %.3f m over the deck (h %.3f)'
          % (end.upper(), uF, E['deck'], E['rail'], E['deck'] + E['rail']))
    if not rows:
        print('   no posed frame stands on this deck looking out')
        continue
    print('   %-5s %-14s  cam u    d     h     axis crosses the face on h   over the deck   range')
    for cname, k, cu, cd, ch, hx, dx, t in sorted(rows, key=lambda r: r[5])[:14]:
        print('   %-5s %-14s %6.2f %5.2f %5.2f          %6.3f            %6.3f       %.2f m'
              % (cname, k, cu, cd, ch, hx, hx - E['deck'], t))
    hs = np.array([r[5] for r in rows])
    lo = float(hs.min())
    print('   %d frames stand on this deck and look out. The lowest unobstructed axis crosses the face on'
          % len(rows))
    print('   h %.3f, which is %.3f m over the deck, and the frames spread %.3f m.'
          % (lo, lo - E['deck'], float(hs.max() - hs.min())))
    # ONLY AN OPAQUE SURFACE CAN REFUTE A SIGHTLINE, and the first version of this compared against the
    # RAIL TOP, which is the top of a glass panel. Glass does not block a view. The opaque things this
    # file draws on the face are the solid upstand, from the deck up to ups, and the handrail, the top
    # 60 mm of the rail. A ray is refuted only if it crosses a band one of those occupies.
    ups_hi = E['deck'] + E['ups']
    hand_lo, hand_hi = E['deck'] + E['rail'] - 0.06, E['deck'] + E['rail']
    hit_ups = lo <= ups_hi
    hit_hand = hand_lo <= lo <= hand_hi
    print('   OPAQUE ELEMENTS ON THIS FACE: the solid upstand up to h %.3f, and the handrail h %.3f to'
          % (ups_hi, hand_lo))
    print('   %.3f. The glass between them cannot block a view and is not tested.' % hand_hi)
    if hit_ups:
        print('   REFUTED: the lowest sightline passes through the solid upstand.')
    elif hit_hand:
        print('   REFUTED: the lowest sightline passes through the handrail.')
    else:
        print('   NEITHER IS REFUTED. The lowest axis crosses at h %.3f, above the upstand top %.3f and'
              % (lo, ups_hi))
        print('   below the handrail at %.3f, so it threads the glass. The occlusion test PASSES here,'
              % hand_lo)
        print('   and the band seen in the pair render is NOT explained by the opaque end-face geometry.')
