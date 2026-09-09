# 2026-09-09: stop measuring edges one at a time and ask the whole model how far off it is, in metres,
# on every posed frame at once.
#
# EVERY INSTRUMENT TONIGHT HAS FITTED ONE FEATURE FROM RAYS. That is how the openings, the upstands, the
# recess, the corridor ceiling and the jamb plane were each settled, and it is slow and it only ever
# answers about the feature it was pointed at. tools/overlay_walls.py drew the model over three posed
# frames and the verdict was that things "land on the real ones", which is an eye's verdict and carries no
# number.
#
# SO PUT A NUMBER ON IT, FEATURE BY FEATURE, ACROSS THE ARCHIVE. For each drawn line, walk a profile
# THROUGH it in the real image: sample the frame along the 3D direction the line is free to be wrong in,
# from half a metre one side to half a metre the other, and find the strongest brightness step in that
# profile. The offset comes out in METRES directly, because the profile is walked in metres, so no
# intrinsics and no pixel conversion enter the answer.
#
# THREE THINGS MAKE IT AN EXPERIMENT RATHER THAN A PICTURE.
#   A NULL LINE. A feature is placed where the model draws nothing: blank stone on the north wall face,
#   h 5.00, well below every opening. Whatever offsets that returns is what the machinery produces on its
#   own, and no real feature counts unless it beats that.
#   WINDOW INVARIANCE, RUN BY THE TOOL AND NOT BY HAND. Every feature is measured through a half-metre
#   window and a quarter-metre one in the same pass, and the two medians are printed side by side with
#   the movement between them. An edge that moves when the window changes is the window. This is the
#   fault that pinned a deck fit against its own ladder ceiling an hour ago and handed it 100 per cent
#   agreement while doing it, and doing the comparison by eye afterwards is how it nearly went unnoticed
#   the first time.
#   THE BLIND ZONE NAMED OUT LOUD. Averaging eight samples either side means the detector cannot see
#   within HWIN*STEP of either end of its profile, so with no real step to find it reports that
#   boundary itself. On the half-metre window that is 0.42 m, and the pier nulls duly come back on
#   -420 mm with a spread of zero. Any median within 30 mm of the boundary is the window speaking.
#   A CONTRAST BAR. A profile with no real step in it still has a maximum. Steps under 12 grey levels are
#   not counted, and the count that survives is reported beside the offset so a thin answer cannot hide
#   behind a tidy median.
#
# WHAT IT CANNOT DO is tell a feature from its neighbour half a metre away. A window of 0.5 m around the
# opening head will find the head; one around the deck will find whatever is nearest, and the deck's
# nearest neighbour is the parapet 0.76 m above it. So the windows are deliberately smaller than the
# spacing of what is drawn, and where that is not possible the feature is left out rather than fudged.
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U  # noqa: E402

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
VY = np.array([0.0, 1.0, 0.0])

CLASS = os.environ.get('CLS', 'walk')
STRIDE = int(os.environ.get('STRIDE', '8'))
SPANS = [float(x) for x in os.environ.get('SPANS', '0.50,0.30').split(',')]
STEP = 0.01
HWIN = 8
CONTRAST = 12.0
NSAMP = 9

# THE OPENINGS AS THE MODEL DRAWS THEM, and the PIERS between them, which are this instrument's null.
# The first run used blank stone for the null and it produced one profile in ninety-nine: real blank stone
# has no twelve-grey-level step in it, so the null could not return a number to be beaten. That is the
# cleanest possible pass and also useless as a bar. A pier carries the same masonry, the same lighting and
# the same courses as the wall beside an opening, so a null line drawn across a pier on the sill's own
# height is the honest question: does this machinery find "the sill" where there is no sill?
# 2026-09-09, SECOND FEATURE SET: THE EAST GALLERY, MEASURED FROM THE CAMERAS STANDING ON IT.
# Every balcony number in this model was fitted from HALL FLOOR frames looking at an end wall from 6 to
# 42 m away, through grazing sightlines and dark stone, and that is why the deck refused three times
# tonight. But roughly three hundred posed frames STAND ON the east gallery: b3 and b3p on u 47.9 to 48.5,
# b6g and b6gp on 49.1 to 49.4, day4k on 47.8 to 48.6, all with lens heights of 9.1 to 10.3. From up there
# the parapet is one to two metres away and lit, and the deck-to-parapet junction, which is the level 8.34
# itself, is directly underfoot and in view. It is the one place in this archive where the least supported
# number in the model is a near object rather than a far one.
#
# THE WINDOWS ARE SMALLER HERE AND THAT IS FORCED, NOT CHOSEN. The deck, the solid top and the rail top
# are 0.755 and 0.770 m apart, so a half-metre window would reach its neighbour and every feature would be
# free to answer with the wrong one. 0.30 and 0.20 both stay well inside that spacing.
#
# THE NULLS ARE MID-UPSTAND. Two lines are drawn across blank parapet face, 8.60 and 8.85, where the model
# draws nothing between the deck and the solid top. Same stone, same light, same distance as the real
# features either side of them.
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920], [15.227, 16.440], [18.917, 20.130],
        [22.565, 23.778], [26.213, 27.426], [29.963, 31.175], [33.642, 34.853], [37.177, 38.383],
        [40.906, 42.118], [44.526, 45.739]]
PIERS = [[OPEN[i][1] + 0.35, OPEN[i + 1][0] - 0.35] for i in range(len(OPEN) - 1)]
DN, SILL, HEAD = -0.030, 8.740, 11.165
SET = os.environ.get('SET', 'north')
FEATURES = []
if SET == 'north':
    for i, (u0, u1) in enumerate(OPEN):
        FEATURES.append(('opening %-2d sill' % (i + 1), (u0, u1), DN, SILL, 'h', False))
        FEATURES.append(('opening %-2d head' % (i + 1), (u0, u1), DN, HEAD, 'h', False))
    for i, (u0, u1) in enumerate(PIERS):
        if u1 - u0 < 0.8:
            continue
        FEATURES.append(('NULL pier %-2d sill line' % (i + 1), (u0, u1), DN, SILL, 'h', True))
        FEATURES.append(('NULL pier %-2d head line' % (i + 1), (u0, u1), DN, HEAD, 'h', True))
else:
    # the east gallery parapet, run in BANDS across the hall so a partial view still answers
    UFACE, DECK = 48.056, 8.34
    BANDS = [(1.0, 4.5), (4.5, 8.0), (8.0, 11.5), (11.5, 14.9)]
    LEVELS = [('deck junction  8.340', DECK, False), ('solid top      9.095', 9.095, False),
              ('rail top       9.865', 9.865, False), ('NULL face      8.600', 8.600, True),
              ('NULL face      8.850', 8.850, True)]
    for name, hv, isnull in LEVELS:
        for bi, (d0, d1) in enumerate(BANDS):
            FEATURES.append(('%s d%d' % (name, bi + 1), (d0, d1), UFACE, hv, 'h', isnull))


def unit(v):
    return v / np.linalg.norm(v)


def world(u, d, h):
    return O + u * HU + d * HD + h * VY


def profile(im, cam, X, N, span):
    """the longest contiguous run of the profile that is actually visible.

    THE FIRST GALLERY RUN RETURNED ZERO PROFILES ON NINETEEN OF TWENTY FEATURES, and the reason was this
    function rather than the building. It demanded that EVERY sample of a profile be in front of the lens
    and inside the frame. That is a fair demand from the hall floor, where a wall is fifteen metres away
    and a 0.6 m profile spans a few dozen pixels. It is an impossible demand from a camera standing ON the
    gallery a metre from the parapet, where the same 0.6 m fills much of the frame and its ends run off
    the edge. So the near view, the one place in this archive where the deck is a NEAR object, was being
    thrown away by a rule written for the far view.
    The longest contiguous visible run is used instead, provided it is long enough to carry the detector's
    own window. Nothing else relaxes: the detector still needs HWIN samples either side of a candidate, so
    a run that only just qualifies can still only report near its own middle."""
    ts = np.arange(-span, span + 1e-9, STEP)
    P = np.array([X + t * N for t in ts])
    x, y, z = cam.project(P)
    H, W = im.shape[:2]
    ok = np.logical_and.reduce([z > 0.3, x > 1, y > 1, x < W - 2, y < H - 2])
    if not ok.any():
        return None, None
    best_a, best_b, a = 0, 0, None
    for i, v in enumerate(list(ok) + [False]):
        if v and a is None:
            a = i
        elif not v and a is not None:
            if i - a > best_b - best_a:
                best_a, best_b = a, i
            a = None
    if best_b - best_a < 3 * HWIN + 1:
        return None, None
    sl = slice(best_a, best_b)
    xi = np.rint(x[sl]).astype(int)
    yi = np.rint(y[sl]).astype(int)
    return ts[sl], im[yi, xi].astype(np.float64)


def strongest(ts, v):
    best, bt = 0.0, None
    for i in range(HWIN, len(v) - HWIN):
        s = float(v[i - HWIN:i].mean() - v[i + 1:i + 1 + HWIN].mean())
        if abs(s) > abs(best):
            best, bt = s, float(ts[i])
    return bt, abs(best)


frames = U.load_class(CLASS)
keys = sorted(frames)[::STRIDE]
print('%s: %d frames in the class, %d sampled (stride %d)' % (CLASS, len(frames), len(keys), STRIDE))
print('windows %s m, step %.0f mm, %d samples each side, contrast bar %.0f grey levels'
      % (', '.join('%.2f' % s for s in SPANS), 1000 * STEP, HWIN, CONTRAST))
for s in SPANS:
    print('   a %.2f m window is blind within %.0f mm of its own ends, so its floor is %+.0f mm'
          % (s, 1000 * HWIN * STEP, -1000 * (s - HWIN * STEP)))

acc = {(f[0], s): [] for f in FEATURES for s in SPANS}
for k in keys:
    cam, ipath = frames[k]
    im = cv2.imread(ipath, cv2.IMREAD_GRAYSCALE)
    if im is None:
        continue
    im = cv2.GaussianBlur(im, (5, 5), 0)
    for name, rng, dfix, hfix, free, isnull in FEATURES:
        N = VY if free == 'h' else HD
        for a in np.linspace(rng[0] + 0.15, rng[1] - 0.15, NSAMP):
            X = world(a, dfix, hfix) if SET == 'north' else world(dfix, a, hfix)
            for s in SPANS:
                ts, v = profile(im, cam, X, N, s)
                if ts is None:
                    continue
                t, mag = strongest(ts, v)
                if t is None or mag < CONTRAST:
                    continue
                acc[(name, s)].append(t)


def med_of(name, s):
    a = np.array(acc[(name, s)])
    if len(a) < 20:
        return None, len(a), None
    m = float(np.median(a))
    return m, len(a), float(np.median(np.abs(a - m)))


FLOORS = {s: -(s - HWIN * STEP) for s in SPANS}
print('')
print('   feature                    n(wide)  wide      narrow    moves    verdict')
rows = []
for name, *_ in FEATURES:
    mw, nw, adw = med_of(name, SPANS[0])
    mn, nn, _ = med_of(name, SPANS[1])
    if mw is None or mn is None:
        print('   %-26s %5d   too few profiles cleared the contrast bar' % (name, nw))
        continue
    move = abs(mw - mn)
    onfloor = min(abs(mw - FLOORS[SPANS[0]]), abs(mn - FLOORS[SPANS[1]])) < 0.030
    if onfloor:
        verdict = 'THE WINDOW, sits on its own floor'
    elif move > 0.060:
        verdict = 'NOT INVARIANT, moves with the window'
    elif abs(mw) <= 0.050:
        verdict = 'CONFIRMED within 50 mm'
    else:
        verdict = 'OFFSET, invariant'
    rows.append((name, nw, mw, mn, move, verdict, name.startswith('NULL')))
    print('   %-26s %5d  %+6.0f mm  %+6.0f mm  %5.0f mm  %s'
          % (name, nw, 1000 * mw, 1000 * mn, 1000 * move, verdict))

real = [r for r in rows if not r[6]]
nul = [r for r in rows if r[6]]
inv = [r for r in real if 'NOT INVARIANT' not in r[5] and 'WINDOW' not in r[5]]
conf = [r for r in inv if 'CONFIRMED' in r[5]]
print('')
print('   %d drawn features and %d pier nulls carried enough signal to answer.' % (len(real), len(nul)))
print('   %d of the %d drawn features are window-invariant, and %d of those sit within 50 mm of where'
      % (len(inv), len(real), len(conf)))
print('   this model draws them.')
if nul:
    onfl = sum(1 for r in nul if 'WINDOW' in r[5])
    print('   %d of the %d nulls are the window speaking, which is the machinery telling on itself: with'
          % (onfl, len(nul)))
    print('   nothing to find it reports the edge of its own blind zone.')
if inv:
    worst = max(inv, key=lambda r: abs(r[2]))
    print('   The largest invariant offset is %s, %+.0f mm wide and %+.0f mm narrow.'
          % (worst[0].strip(), 1000 * worst[2], 1000 * worst[3]))
