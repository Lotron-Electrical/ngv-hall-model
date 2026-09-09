# 2026-09-09: the sill was never really measured, it was measured along a ray, and this is the fix.
#
# The window-invariance audit put the north wall sill through three averaging windows with the RANSAC band
# narrowed so all three had to find the SAME feature, and all three did: 96 to 98 per cent of the inliers
# inside a drawn opening every time, which is the specificity test that says a line is the openings' own.
# They then disagreed by 149 mm in height and 285 mm in depth, against a head that held to 22 and 26.
#
# BUT THEY DID NOT SCATTER, THEY SLID. The three sill answers are (-0.058, 8.761), (-0.246, 8.859) and
# (-0.343, 8.910), and the ratio of the steps between consecutive pairs is -0.52 and -0.53. Three points
# on one straight line in the (d, h) plane is not noise; it is the degenerate direction of the fit. The
# rays cannot separate the depth of that edge from its height, so what was measured is one combination of
# the two, and the window merely chose where along the line to stop. A single number with a 15 mm residual
# was reported for something the data never pinned.
#
# THE FIX NEEDS NO NEW IMAGERY, ONLY THE THING ALREADY KNOWN. The wall face has been measured
# independently, twice, by edges of opposite polarity, and the model draws it on d -0.090. Slide each fit
# along its own degenerate direction until it reaches that face and the free parameter is gone. Do that
# and the sill's three windows collapse from a 149 mm spread onto a single value; the head, which was
# never badly conditioned, tightens as well.
#
# This is the same disease the corridor died of, caught in a place where there IS a cure: there the
# baseline was gone and nothing could anchor it, here the anchor was measured hours earlier.
import numpy as np

DNORTH = -0.090
FITS = {
    'sill': ((-0.058, 8.761), (-0.246, 8.859), (-0.343, 8.910)),
    'head': ((-0.107, 11.236), (-0.129, 11.250), (-0.133, 11.258)),
}
WINDOWS = (40, 20, 30)

for edge in ('sill', 'head'):
    pts = np.array(FITS[edge], float)
    d, h = pts[:, 0], pts[:, 1]
    slope = float(np.polyfit(d, h, 1)[0])
    resid = h - (h.mean() + slope * (d - d.mean()))
    print('')
    print('%s: three windows %s' % (edge.upper(), ', '.join(str(w) for w in WINDOWS)))
    for (dv, hv), w in zip(FITS[edge], WINDOWS):
        print('   HWIN %-3d d %+.3f h %.3f' % (w, dv, hv))
    print('   raw spread %.0f mm in height and %.0f mm in depth'
          % (1000 * float(np.ptp(h)), 1000 * float(np.ptp(d))))
    print('   they lie on one line of slope %+.3f m per m, off it by at most %.0f mm, which is the'
          % (slope, 1000 * float(np.abs(resid).max())))
    print('   degenerate direction of the fit and not three independent answers')
    anchored = h + slope * (DNORTH - d)
    print('   slid along that line onto the measured face d %+.3f they give %s'
          % (DNORTH, ', '.join('%.3f' % a for a in anchored)))
    print('   ANCHORED %s = %.3f, spread now %.0f mm (was %.0f)'
          % (edge, float(anchored.mean()), 1000 * float(np.ptp(anchored)), 1000 * float(np.ptp(h))))
