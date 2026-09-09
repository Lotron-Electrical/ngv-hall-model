# 2026-09-09: MEASURE THE BALUSTRADE ACROSS THE NORTH WALL OPENINGS, which the model does not draw.
#
# The pan poses (tools/pan_poses.py) put 13 b1 frames inside north opening 5, and every one of them shows
# the operator leaning on a metal balustrade that exists in the photographs and not in index.html. Before
# it can be added it has to be measured, and two things rule out the obvious methods:
#   TRIANGULATION IS OUT. tools/pan_points.py was tried and REFUTED by drawing its own output back into the
#     frame: with the cameras a few centimetres apart, a one degree ray angle is pose noise rather than
#     parallax, so 3,611 "near field" points were really distant floor and people placed a metre away. With
#     a real parallax demand (5 degrees or more) exactly 2 points survive the whole clip. There is no
#     baseline here and no amount of filtering invents one.
#   A SINGLE FRAME IS OUT. One ray gives one equation and the rail has two unknowns, its height and how far
#     it stands from the wall. Assuming the depth and solving the height is how a wrong answer gets a tight
#     error bar.
#
# WHAT IS LEFT IS THE ONE THING THE POSES ARE GOOD FOR: many frames, taken from positions that differ by
# 0.3 m horizontally and 0.28 m vertically, must ALL agree about a single horizontal line in space. So the
# search is over the line itself, not over any image. For a candidate depth d and height h the line is
# projected into every frame and scored by the image gradient it lands on. A candidate that is wrong may
# land on a strong edge in one frame by luck; it cannot land on strong edges in thirteen frames shot from
# different places, because the perspective differs. The maximum of the summed score is the rail.
#
# THIS CANNOT ECHO THE MODEL. The grid runs from well below the opening sill to well above it, the model
# draws nothing in that space at all, and the score comes from raw image gradient with no starting line.
# The follow bias that had to be fitted out of every level measurement in this project cannot arise.
#
# WHAT IS REPORTED. The summed peak, and separately EACH FRAME'S OWN peak. If the frames independently
# agree the spread is small and the number is measured; if the summed peak is sharp only because one frame
# dominates, the spread says so and nothing is claimed.
#   python tools/rail_fit.py <class> <u0> <u1> [--dlo -1.2] [--dhi 0.6] [--hlo 8.6] [--hhi 10.3]
import argparse
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])

ap = argparse.ArgumentParser()
ap.add_argument('cls')
ap.add_argument('u0', type=float)
ap.add_argument('u1', type=float)
ap.add_argument('--dlo', type=float, default=-1.2)
ap.add_argument('--dhi', type=float, default=0.6)
ap.add_argument('--hlo', type=float, default=8.6)
ap.add_argument('--hhi', type=float, default=10.3)
ap.add_argument('--step-d', type=float, default=0.04)
ap.add_argument('--step-h', type=float, default=0.02)
ap.add_argument('--samples', type=int, default=80)
ap.add_argument('--max-frames', type=int, default=18)
a = ap.parse_args()

frames = U.load_class(a.cls)
# only the frames that stand in this run of wall and look downward, which is what seeing a rail means
use = []
for stem, (cam, path) in frames.items():
    q = cam.center - O
    cu, cd, ch = float(q @ HU), float(q @ HD), float(cam.center[1] - O[1])
    look = cam.R.T @ np.array([0.0, 0.0, 1.0])
    if a.u0 - 1.0 < cu < a.u1 + 1.0 and abs(cd) < 1.5 and 8.5 < ch < 10.5 and look[1] < -0.15:
        use.append((stem, cam, path, cu, cd, ch))
# KEEP THE FRAMES THAT DIFFER MOST, not the first ones found. The whole argument is that many viewpoints
# must agree, so twenty frames from one second of pan are worth less than eight spread across the look.
use.sort(key=lambda r: r[0])
if len(use) > a.max_frames:
    pick = np.linspace(0, len(use) - 1, a.max_frames).round().astype(int)
    use = [use[k] for k in sorted(set(pick.tolist()))]
print(a.cls, len(use), 'frames stand in u', a.u0, 'to', a.u1, 'and look downward')
if len(use) < 4:
    raise SystemExit('too few frames to make many-view agreement mean anything')
cu = np.array([r[3] for r in use])
cd = np.array([r[4] for r in use])
ch = np.array([r[5] for r in use])
print('   they stand across u', round(float(cu.max() - cu.min()), 3), 'm, d', round(float(cd.max() - cd.min()), 3),
      'm and h', round(float(ch.max() - ch.min()), 3), 'm, which is the whole geometry available')

grads = {}
for stem, cam, path, _a1, _a2, _a3 in use:
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    im = cv2.GaussianBlur(im, (0, 0), 2.0)
    gx = cv2.Sobel(im, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(im, cv2.CV_32F, 0, 1, ksize=5)
    g = np.hypot(gx, gy)
    grads[stem] = g / (float(np.percentile(g, 99)) + 1e-6)

us = np.linspace(a.u0, a.u1, a.samples)
dgrid = np.arange(a.dlo, a.dhi + 1e-9, a.step_d)
hgrid = np.arange(a.hlo, a.hhi + 1e-9, a.step_h)


# EVERY CANDIDATE LINE FOR ONE FRAME IN ONE PROJECTION. The grid is 46 depths by 86 heights by 80 samples,
# and projecting those one line at a time is a million calls per clip. Built as a single array it is one.
DV, HV, UV = np.meshgrid(dgrid, hgrid, us, indexing='ij')
PTS = (O + UV.reshape(-1, 1) * HU + DV.reshape(-1, 1) * HD
       + np.stack([np.zeros(DV.size), HV.reshape(-1), np.zeros(DV.size)], axis=1))
SHAPE = DV.shape


def score_frame_all(cam, g):
    x, y, z = cam.project(PTS)
    ok = np.logical_and(z > 0.2, np.logical_and(x >= 0, x <= g.shape[1] - 1.51))
    ok = np.logical_and(ok, np.logical_and(y >= 0, y <= g.shape[0] - 1.51))
    xi = np.clip(np.round(x), 0, g.shape[1] - 1).astype(np.int32)
    yi = np.clip(np.round(y), 0, g.shape[0] - 1).astype(np.int32)
    v = np.where(ok, g[yi, xi], 0.0).reshape(SHAPE)
    n = ok.reshape(SHAPE).sum(axis=2)
    # A CAMERA INSIDE AN OPENING SEES ONLY PART OF THE LINE, because the reveal cuts it off, so demanding
    # half of it visible refused most of the frames and left the peak sitting on the edge of the grid. A
    # quarter is enough to place a line, and the count is what keeps a two-sample fluke out.
    M = np.where(n >= 0.25 * SHAPE[2], v.sum(axis=2) / np.maximum(n, 1), np.nan)
    return M


S = np.zeros((len(dgrid), len(hgrid)))
per = {}
for stem, cam, _p, _a1, _a2, _a3 in use:
    g = grads[stem]
    M = score_frame_all(cam, g)
    if np.all(np.isnan(M)):
        continue
    # NORMALISE EACH FRAME BY ITS OWN RANGE before adding. Without this a single bright, contrasty frame
    # decides the answer for all of them and the many-view agreement that justifies the whole method never
    # actually happens.
    lo, hi = float(np.nanmin(M)), float(np.nanmax(M))
    N = (M - lo) / max(1e-9, hi - lo)
    per[stem] = N
    S += np.nan_to_num(N)

if not per:
    raise SystemExit('no frame could see the whole line anywhere in the grid')
S /= len(per)
i, j = np.unravel_index(int(np.nanargmax(S)), S.shape)
print('')
print('SUMMED PEAK: d', round(float(dgrid[i]), 3), 'h', round(float(hgrid[j]), 3), 'score', round(float(S[i, j]), 4))

print('')
print('EACH FRAME ON ITS OWN, at the summed peak depth')
hs = []
for stem in sorted(per):
    col = per[stem][i, :]
    if np.all(np.isnan(col)):
        continue
    k = int(np.nanargmax(col))
    hs.append(float(hgrid[k]))
    print('   ', stem, 'peaks h', round(float(hgrid[k]), 3), 'score', round(float(col[k]), 3))
if len(hs) >= 4:
    H = np.array(hs)
    print('')
    print('   ', len(H), 'frames: median', round(float(np.median(H)), 3), 'spread', round(float(H.max() - H.min()), 3),
          'quartiles', round(float(np.percentile(H, 25)), 3), round(float(np.percentile(H, 75)), 3))
    if H.max() - H.min() <= 0.10:
        print('    THE FRAMES AGREE INDEPENDENTLY, this is a measurement')
    else:
        print('    THE FRAMES DISAGREE by more than 0.10 m, so the summed peak is not a measurement')

print('')
print('THE FIVE BEST CANDIDATES OVERALL, to show whether the peak is isolated or one of many')
flat = np.argsort(S, axis=None)[::-1]
shown = []
for f in flat:
    ii, jj = np.unravel_index(int(f), S.shape)
    if any(abs(dgrid[ii] - d0) < 0.1 and abs(hgrid[jj] - h0) < 0.08 for d0, h0 in shown):
        continue
    shown.append((float(dgrid[ii]), float(hgrid[jj])))
    print('    d', round(float(dgrid[ii]), 3), 'h', round(float(hgrid[jj]), 3), 'score', round(float(S[ii, jj]), 4))
    if len(shown) >= 5:
        break
