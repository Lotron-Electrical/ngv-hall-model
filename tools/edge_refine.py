# 2026-09-09: THE FOLLOW BIAS, and the fix for it.
# An adversarial audit of today's three measurements found the same defect in both instruments: the answer
# partly follows the value the model draws. Same frames, same face, same code, only the drawn level changed:
#   drawn 8.90 -> edge reported at h 9.057      drawn 9.02 -> edge reported at h 9.093
# The drawn line moved 0.120 m and the SAME PHYSICAL EDGE came back 0.036 m higher, a follow gain of 0.30.
# On the wall it is worse: drawn width 1.256 measured 1.219, drawn 1.213 measured 1.189, a gain of 0.70.
# That matters far beyond the bias itself. It makes "the residual is near zero after the change" worthless
# as a check, because part of the zero was manufactured by the change, and several comments in index.html
# were written in exactly that form.
# TWO CAUSES, both fixed here:
#  1. The profile is centred on the drawn line and only reaches half a window either way, so an edge near
#     the rim is pulled inward, and an edge outside is reported AS the rim.
#  2. argmax over the profile has no interior test. When the true edge is outside the window the peak lands
#     on the slice boundary and that boundary is returned as a reading, which looks like a small offset.
# THE FIX is a fixed point rather than a single look. Search, re-centre the window on what was found, search
# again, and repeat until it stops moving. Where it settles is a property of the picture, not of the line
# the model happened to draw, so the same physical edge returns the same height whatever the model says.
# A sample whose peak sits on the slice boundary at convergence is refused rather than reported.
import numpy as np


import os as _os

MAXR = int(_os.environ.get('MAXR', 90))


def find_edge(img, x, y, ux, uy, mpp, win, iters=4, min_contrast=10.0, max_travel=None):
    """Offset in metres from (x, y) along (ux, uy) to the strongest brightness edge, or None.

    win is the HALF window in metres. The window is re-centred on each iteration, so the total travel is
    bounded by max_travel (default 2*win) and a sample that wants to run further is refused instead of
    being clipped: a reading that has walked two windows away is a different feature, not this one.
    """
    R = int(round(win / mpp))
    # THE UPPER CAP USED TO BE 90 PIXELS AND IT WAS THROWING AWAY THE BEST FRAMES IN THE ARCHIVE
    # (2026-09-09). The window is set in METRES, so its size in pixels grows as the camera gets closer, and
    # a fixed pixel cap therefore refuses a frame for being NEAR. Measured: b7s stands 0.86 to 1.00 m
    # behind an end parapet, the only capture in the archive that sees one from arm's length rather than
    # across 28 to 40 m of hall, and there a 0.25 m window is 490 to 566 px. All 12 of those frames, and
    # all 27 pan-chained ones, were refused before a single pixel was read. That is a large part of why
    # every parapet reading has come from the far side of the room, and why the fitted follow gain there
    # runs 0.66 to 0.70: a distant instrument has little to go on but the line it started from.
    # The cap is now a parameter and still DEFAULTS TO 90, because raising it silently would change every
    # number ever taken with this finder, and the point of the fixed-point rewrite was that the instrument
    # stops moving underneath the measurements. A caller that wants the near field asks for it by name.
    if R < 4 or R > MAXR:
        return None
    if max_travel is None:
        max_travel = 2.0 * win
    t = np.arange(-R, R + 1)
    cx, cy, moved = float(x), float(y), 0.0
    H, W = img.shape[:2]
    for it in range(iters):
        sx = np.clip(np.round(cx + ux * t).astype(int), 0, W - 1)
        sy = np.clip(np.round(cy + uy * t).astype(int), 0, H - 1)
        prof = img[sy, sx].astype(np.float32)
        if prof.max() - prof.min() < min_contrast:
            return None
        g = np.abs(np.gradient(prof))
        j = int(np.argmax(g[2:-2])) + 2
        step = float(t[j]) * mpp
        # the interior test: a peak on the rim means the real edge is outside this window
        if j <= 2 or j >= len(t) - 3:
            return None
        moved += step
        if abs(moved) > max_travel:
            return None
        cx += ux * (step / mpp); cy += uy * (step / mpp)
        if abs(step) < mpp:              # settled to under a pixel: this is the fixed point
            return moved
    return None                          # never settled: refuse rather than report the last guess
