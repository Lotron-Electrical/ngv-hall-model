# 2026-09-09: THE CORRIDOR BEHIND THE NORTH WALL, MEASURED BY THE CAMERAS THAT STOOD IN IT.
# Everything drawn behind that wall (width 2.0, floor 8.34, ceiling 11.4) is either inferred or unmeasured,
# and today's audit showed why nothing photometric will fix that: from the hall floor an opening is 100-150
# px wide with under 20 grey levels of signal inside it, and the head soffit stands over the reveal so an
# upward sightline ends on its underside. The one instrument left is the one that settled where clip 153148
# was shot: a REGISTERED CAMERA IS A MEASUREMENT OF THE POINT IT STOOD AT. If a phone was carried into that
# corridor and those frames registered against the site model, the corridor has been surveyed from inside,
# whatever the pixels look like.
# This walks every accepted model in the archive, puts every camera centre in the hall's frame, and sorts
# them by where they stand relative to the north wall.
#   python tools/corridor_poses.py [--csv out.csv]
import sys, os, numpy as np
sys.path.insert(0, 'tools')
import underside_geom as U
from colmap_bin import read_model

O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
FACE = -0.09          # the north wall's inner (hall side) face
REVEAL = -0.99        # the back of the reveal: FACE minus openDepth 0.9
BACK = -2.99          # the corridor's back wall as drawn: REVEAL minus width 2.0

rows = []
for name in ('walk', 'night', 'day4k', 'b1', 'b3', 'b6g', 'b7s'):
    spec = U.CLASSES[name]
    if not os.path.isdir(spec['model']):
        print('%-6s no model' % name); continue
    cams, imgs, _ = read_model(spec['model'], with_points2d=False)
    for im in imgs.values():
        stem = os.path.basename(im.name).rsplit('.', 1)[0]
        if spec['prefixes'] is not None and stem.split('_')[0] not in spec['prefixes']:
            continue
        R, t = im.R(), im.t
        C = -R.T @ t
        f = R.T @ np.array([0, 0, 1.0])
        q = C - O
        rows.append((name, stem, float(q @ HU), float(q @ HD), float(q[1]),
                     float(f @ HU), float(f @ HD), float(f[1])))

print('%d registered cameras across %d classes' % (len(rows), len({r[0] for r in rows})))
print('the north wall inner face is d %.2f; the reveal ends d %.2f; the corridor is drawn d %.2f to %.2f'
      % (FACE, REVEAL, REVEAL, BACK))
print('')
bands = [('in the hall (d > %.2f)' % FACE, lambda d: d > FACE),
         ('IN A REVEAL (%.2f to %.2f)' % (REVEAL, FACE), lambda d: REVEAL <= d <= FACE),
         ('IN THE CORRIDOR (d < %.2f)' % REVEAL, lambda d: d < REVEAL)]
for label, test in bands:
    sel = [r for r in rows if test(r[3])]
    print('%-34s %4d cameras' % (label, len(sel)))
    if not sel: continue
    by = {}
    for r in sel: by.setdefault(r[0], []).append(r)
    for k in sorted(by):
        v = by[k]
        u = [r[2] for r in v]; d = [r[3] for r in v]; h = [r[4] for r in v]
        print('    %-6s %3d   u %6.2f..%-6.2f  d %6.2f..%-6.2f  h %5.2f..%-5.2f'
              % (k, len(v), min(u), max(u), min(d), max(d), min(h), max(h)))

deep = sorted([r for r in rows if r[3] < FACE], key=lambda r: r[3])
print('')
if deep:
    print('the twelve cameras that stand furthest north (deepest into the wall):')
    print('  %-6s %-16s %7s %7s %7s   %s' % ('class', 'frame', 'u', 'd', 'h', 'looking'))
    for r in deep[:12]:
        print('  %-6s %-16s %7.2f %7.2f %7.2f   u %+.2f d %+.2f up %+.2f' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
    dmin = deep[0][3]
    print('')
    print('DEEPEST CAMERA d %.2f. That is a HARD LOWER BOUND on how far the space behind the wall runs:' % dmin)
    print('a phone stood there, so the room is at least %.2f m deep from the inner face,' % (FACE - dmin))
    print('and at least %.2f m deep from the back of the reveal.' % max(0.0, REVEAL - dmin))
    inC = [r for r in deep if r[3] < REVEAL]
    if inC:
        hs = sorted(r[4] for r in inC)
        print('%d of them are past the reveal, standing IN the corridor, h %.2f..%.2f.' % (len(inC), hs[0], hs[-1]))
        print('A phone is carried 1.35-1.65 m above the floor, so the floor they stand on is h %.2f..%.2f'
              % (hs[0] - 1.65, hs[-1] - 1.35))
        print('(the model draws that floor as 8.34).')
    else:
        print('NONE of them is past the reveal: every camera north of the wall is standing IN AN OPENING,')
        print('leaning through it, not in the corridor. The corridor itself has never been stood in by a')
        print('registered camera, so its width and its ceiling remain unmeasured by this instrument too.')
else:
    print('NO registered camera in the whole archive stands north of the wall face. The corridor has never')
    print('been surveyed from inside and nothing in the imagery constrains its width or its ceiling.')

if '--csv' in sys.argv:
    out = sys.argv[sys.argv.index('--csv') + 1]
    with open(out, 'w', newline='\n') as fh:
        fh.write('class,frame,u,d,h,look_u,look_d,look_up\n')
        for r in rows: fh.write('%s,%s,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n' % r)
    print('\nwrote %s' % out)
