# 2026-09-10: DOES THE PHOTOGRAPH SHOW A DARK BAR WHERE THIS FILE DRAWS A HANDRAIL.
#
# tools/rail_seeover.py projected each deck-standing camera's OPTICAL AXIS onto the end face and found it
# threads between the solid upstand and the handrail, and I read that as clearing the handrail. It does
# not. An axis is one ray. A handrail 60 mm tall standing 0.16 m from a lens blocks a BAND of the view
# either side of that ray while the ray itself goes under it, so the axis test can never refute a handrail
# and should never have been asked to.
#
# THE RIGHT QUESTION IS PUT TO THE PICTURE. Project the handrail's own top and bottom edges into the frame
# and look at what is there. An opaque rail 0.16 m from the lens is the darkest and flattest thing in the
# picture: nearly no brightness variation across it, and much darker than whatever it is standing against.
# The hall behind it is bright, varied and full of edges. So sample the band the handrail occupies and the
# two bands immediately above and below it, and compare.
#
# THE CONTROL IS BUILT IN. The bands above and below are the same picture, the same exposure and the same
# lens, and they are chosen the same way. If the handrail band is not markedly darker and flatter than
# both of them, there is no rail there. If it is, there is. Nothing about the model enters the comparison
# except where to look.
#
# WHAT IT CANNOT DO. It tests the rail as DRAWN. A rail 0.2 m lower would put its band somewhere else and
# this would report the drawn band as empty without saying where the real one is. It refuses a position;
# it cannot find one.
#   python tools/rail_band.py [west|east|both]
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
ENDS = {'west': {'face': 4.194, 'deck': 8.34, 'rail': 1.459, 'sense': -1.0},
        'east': {'face': 48.056, 'deck': 8.34, 'rail': 1.525, 'sense': 1.0}}
CLASSES = ('b1', 'b3', 'b5', 'b7s', 'b6g')
THK = 0.06


def band_stats(im, cam, uF, lo, hi, ds):
    """mean and variation of the pixels a horizontal strip on the face plane covers in this frame"""
    vals = []
    for d in ds:
        a = O + uF * HU + d * HD + np.array([0.0, lo, 0.0])
        b = O + uF * HU + d * HD + np.array([0.0, hi, 0.0])
        x, y, z = cam.project(np.asarray([a, b]))
        if not np.all(z > 0.02):
            continue
        n = int(max(3, min(60, abs(y[1] - y[0]) + abs(x[1] - x[0]))))
        for t in np.linspace(0.15, 0.85, n):
            px, py = float(x[0] + t * (x[1] - x[0])), float(y[0] + t * (y[1] - y[0]))
            if 1 < px < cam.w - 2 and 1 < py < cam.h - 2:
                vals.append(float(im[int(py), int(px)]))
    if len(vals) < 40:
        return None
    v = np.array(vals)
    return float(v.mean()), float(v.std()), len(v)


which = sys.argv[1] if len(sys.argv) > 1 else 'both'
for end in (('west', 'east') if which == 'both' else (which,)):
    E = ENDS[end]
    uF, s = E['face'], E['sense']
    rail_hi = E['deck'] + E['rail']
    rail_lo = rail_hi - THK
    print('')
    print('%s end: the handrail as drawn is h %.3f to %.3f on the face plane u %.3f'
          % (end.upper(), rail_lo, rail_hi, uF))
    print('   %-14s  cam h   rail band       below           above       verdict'
          % 'frame')
    rows = []
    for cname in CLASSES:
        try:
            frames = U.load_class(cname)
        except Exception:
            continue
        for k, (cam, ip) in sorted(frames.items()):
            q = cam.center - O
            cu, cd, ch = float(q @ HU), float(q @ HD), float(q[1])
            if (cu - uF) * s < 0.02 or (cu - uF) * s > 3.5:
                continue
            if not (0.5 < cd < 14.9) or not (E['deck'] + 0.6 < ch < E['deck'] + 2.4):
                continue
            f = cam.R.T @ np.array([0, 0, 1.0])
            if float(f @ HU) * s > -0.15:
                continue
            im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            ds = np.linspace(max(0.4, cd - 3.0), min(14.9, cd + 3.0), 13)
            r = band_stats(im, cam, uF, rail_lo, rail_hi, ds)
            b = band_stats(im, cam, uF, rail_lo - 3 * THK, rail_lo - THK, ds)
            a = band_stats(im, cam, uF, rail_hi + THK, rail_hi + 3 * THK, ds)
            if r is None or b is None or a is None:
                continue
            darker = r[0] < 0.75 * min(a[0], b[0])
            flatter = r[1] < 0.75 * min(a[1], b[1])
            rows.append((cname, k, ch, r, b, a, darker and flatter))
            if len(rows) <= 16:
                print('   %-14s %5.2f   %5.1f/%4.1f     %5.1f/%4.1f     %5.1f/%4.1f    %s'
                      % (k, ch, r[0], r[1], b[0], b[1], a[0], a[1],
                         'a dark flat bar' if (darker and flatter) else 'no bar here'))
    if not rows:
        print('   no frame puts the drawn handrail band in shot')
        continue
    hits = sum(1 for r in rows if r[6])
    print('   %d frames tested, %d show a dark flat bar where the handrail is drawn (%.0f per cent)'
          % (len(rows), hits, 100.0 * hits / len(rows)))
    rm = float(np.median([r[3][0] for r in rows]))
    bm = float(np.median([r[4][0] for r in rows]))
    am = float(np.median([r[5][0] for r in rows]))
    print('   median brightness: rail band %.1f, below it %.1f, above it %.1f' % (rm, bm, am))
    # A VERDICT NEEDS ENOUGH FRAMES TO BE ONE. On seven frames, two hits is 29 per cent and the first
    # version of this printed "it stands" on exactly that, which is a coin landing twice. Under twelve
    # frames the run reports itself as inconclusive and no verdict is given either way.
    if len(rows) < 12:
        print('   INCONCLUSIVE: %d frames is not enough to say either way, and the brightness runs as a'
              % len(rows))
        print('   gradient (below %.1f, band %.1f, above %.1f) rather than as a bar in any case.'
              % (bm, rm, am))
    elif hits < 0.25 * len(rows):
        print('   THE HANDRAIL AS DRAWN IS NOT IN THESE PICTURES. It is a full-width opaque bar 0.16 m')
        print('   from the lens; it cannot be invisible. The drawn position is refused, and where the')
        print('   real one sits is not answered here.')
    else:
        print('   the drawn handrail band does read as a bar in these frames, so it stands')
