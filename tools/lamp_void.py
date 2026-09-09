# 2026-09-10: THE SPACE 33 RAYS CROSSED IS EMPTY, AND THIS SWEEPS IT.
#
# tools/gallery_lamp.py triangulated a fitting inside the west end's lower band on u 2.191, d 7.858,
# h 7.083, and reported that its rays crossed the end face plane between h 5.458 and 6.842. That single
# crossing band is only the first slice of a much bigger statement. Each of those rays travelled from a
# camera out in the hall all the way to the fitting, so EVERY point on every ray is empty space. Sweeping
# the rays plane by plane from the face back to the fitting gives, for each depth, the band of heights
# that cannot contain anything solid.
#
# WHY THAT IS THE RIGHT SHAPE OF ANSWER HERE. A bound on one plane can always be dodged by moving the
# surface off that plane, and this model has done exactly that before: the corridor width absorbed a face
# move. The lower tier front could be pushed back a few centimetres, satisfy a face-plane bound, and still
# block the light. A swept void cannot be dodged that way. It says where the emptiness is, in world
# coordinates, and any surface drawn inside it is refuted wherever it sits.
#
# WHAT IT CANNOT DO, said before it is used. The void is only as wide in d as the rays happen to be, so it
# constrains this end near the d of the fitting and says nothing about the rest of the 15.4 m width. It is
# a bound and never a reading: it can delete a surface and can never place one.
#   python tools/lamp_void.py <lamps.jsonl> [nsteps]
import json
import sys

import numpy as np

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
# every quad ENDW draws on the end FACE plane, as (name, h low, h high)
FACE_QUADS = [('end ground wall', 0.00, 5.30), ('gallery apron', 5.40, 6.33),
              ('lower parapet upstand', 6.33, 6.85), ('lower glass rail', 6.85, 7.16),
              ('top gallery fascia', 8.08, 8.34), ('top parapet upstand', 8.34, 9.02),
              ('end wall over the head', 11.09, 13.50)]
# the horizontal slabs it draws from the face back to the plate end, as (name, h)
SLABS = [('lower gallery floor', 6.33), ('lower gallery ceiling', 8.08)]

srcfile = sys.argv[1]
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
recs = [json.loads(ln) for ln in open(srcfile, encoding='utf-8') if ln.strip()]
if not recs:
    sys.exit('no fittings in %s' % srcfile)

for rec in recs:
    uF, uB = rec['uF'], rec['uB']
    s = 1.0 if uB > uF else -1.0            # from the face into the end
    rays = [(np.array(C), np.array(v)) for C, v, _ in rec['rays']]
    print('')
    print('%s end: fitting on u %.3f d %.3f h %.3f from %d rays, %.3f m rms'
          % (rec['end'].upper(), rec['u'], rec['d'], rec['h'], len(rays), rec['rms']))
    print('   face on u %.3f, back wall on u %.3f, so the sweep runs %.3f m into the end'
          % (uF, uB, abs(rec['u'] - uF)))
    print('')
    print('     u      depth behind face   rays    h band that must be EMPTY   d band')
    bands = []
    for uu in np.linspace(uF, rec['u'], NS):
        hs, ds = [], []
        for C, v in rays:
            du = float(v @ HU)
            if abs(du) < 1e-9:
                continue
            t = (uu - float((C - O) @ HU)) / du
            if t <= 0:
                continue
            X = C + t * v
            # only the part of the ray that has not yet reached the fitting is known to be empty
            if (float((X - O) @ HU) - rec['u']) * s > 0.02:
                continue
            q = X - O
            hs.append(float(q[1]))
            ds.append(float(q @ HD))
        if len(hs) < 4:
            continue
        bands.append((float(uu), min(hs), max(hs), min(ds), max(ds), len(hs)))
    if not bands:
        print('   no plane carried four rays; nothing swept')
        continue
    for i, b in enumerate(bands):
        if i % max(1, len(bands) // 12) and i != len(bands) - 1:
            continue
        print('   %7.3f   %8.3f          %3d     %6.3f to %6.3f          %5.2f to %5.2f'
              % (b[0], abs(b[0] - uF), b[5], b[1], b[2], b[3], b[4]))

    print('')
    print('   WHAT THE MODEL DRAWS INSIDE THAT VOID:')
    hit = []
    b0 = bands[0]
    for nm, h0, h1 in FACE_QUADS:
        lo, hi = max(h0, b0[1]), min(h1, b0[2])
        if hi > lo:
            hit.append((nm, 'on the face plane', lo, hi, hi - lo))
    for nm, hv in SLABS:
        for b in bands:
            if b[1] <= hv <= b[2]:
                hit.append((nm, 'a slab on h %.2f, first struck on u %.3f' % (hv, b[0]), hv, hv, 0.0))
                break
    if not hit:
        print('      nothing. Every surface this file draws is clear of the swept void.')
    for nm, where, lo, hi, ov in hit:
        if ov > 0:
            print('      %-24s %s, overlapping the void from h %.3f to %.3f (%.3f m)'
                  % (nm, where, lo, hi, ov))
        else:
            print('      %-24s %s' % (nm, where))
    print('')
    print('   the void is only as wide in d as the rays are, so it constrains this end near d %.1f to %.1f'
          % (min(b[3] for b in bands), max(b[4] for b in bands)))
    print('   and says nothing about the rest of the width. It can delete a surface, never place one.')
