# For a posed 4K frame: which height h does an image row correspond to on a vertical plane u = U
# across the hall (d 2..13)? Reads the rows off the overlay crop (2x, offset as endwall_overlay.py).
#   python tools/endwall_rows.py <frame> <row_in_crop> [<row> ...]
import sys, cv2, numpy as np
sys.path.insert(0, 'tools'); import underside_geom as U
O = np.array([-54.907447, -1.43545, 3.040286]); HU = np.array([0.975681, 0, 0.219196]); HD = np.array([0.219196, 0, -0.975681])
def world(u, d, h): return O + u * HU + d * HD + np.array([0, h, 0])
frame = sys.argv[1]; rows = [float(a) for a in sys.argv[2:]]
cams = U.load_class('day4k'); cam, fpath = cams[frame]
UB = 0.344; D = 15.364
def pt(u, d, h):
    x, y, z = cam.project(np.asarray([world(u, d, h)])); return (float(x[0]), float(y[0]))
ps = [pt(UB, 0, 0), pt(UB, D, 0), pt(UB, 0, 12.5), pt(UB, D, 12.5)]
xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
x0 = max(0, min(xs) - 150); y0 = max(0, min(ys) - 150)
# invert: for plane u = U and d = dm, find h whose projected row equals the target (monotonic in h)
def h_of_row(Uplane, dm, row):
    lo, hi = -2.0, 14.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if pt(Uplane, dm, mid)[1] > row: lo = mid
        else: hi = mid
    return (lo + hi) / 2
for r in rows:
    orig = y0 + r / 2.0
    out = ['row %5.0f (orig %5.0f):' % (r, orig)]
    for Uplane in (4.7, 4.05, 3.4, 0.344, -4.65):
        hs = [h_of_row(Uplane, dm, orig) for dm in (3.0, 7.7, 12.5)]
        out.append(' u=%5.2f h=%.2f/%.2f/%.2f' % (Uplane, *hs))
    print(''.join(out))
