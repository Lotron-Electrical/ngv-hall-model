# 2026-09-10: WHERE ALONG THE WALL IS THE DARK PATCH, RATHER THAN IS THERE ONE.
#
# tools/opening_holes.py asked whether a hole is where this file draws one. Eleven of the twelve read as
# holes against the stone beside them and opening 3 read the other way round: its interior came back
# BRIGHTER than its own pier, 45.5 against 41.5, and it was the brightest interior and the darkest pier
# of all twelve. Both halves moving at once is the signature of a rectangle in the wrong place, because a
# rectangle drawn off the real opening samples stone while the pier sample beside it catches the hole.
#
# AND THE FILE PREDICTED WHICH WAY BEFORE ANY PICTURE WAS OPENED. A straight line fitted to the other
# eleven drawn centres gives a spacing of 3.679 m and holds them all within 0.115 m. Opening 3 sits
# 0.784 m WEST of that rhythm. So the prediction, written down first: the picture should find opening 3
# about +0.78 m east of where it is drawn, and the other eleven at zero.
#
# THE INSTRUMENT. For each frame and each opening, brightness is read in a column of the wall band at
# 60 mm steps across a span reaching 1.5 m either side of the drawn opening, and the darkest window one
# opening wide is found. The offset of that window from the drawn position is the reading.
#
# THE TRAP THIS HAS TO AVOID, and it is the one that has caught this file all day. A search centred on
# the drawn position returns a median of ZERO when it is pure noise, by symmetry, exactly as it does when
# the model is right. So "the other eleven come back at zero" is NOT on its own evidence of anything.
# The discriminator is the SPREAD: noise scatters the per-frame offsets across the whole 3 m search and
# signal clusters them. The real test is the ASYMMETRY: noise cannot put one opening a long way off zero
# and leave its neighbours put.
#   python tools/opening_shift.py
import sys

import cv2
import numpy as np

sys.path.insert(0, 'tools')
import underside_geom as U

O = np.array([-54.907447, -1.43545, 3.040286])
HU = np.array([0.975681, 0, 0.219196])
HD = np.array([0.219196, 0, -0.975681])
DN = -0.030
SILL, HEAD = 8.740, 11.165
OPEN = [[4.098, 5.310], [7.697, 8.911], [10.707, 11.920],
        [15.227, 16.440], [18.917, 20.130], [22.565, 23.778],
        [26.213, 27.426], [29.963, 31.175], [33.642, 34.853],
        [37.177, 38.383], [40.906, 42.118], [44.526, 45.739]]
CLASSES = ('walk', 'night', 'day4k')
REACH, USTEP = 1.5, 0.06
LEVS = np.linspace(SILL + 0.25, HEAD - 0.25, 9)


def profile(im, cam, ucols):
    """median brightness in the wall band at each u, or None if any column is out of shot"""
    pts = np.array([O + u * HU + DN * HD + np.array([0.0, lv, 0.0]) for u in ucols for lv in LEVS])
    x, y, z = cam.project(pts)
    ok = np.logical_and.reduce([z > 0.5, x > 1, x < cam.w - 2, y > 1, y < cam.h - 2])
    ok = ok.reshape(len(ucols), len(LEVS))
    if not ok.all():                      # a partly visible sweep biases the darkest window
        return None
    x = x.reshape(len(ucols), len(LEVS))
    y = y.reshape(len(ucols), len(LEVS))
    if (x.max() - x.min()) < 40 and (y.max() - y.min()) < 40:
        return None
    out = np.empty(len(ucols))
    for i in range(len(ucols)):
        out[i] = np.median([float(im[int(y[i, j]), int(x[i, j])]) for j in range(len(LEVS))])
    return out


rows = []
for cname in CLASSES:
    try:
        frames = U.load_class(cname)
    except Exception:
        continue
    for k, (cam, ip) in sorted(frames.items()):
        q = cam.center - O
        cd, ch = float(q @ HD), float(q[1])
        if ch > 3.0 or cd < 3.0:
            continue
        im = None
        for oi, (u0, u1) in enumerate(OPEN):
            w = u1 - u0
            cu = 0.5 * (u0 + u1)
            if im is None:
                im = cv2.imread(ip, cv2.IMREAD_GRAYSCALE)
                if im is None:
                    break
            ucols = np.arange(cu - REACH - w / 2 + 0.12, cu + REACH + w / 2 - 0.12 + 1e-9, USTEP)
            pr = profile(im, cam, ucols)
            if pr is None:
                continue
            half = int(round((w / 2 - 0.12) / USTEP))
            lo0, hi0 = half, len(ucols) - half
            if hi0 - lo0 < 9:
                continue
            win = np.array([pr[i - half:i + half + 1].mean() for i in range(lo0, hi0)])
            cs = ucols[lo0:hi0]
            # THE FRAME MUST CARRY CONTRAST TO CARRY AN ANSWER. A flat profile has a darkest window
            # somewhere, and it means nothing.
            if win.min() > 0.80 * win.max():
                continue
            rows.append((oi + 1, float(cs[int(np.argmin(win))] - cu), cd, k, cname))

print('%d readings, each the darkest opening-wide window within 1.5 m of a drawn opening' % len(rows))
print('')
print(' opening   n     offset found    quartiles        near / far      spread')
res = []
for oi in range(1, 13):
    rs = [r for r in rows if r[0] == oi]
    if len(rs) < 12:
        print('   %2d     %3d    too few to say' % (oi, len(rs)))
        continue
    v = np.array([r[1] for r in rs])
    q1, q3 = float(np.percentile(v, 25)), float(np.percentile(v, 75))
    byd = sorted(rs, key=lambda r: r[2])
    h = len(byd) // 2
    near = float(np.median([r[1] for r in byd[:h]]))
    far = float(np.median([r[1] for r in byd[h:]]))
    med = float(np.median(v))
    res.append((oi, len(rs), med, q1, q3, near, far))
    print('   %2d     %3d      %+.3f m      %+.3f %+.3f    %+.3f %+.3f    %.3f'
          % (oi, len(rs), med, q1, q3, near, far, q3 - q1))
print('')
if len(res) < 10:
    sys.exit('   too few openings answered to run the control')

# THE RAW OFFSETS ARE NOT THE ANSWER AND THE FIRST VERSION OF THIS PRINTED THEM AS IF THEY WERE.
# Opening 3 came back +1.014 m against a prediction of +0.784 and the run declared the prediction held,
# on a claim whose own interquartile range was 1.200 m. That is the mistake this file has now paid for
# five times: a number that lands where you hoped, on a scatter wide enough to land anywhere.
#
# AND THE TABLE SHOWS WHY IT CANNOT BE READ RAW. The offsets run positive in the west and negative in
# the east, right across the wall: +0.29 +0.23 down to -0.19 -0.07. Something common to the whole run
# leans them, and the west frames are the few, the far and the poor ones. So opening 3 sitting positive
# is partly just opening 3 being in the west.
#
# SO IT IS DIFFERENCED AGAINST ITS OWN NEIGHBOURS, which is the move that settled the head lean: whatever
# leans the instrument leans the openings either side of it by the same amount, and subtracting them
# cancels it. Each opening is compared with the median of the (up to four) openings within two places of
# it. That statistic is computed for ALL TWELVE, so the other eleven are the control on the differencing
# itself and not only on the offsets, and the 95 per cent range on each comes from resampling its own
# frames rather than from any assumption about how they scatter.
rng = np.random.default_rng(20260910)
samples = {r[0]: np.array([q[1] for q in rows if q[0] == r[0]]) for r in res}
answered = [r[0] for r in res]


def diffs(med):
    out = {}
    for oi in answered:
        nb = [med[j] for j in answered if j != oi and abs(j - oi) <= 2]
        if nb:
            out[oi] = med[oi] - float(np.median(nb))
    return out


base = diffs({oi: float(np.median(samples[oi])) for oi in answered})
boot = {oi: [] for oi in base}
for _ in range(2000):
    md = {oi: float(np.median(rng.choice(samples[oi], samples[oi].size))) for oi in answered}
    d = diffs(md)
    for oi in boot:
        boot[oi].append(d[oi])
blo = {oi: float(np.percentile(boot[oi], 2.5)) for oi in boot}
bhi = {oi: float(np.percentile(boot[oi], 97.5)) for oi in boot}


def certain(oi):
    """does the 95 per cent range for this opening keep clear of zero"""
    return blo[oi] > 0 or bhi[oi] < 0


print('   EACH OPENING AGAINST ITS OWN NEIGHBOURS, which cancels anything leaning the whole run:')
print('    opening    stands out by      95 per cent from 2000 resamples')
for oi in sorted(base):
    print('       %2d        %+.3f m          %+.3f to %+.3f%s'
          % (oi, base[oi], blo[oi], bhi[oi], '   <-- clear of zero' if certain(oi) else ''))
if 3 not in base:
    sys.exit('   opening 3 did not answer, so the prediction is untested')
d3 = base[3]
others = [abs(v) for k, v in base.items() if k != 3]
worst = max(others)
print('')
print('   OPENING 3 STANDS OUT BY %+.3f m, 95 per cent %+.3f to %+.3f, on %d frames.'
      % (d3, blo[3], bhi[3], len(samples[3])))
print('   THE ELEVEN CONTROLS STAND OUT BY AT MOST %.3f m, and %d of them keep clear of zero.'
      % (worst, sum(1 for k in base if k != 3 and certain(k))))
print('   THE PREDICTION, written before any picture was opened, was +0.784 m from the rhythm of the')
print('   other eleven drawn centres.')
if not certain(3):
    print('   REFUSED. The 95 per cent range on opening 3 includes zero, so the picture does not separate')
    print('   it from its neighbours however far the median wanders. Nothing moves.')
elif abs(d3) < 1.6 * worst:
    print('   REFUSED. Opening 3 stands out by %.3f m and a control stands out by %.3f, so it is not the'
          % (abs(d3), worst))
    print('   odd one out by enough to act on. Nothing moves.')
elif not (blo[3] <= 0.784 <= bhi[3]):
    print('   A REAL OFFSET, AND NOT THE PREDICTED ONE: %+.3f m, with the prediction 0.784 outside the'
          % d3)
    print('   range. The two lines agree opening 3 is wrong and disagree about by how much, so the drawn')
    print('   position is refused and no replacement is drawn from this. Nothing moves yet.')
else:
    print('   THE PREDICTION HOLDS, AND THE CONVERGENCE IS WHAT MAKES IT ONE. The drawn spacing of the')
    print('   other eleven and the photographs are independent: one is arithmetic on this file, the other')
    print('   is pixels. They put opening 3 in the same place, %.2f m east of where it is drawn, while'
          % d3)
    print('   eleven controls run through the identical code and stay put.')
