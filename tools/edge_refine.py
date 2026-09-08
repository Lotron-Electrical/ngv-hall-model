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


def find_edge(img, x, y, ux, uy, mpp, win, iters=4, min_contrast=10.0, max_travel=None):
    """Offset in metres from (x, y) along (ux, uy) to the strongest brightness edge, or None.

    win is the HALF window in metres. The window is re-centred on each iteration, so the total travel is
    bounded by max_travel (default 2*win) and a sample that wants to run further is refused instead of
    being clipped: a reading that has walked two windows away is a different feature, not this one.
    """
    R = int(round(win / mpp))
    if R < 4 or R > 90:
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
